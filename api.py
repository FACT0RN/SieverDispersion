import requests
from gmpy2 import is_prime
import traceback
import time
import random
import functools
import os

from config import IS_DOCKER, SCRIPT_FOLDER, API_DEF_RETRIES, API_MAX_TIMEOUT, API_CANDIDATE_GEN_WAIT_TIME
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


def getCandidateFromSisMargaret(retriesLeft = API_DEF_RETRIES):
    while True:
        try:
            url = SISMARGARET_API_BASE + "candidate"
            ret = API_SESSION.get(url).json()
            if "n" in ret:
                print(f"getCandidateFromSisMargaret: Got new candidate {ret}")
                return Candidate(ret["id"], ret["height"], int(ret["n"]))
            else:
                waitTime = random.uniform(*API_CANDIDATE_GEN_WAIT_TIME)
                print(f"getCandidateFromSisMargaret: No candidate available. Retrying in {waitTime:.1f}s")
                time.sleep(waitTime)
        except Exception:
            onAPIError("getCandidateFromSisMargaret", retriesLeft)
            retriesLeft -= 1


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
            payload = f'{{"factor1":"{factor1}","factor2":"{factor2}","candidateId":{candidate.id}}}'
            url = SISMARGARET_API_BASE + "solution"
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


def isCandidateActiveOnSisMargaret(candidateId: int, retriesLeft = API_DEF_RETRIES):
    while True:
        try:
            url = SISMARGARET_API_BASE + f"candidate/{candidateId}/active"
            resp = API_SESSION.get(url).text
            print("isCandidateActiveOnSisMargaret: Response:", resp)
            return resp == "true"
        except Exception:
            onAPIError("isCandidateActiveOnSisMargaret", retriesLeft)
            retriesLeft -= 1
