import time
import traceback
from threading import Lock, Thread
import random

from ecm import conductECMViaYAFU, conductECMViaCUDAECM, stopYAFU, stopCUDAECM
from api import submitSolutionToSisMargaret, getHeightFromSisMargaret, getCandidateFromSisMargaret, isCandidateActiveOnSisMargaret, getAllCandidatesFromSisMargaret
from config import SIEVER_MODE, API_CANDIDATE_GEN_WAIT_TIME
from candidate import Candidate


class Manager:
    def __init__(self):
        self.height = getHeightFromSisMargaret()
        self.gpuHeight = None
        self.cpuCandidate: Candidate = None
        self.cpuCandidateLock = Lock()


    def startCUDAECMWorker(self):
        while True:
            self.gpuHeight = self.height
            cands = getAllCandidatesFromSisMargaret()
            if len(cands) == 0:
                waitTime = random.uniform(*API_CANDIDATE_GEN_WAIT_TIME)
                print(f"startCUDAECMWorker: No candidates to run. Retrying after {waitTime:.1f}s")
                time.sleep(waitTime)
                continue
            conductECMViaCUDAECM(self, getAllCandidatesFromSisMargaret())
            time.sleep(0.1)


    def heightCheckWorker(self):
        while True:
            try:
                height = getHeightFromSisMargaret()
                if height != self.height:
                    print("heightCheckWorker: Race lost. Aborting all candidates")
                    self.height = height
                    with self.cpuCandidateLock:
                        if self.cpuCandidate is not None and self.cpuCandidate.height != height:
                            self.cpuCandidate.active = False
                            self.cpuCandidate = None
                            stopYAFU()

                    if SIEVER_MODE == 1 and self.gpuHeight != height:
                        stopCUDAECM()
                time.sleep(5)
            except Exception:
                traceback.print_exc()


    def cpuCandidateActiveCheckWorker(self):
        while True:
            try:
                if self.cpuCandidate is not None:
                    id = self.cpuCandidate.id
                    if not isCandidateActiveOnSisMargaret(self.cpuCandidate):
                        self.cpuCandidateLock.acquire()
                        if self.cpuCandidate is None or id != self.cpuCandidate.id:
                            self.cpuCandidateLock.release()
                            time.sleep(5)
                            continue

                        print("cpuCandidateActiveCheckWorker: CPU candidate is no longer active")
                        self.cpuCandidate.active = False
                        self.cpuCandidate = None
                        stopYAFU()
                        self.cpuCandidateLock.release()
                time.sleep(5)
            except Exception:
                traceback.print_exc()


    def start(self):
        Thread(target=self.heightCheckWorker, daemon=True).start()
        if SIEVER_MODE == 0:
            pass
            # Thread(target=self.cpuCandidateActiveCheckWorker, daemon=True).start()
        elif SIEVER_MODE == 1:
            Thread(target=self.startCUDAECMWorker, daemon=True).start()

        while True:
            if SIEVER_MODE == 1:
                # CPU ECM is disabled, just chill
                time.sleep(100)
                continue

            try:
                with self.cpuCandidateLock:
                    self.cpuCandidate = getCandidateFromSisMargaret()
                factors = conductECMViaYAFU(self.cpuCandidate)
                with self.cpuCandidateLock:
                    if self.cpuCandidate is None or (not self.cpuCandidate.active) or len(factors) < 2:
                        continue

                    factor1 = factors[0]
                    factor2 = self.cpuCandidate.N // factor1
                    Thread(target=submitSolutionToSisMargaret, args=(self.cpuCandidate, factor1, factor2), daemon=True).start()
                    self.cpuCandidate.active = False
                    self.cpuCandidate = None
            except Exception:
                traceback.print_exc()


myManager = Manager()
