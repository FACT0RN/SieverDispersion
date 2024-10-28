#!/usr/bin/python3
from ecm import conductECMViaYAFU, stopYAFU
from api import submitSolutionToSisMargaret, getHeightFromSisMargaret, getCandidateFromSisMargaret
import time
import traceback
from threading import Lock, Thread

candidate = None
candidateLock = Lock()


def heightCheckWorker():
    global candidate, candidateLock
    while True:
        try:
            if candidate is not None:
                height = getHeightFromSisMargaret()
                if height > candidate["height"]:
                    print("heightCheckWorker: Race lost. Aborting candidate")
                    with candidateLock:
                        candidate["aborted"] = True
                        candidate = None
                    stopYAFU()
            time.sleep(5)
        except Exception:
            traceback.print_exc()


if __name__ == "__main__":
    Thread(target=heightCheckWorker, daemon=True).start()
    while True:
        try:
            with candidateLock:
                candidate = getCandidateFromSisMargaret()
            factors = conductECMViaYAFU(candidate)
            with candidateLock:
                if candidate is None or candidate["aborted"] or len(factors) < 2:
                    continue

                factor1 = factors[0]
                factor2 = int(candidate["n"]) // factor1
                submitSolutionToSisMargaret(factor1, factor2)
        except Exception:
            traceback.print_exc()
