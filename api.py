import requests
from gmpy2 import is_prime
import traceback
import time
import random
import functools
import os
import json

from config import IS_DOCKER, SCRIPT_FOLDER, API_DEF_RETRIES, API_MAX_TIMEOUT, API_CANDIDATE_GEN_WAIT_TIME, GIT_VERSION, API_CPU_ACCEPT_THRESHOLD
from config import MACHINE_ID
from candidate import Candidate
from taskChunk import TaskChunk

API_TOKEN = open(f"{SCRIPT_FOLDER}/api_token.txt").read().strip()
if IS_DOCKER:
    os.remove(f"{SCRIPT_FOLDER}/api_token.txt")

SISMARGARET_API_BASE = "https://sismargaret.fact0rn.io/api/ecm/"
API_SESSION = requests.Session()
API_SESSION.request = functools.partial(API_SESSION.request, timeout=60)
API_SESSION.headers.update({"Authorization": API_TOKEN})


def onAPIError(funcName, retriesLeft):
    if retriesLeft <= 0:
        raise

    traceback.print_exc()
    toWait = min(API_MAX_TIMEOUT, 2 ** (API_DEF_RETRIES - retriesLeft))
    print(f"{funcName} failed. Retrying after {toWait}s")
    time.sleep(toWait)


def getCandidateAmountOnSisMargaret(retriesLeft = API_DEF_RETRIES):
    while True:
        try:
            url = SISMARGARET_API_BASE + "candidates/remaining"
            return int(API_SESSION.get(url).text)
        except Exception:
            onAPIError("getCandidateAmountOnSisMargaret", retriesLeft)
            retriesLeft -= 1


def getTaskChunkFromSisMargaret(retriesLeft = API_DEF_RETRIES, skipAmountCheck = False):
    while True:
        try:
            waitReason = None
            if not skipAmountCheck:
                amount = getCandidateAmountOnSisMargaret()
                if amount == 0:
                    waitReason = "No candidate available"
                elif amount >= API_CPU_ACCEPT_THRESHOLD:
                    waitReason = "GPU filter ongoing"

            if waitReason is None:
                url = f"{SISMARGARET_API_BASE}taskchunk/version/1?machineID={MACHINE_ID}"
                ret = API_SESSION.get(url).json()
                if "tasks" not in ret or len(ret["tasks"]) == 0:
                    waitReason = "No task chunk available"
                else:
                    ret = TaskChunk(ret)
                    print(f"getTaskChunkFromSisMargaret: Got new task chunk:\n{ret}")
                    return ret

            waitTime = random.uniform(*API_CANDIDATE_GEN_WAIT_TIME)
            print(f"getTaskChunkFromSisMargaret: {waitReason}. Retrying in {waitTime:.1f}s")
            time.sleep(waitTime)
        except Exception:
            onAPIError("getTaskChunkFromSisMargaret", retriesLeft)
            retriesLeft -= 1


def finishTaskChunkOnSisMargaret(taskChunk: TaskChunk, retriesLeft = API_DEF_RETRIES):
    while True:
        try:
            url = f"{SISMARGARET_API_BASE}finishTaskChunk/version/1?machineID={MACHINE_ID}"
            payload = json.dumps({
                "machineID": MACHINE_ID,
                "taskChunkId": taskChunk.taskChunkId,
                "taskResults": [
                    {
                        "taskId": t.taskId,
                        "curvesRan": t.curvesRan,
                        "taskRuntime": t.taskRuntime,
                    } for t in taskChunk.tasks
                ],
                "runtime": taskChunk.taskChunkRuntime
            }, separators=(',', ':'))
            resp = API_SESSION.post(url, data=payload)
            print("finishTaskChunkOnSisMargaret: Response:", resp.status_code, resp.text)
            return resp.status_code == 200
        except Exception:
            onAPIError("finishTaskChunkOnSisMargaret", retriesLeft)
            retriesLeft -= 1


def getAllCandidatesFromSisMargaret(retriesLeft = API_DEF_RETRIES):
    while True:
        try:
            url = f"{SISMARGARET_API_BASE}candidates?machineID={MACHINE_ID}"
            ret = API_SESSION.get(url).json()
            ret = [Candidate(c["id"], c["height"], int(c["n"])) for c in ret]
            return ret
        except Exception:
            onAPIError("getAllCandidatesFromSisMargaret", retriesLeft)


def submitSolutionToSisMargaret(candidateId: int, N: int, factor1: int, factor2: int, taskId = 0, retriesLeft = API_DEF_RETRIES):
    if type(N) != int or type(factor1) != int or type(factor2) != int:
        print(f"submitSolutionToSisMargaret: Invalid arguments {N}, {factor1}, {factor2}")
        return False

    if not is_prime(factor1) or factor1 > factor2 or factor1 * factor2 != N:
        print(f"submitSolutionToSisMargaret: Invalid solution {N} = {factor1} * {factor2}")
        return False

    print(f"submitSolutionToSisMargaret: Submitting {N} = {factor1} * {factor2}")
    while True:
        try:
            payload = json.dumps({
                "machineID": MACHINE_ID,
                "commit": GIT_VERSION,
                "taskId": taskId,
                "factor1": str(factor1),
                "factor2": str(factor2),
                "candidateId": candidateId
            }, separators=(',', ':'))
            url = SISMARGARET_API_BASE + "solution/version/1"
            resp = API_SESSION.post(url, data=payload)
            print("submitSolutionToSisMargaret: Response:", resp.status_code, resp.text)
            return resp.status_code == 200
        except Exception:
            onAPIError("submitSolutionToSisMargaret", retriesLeft)
            retriesLeft -= 1


def getHeightFromSisMargaret(retriesLeft = API_DEF_RETRIES):
    while True:
        try:
            url = SISMARGARET_API_BASE + "height"
            return int(API_SESSION.get(url).text)
        except Exception:
            onAPIError("getHeightFromSisMargaret", retriesLeft)
            retriesLeft -= 1


def isCandidateActiveOnSisMargaret(candidate: Candidate, retriesLeft = API_DEF_RETRIES):
    while True:
        try:
            url = SISMARGARET_API_BASE + f"candidate/{candidate.id}/active"
            resp = API_SESSION.get(url).text
            print("isCandidateActiveOnSisMargaret: Response:", resp)
            return resp == "true"
        except Exception:
            onAPIError("isCandidateActiveOnSisMargaret", retriesLeft)
            retriesLeft -= 1


def areCandidatesActiveOnSisMargaret(candidateIds: list[int], retriesLeft = API_DEF_RETRIES) -> dict[str, bool]:
    while True:
        try:
            url = SISMARGARET_API_BASE + "candidates/active"
            resp = API_SESSION.post(url, data=str(candidateIds))
            return resp.json()
        except Exception:
            onAPIError("areCandidatesActiveOnSisMargaret", retriesLeft)
            retriesLeft -= 1
