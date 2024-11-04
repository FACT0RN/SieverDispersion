import time
import traceback
from threading import Lock, Thread

from ecm import conductECMViaYAFU, conductECMViaCUDAECM, stopYAFU, stopCUDAECM, resetWorkdir
from api import submitSolutionToSisMargaret, getHeightFromSisMargaret, getCandidateFromSisMargaret, isCandidateActiveOnSisMargaret, getAllCandidatesFromSisMargaret
from config import SIEVER_MODE, DEFAULT_WORKDIR
from candidate import Candidate


class Manager:
    def __init__(self):
        self.height = getHeightFromSisMargaret()
        self.cpuCandidate: Candidate = None
        self.cpuCandidateLock = Lock()


    def startCUDAECMWorker(self):
        height = None
        while True:
            if height != self.height:
                height = self.height
                conductECMViaCUDAECM(self, getAllCandidatesFromSisMargaret())
            time.sleep(0.1)


    def heightCheckWorker(self):
        while True:
            try:
                height = getHeightFromSisMargaret()
                if height > self.height:
                    print("heightCheckWorker: Race lost. Aborting all candidates")
                    self.cpuCandidateLock.acquire()
                    self.cpuCandidate.active = False
                    self.cpuCandidate = None
                    self.height = height
                    stopYAFU()
                    if SIEVER_MODE == 1:
                        stopCUDAECM()
                    self.cpuCandidateLock.release()
                    resetWorkdir(DEFAULT_WORKDIR)
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
        Thread(target=self.startCUDAECMWorker, daemon=True).start()
        # Thread(target=self.cpuCandidateActiveCheckWorker, daemon=True).start()
        resetWorkdir(DEFAULT_WORKDIR)
        while True:
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
