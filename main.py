#!/usr/bin/python3
import time
import traceback
from threading import Lock, Thread

from ecm import conductECMViaYAFU, stopYAFU, resetWorkdir
from api import submitSolutionToSisMargaret, getHeightFromSisMargaret, getCandidateFromSisMargaret, isCandidateActiveOnSisMargaret
from config import DEFAULT_WORKDIR
from candidate import Candidate

cpuCandidate: Candidate = None
candidateLock = Lock()


def heightCheckWorker():
    global cpuCandidate, candidateLock
    while True:
        try:
            if cpuCandidate is not None:
                height = getHeightFromSisMargaret()
                candidateLock.acquire()
                if cpuCandidate is not None and height > cpuCandidate.height:
                    print("heightCheckWorker: Race lost. Aborting all candidates")
                    cpuCandidate.active = False
                    cpuCandidate = None
                    candidateLock.release()
                    stopYAFU()
                    resetWorkdir(DEFAULT_WORKDIR)
                else:
                    candidateLock.release()
            time.sleep(5)
        except Exception:
            traceback.print_exc()


def cpuCandidateActiveCheckWorker():
    global cpuCandidate, candidateLock
    while True:
        try:
            if cpuCandidate is not None:
                id = cpuCandidate.id
                if not isCandidateActiveOnSisMargaret(id):
                    candidateLock.acquire()
                    if cpuCandidate is None or id != cpuCandidate.id:
                        candidateLock.release()
                        time.sleep(5)
                        continue

                    print("cpuCandidateActiveCheckWorker: CPU candidate is no longer active")
                    cpuCandidate.active = False
                    cpuCandidate = None
                    candidateLock.release()
                    stopYAFU()
                    resetWorkdir(DEFAULT_WORKDIR)
            time.sleep(5)
        except Exception:
            traceback.print_exc()


if __name__ == "__main__":
    Thread(target=heightCheckWorker, daemon=True).start()
    Thread(target=cpuCandidateActiveCheckWorker, daemon=True).start()
    resetWorkdir(DEFAULT_WORKDIR)
    while True:
        try:
            with candidateLock:
                cpuCandidate = getCandidateFromSisMargaret()
            factors = conductECMViaYAFU(cpuCandidate)
            with candidateLock:
                if cpuCandidate is None or (not cpuCandidate.active) or len(factors) < 2:
                    continue

                factor1 = factors[0]
                factor2 = cpuCandidate.N // factor1
                submitSolutionToSisMargaret(cpuCandidate, factor1, factor2)
                cpuCandidate.active = False
                cpuCandidate = None
        except Exception:
            traceback.print_exc()
