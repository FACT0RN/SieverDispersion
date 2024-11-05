import requests
from gmpy2 import is_prime
import traceback
import time
import random
import functools
import os

from config import IS_DOCKER, SCRIPT_FOLDER, API_DEF_RETRIES, API_MAX_TIMEOUT, API_CANDIDATE_GEN_WAIT_TIME, GIT_VERSION, API_CPU_ACCEPT_THRESHOLD
from candidate import Candidate

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


def getCandidateFromSisMargaret(retriesLeft = API_DEF_RETRIES, skipAmountCheck = False):
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
                url = SISMARGARET_API_BASE + "candidate/version/1"
                ret = API_SESSION.get(url).json()
                if "n" in ret:
                    print(f"getCandidateFromSisMargaret: Got new candidate {ret}")
                    return Candidate(ret["id"], ret["height"], int(ret["n"]))
                else:
                    waitReason = "No candidate available"

            waitTime = random.uniform(*API_CANDIDATE_GEN_WAIT_TIME)
            print(f"getCandidateFromSisMargaret: {waitReason}. Retrying in {waitTime:.1f}s")
            time.sleep(waitTime)
        except Exception:
            onAPIError("getCandidateFromSisMargaret", retriesLeft)
            retriesLeft -= 1


def getAllCandidatesFromSisMargaret(retriesLeft = API_DEF_RETRIES):
    while True:
        try:
            url = SISMARGARET_API_BASE + "candidates"
            ret = API_SESSION.get(url).json()
            ret = [Candidate(c["id"], c["height"], int(c["n"])) for c in ret]
            return ret
        except Exception:
            onAPIError("getAllCandidatesFromSisMargaret", retriesLeft)


def submitSolutionToSisMargaret(candidate: Candidate, factor1: int, factor2: int, retriesLeft = API_DEF_RETRIES):
    N = candidate.N

    if type(N) != int or type(factor1) != int or type(factor2) != int:
        print(f"submitSolutionToSisMargaret: Invalid arguments {N}, {factor1}, {factor2}")
        return False

    if not is_prime(factor1) or factor1 > factor2 or factor1 * factor2 != N:
        print(f"submitSolutionToSisMargaret: Invalid solution {N} = {factor1} * {factor2}")
        return False

    print(f"submitSolutionToSisMargaret: Submitting {N} = {factor1} * {factor2}")
    while True:
        try:
            payload = f'{{"commit":"{GIT_VERSION}","factor1":"{factor1}","factor2":"{factor2}","candidateId":{candidate.id}}}'
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


def areCandidatesActiveOnSisMargaret(candidates: list[Candidate], retriesLeft = API_DEF_RETRIES) -> dict[str, bool]:
    while True:
        try:
            url = SISMARGARET_API_BASE + "candidates/active"
            payload = str([c.id for c in candidates])
            print(payload)
            resp = API_SESSION.post(url, data=payload)
            return resp.json()
        except Exception:
            onAPIError("areCandidatesActiveOnSisMargaret", retriesLeft)
            retriesLeft -= 1
