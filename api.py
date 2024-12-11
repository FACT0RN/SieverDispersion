import requests
from gmpy2 import is_prime
import traceback
import time
import random
import functools
import os
import json
import shutil
import base64

from config import IS_DOCKER, SCRIPT_FOLDER, API_DEF_RETRIES, API_MAX_TIMEOUT, API_CANDIDATE_GEN_WAIT_TIME, GIT_VERSION, API_CPU_ACCEPT_THRESHOLD
from config import DEFAULT_YAFU_WORKDIR
from candidate import Candidate
from taskChunk import TaskChunk
from mqttClient import ThreadsafeMQTTClient

API_TOKEN = open(f"{SCRIPT_FOLDER}/api_token.txt").read().strip()
if IS_DOCKER:
    os.remove(f"{SCRIPT_FOLDER}/api_token.txt")

SISMARGARET_USERNAME = json.loads(base64.urlsafe_b64decode(API_TOKEN.split(".")[1] + "=="))["sub"]
print(f"{SISMARGARET_USERNAME = }")
MACHINE_ID = open(f"{SCRIPT_FOLDER}/machineIDs/machineID-{SISMARGARET_USERNAME}.txt").read().strip()
print(f"{MACHINE_ID = }")

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


def getTaskChunkFromSisMargaret(type, retriesLeft = API_DEF_RETRIES, skipAmountCheck = True, machineID = MACHINE_ID):
    while True:
        try:
            waitReason = None
            if not skipAmountCheck:
                amount = getCandidateAmountOnSisMargaret()
                if amount == 0:
                    waitReason = "No candidate available"
                elif type == "cpu" and amount >= API_CPU_ACCEPT_THRESHOLD:
                    waitReason = "GPU filter ongoing"

            if waitReason is None:
                url = f"{SISMARGARET_API_BASE}{type}taskchunk/version/2?machineID={machineID}"
                ret = API_SESSION.get(url)
                if ret.status_code != 200:
                    waitReason = f"API returned error {ret.status_code}: {ret.text}"
                else:
                    ret = ret.json()
                    try:
                        ret = TaskChunk(ret, type)
                        if len(ret.tasks) == 0:
                            waitReason = "No task chunk available"
                        else:
                            print(f"getTaskChunkFromSisMargaret: Got new task chunk:\n{ret}")
                            return ret
                    except Exception:
                        traceback.print_exc()
                        print(f"{ret = }")
                        waitReason = "Invalid task chunk received"

            waitTime = random.uniform(*API_CANDIDATE_GEN_WAIT_TIME)
            print(f"getTaskChunkFromSisMargaret: {waitReason}. Retrying in {waitTime:.1f}s")
            time.sleep(waitTime)
        except Exception:
            onAPIError("getTaskChunkFromSisMargaret", retriesLeft)
            retriesLeft -= 1


def finishTaskChunkOnSisMargaret(mqtt: ThreadsafeMQTTClient, taskChunk: TaskChunk, retriesLeft = API_DEF_RETRIES):
    while True:
        try:
            payload = json.dumps({
                "taskChunkId": taskChunk.taskChunkId,
                "taskResults": [
                    {
                        "curvesRan": t.curvesRan,
                        "taskRuntime": t.taskRuntime,
                    } for t in taskChunk.tasks
                ],
                "runtime": taskChunk.taskChunkRuntime
            }, separators=(',', ':'))
            mqtt.publishThreadsafe("finishedchunk", payload)
            return True
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


def submitSolutionToSisMargaret(mqtt: ThreadsafeMQTTClient, candidateId: int, N: int, factor1: int, factor2: int, taskChunkId = 0, retriesLeft = API_DEF_RETRIES):
    if type(N) != int or type(factor1) != int or type(factor2) != int:
        print(f"submitSolutionToSisMargaret: Invalid arguments for candidate {candidateId} ({N} = {factor1} * {factor2})")
        return False

    if factor1 > factor2 or factor1 * factor2 != N:
        print(f"submitSolutionToSisMargaret: Invalid solution for candidate {candidateId} ({N} = {factor1} * {factor2})")
        return False

    if not is_prime(factor1):
        if len(str(factor1)) <= 50:
            from ecm import factorCandidateViaYAFU
            try:
                attempt = 1
                while True:
                    assert attempt <= 5
                    print(f"submitSolutionToSisMargaret: Trying to factorize {factor1 = } ({candidateId = }, {N = })")
                    workdir = f"{DEFAULT_YAFU_WORKDIR}_{candidateId}"
                    factor1 = factorCandidateViaYAFU(Candidate(0, 0, factor1), workdir=workdir)[-1]
                    try:
                        shutil.rmtree(workdir)
                    except Exception:
                        pass

                    assert factor1 > 1 and N % factor1 == 0
                    if is_prime(factor1):
                        break
                    attempt += 1
                factor2 = N // factor1
            except Exception:
                print(f"submitSolutionToSisMargaret: Failed to factorize {factor1 = } ({candidateId = }, {N = })")
                return False
        else:
            print(f"submitSolutionToSisMargaret: Invalid solution {N} = {factor1} * {factor2}")
            return False


    print(f"submitSolutionToSisMargaret: Submitting solution for candidate {candidateId} ({N} = {factor1} * {factor2})")
    while True:
        try:
            payload = json.dumps({
                "machineID": MACHINE_ID,
                "commit": GIT_VERSION,
                "taskChunkId": taskChunkId,
                "factor1": str(factor1),
                "factor2": str(factor2),
                "candidateId": candidateId,
            }, separators=(',', ':'))
            mqtt.publishThreadsafe("solution", payload)
            return True
        except Exception:
            onAPIError("submitSolutionToSisMargaret", retriesLeft)
            retriesLeft -= 1


def getHeightFromSisMargaret(retriesLeft = API_DEF_RETRIES):
    while True:
        try:
            url = SISMARGARET_API_BASE + "height/version/2"
            ret = API_SESSION.get(url).text
            print(f"Current block height: {ret}")
            return int(ret)
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
    assert isinstance(candidateIds, list)
    while True:
        try:
            url = SISMARGARET_API_BASE + "candidates/active"
            resp = API_SESSION.post(url, data=str(candidateIds))
            return resp.json()
        except Exception:
            onAPIError("areCandidatesActiveOnSisMargaret", retriesLeft)
            retriesLeft -= 1


def getMQTTCredentialsFromSisMargaret(retriesLeft = API_DEF_RETRIES):
    while True:
        try:
            url = SISMARGARET_API_BASE + "credentials/version/1"
            ret = API_SESSION.get(url).json()
            username = ret["username"]
            password = ret["password"]

            return username, password
        except Exception:
            onAPIError("getMQTTCredentialsFromSisMargaret", retriesLeft)
            retriesLeft -= 1
