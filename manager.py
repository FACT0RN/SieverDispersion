import time
import traceback
from threading import Lock, Thread
import random

from ecm import performECMViaYAFU, conductECMViaCUDAECM, stopYAFU, stopCUDAECM
from api import submitSolutionToSisMargaret, getHeightFromSisMargaret, areCandidatesActiveOnSisMargaret, getAllCandidatesFromSisMargaret
from api import getTaskChunkFromSisMargaret, finishTaskChunkOnSisMargaret
from config import SIEVER_MODE, API_CANDIDATE_GEN_WAIT_TIME
from taskChunk import TaskChunk


class Manager:
    def __init__(self):
        self.height = getHeightFromSisMargaret()
        self.gpuHeight = None
        self.cpuTaskChunk: TaskChunk = None
        self.cpuTaskChunkLock = Lock()


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
                    with self.cpuTaskChunkLock:
                        if self.cpuTaskChunk is not None and self.cpuTaskChunk.height != height:
                            self.cpuTaskChunk.abort()
                            self.cpuTaskChunk = None

                    if SIEVER_MODE == 1 and self.gpuHeight != height:
                        stopCUDAECM()
                time.sleep(5)
            except Exception:
                traceback.print_exc()


    def cpuCandidateActiveCheckWorker(self):
        while True:
            try:
                if self.cpuTaskChunk is not None:
                    ids = set(task.candidateId for task in self.cpuTaskChunk.tasks)
                    result = areCandidatesActiveOnSisMargaret(ids)
                    inactiveIds = set(id for id, active in result.items() if not active)

                    if len(inactiveIds) == 0:
                        time.sleep(5)
                        continue

                    with self.cpuTaskChunkLock:
                        if self.cpuTaskChunk is not None:
                            for task in self.cpuTaskChunk.tasks:
                                if task.candidateId in inactiveIds:
                                    print(f"cpuCandidateActiveCheckWorker: Candidate {task.candidateId} is no longer active, aborting task {task.taskId}")
                                    task.active = False
                                    if task.ongoing:
                                        print(f"cpuCandidateActiveCheckWorker: Task {task.taskId} is ongoing, stopping YAFU")
                                        stopYAFU()
                time.sleep(5)
            except Exception:
                traceback.print_exc()


    def start(self):
        Thread(target=self.heightCheckWorker, daemon=True).start()
        if SIEVER_MODE == 0:
            Thread(target=self.cpuCandidateActiveCheckWorker, daemon=True).start()
        elif SIEVER_MODE == 1:
            Thread(target=self.startCUDAECMWorker, daemon=True).start()

        while True:
            if SIEVER_MODE == 1:
                # CPU ECM is disabled, just chill
                time.sleep(100)
                continue

            try:
                with self.cpuTaskChunkLock:
                    self.cpuTaskChunk = getTaskChunkFromSisMargaret()

                self.cpuTaskChunk.startedAt = time.time()
                for task in self.cpuTaskChunk.tasks:
                    if self.cpuTaskChunk.height != self.height:
                        break

                    if not task.active:
                        continue

                    factors = performECMViaYAFU(task)
                    with self.cpuTaskChunkLock:
                        if not task.active or len(factors) < 2:
                            continue

                        factor1 = factors[0]
                        factor2 = task.N // factor1
                        Thread(target=submitSolutionToSisMargaret, args=(task.candidateId, task.N, factor1, factor2),
                               kwargs={"taskId": task.taskId}, daemon=True).start()

                self.cpuTaskChunk.taskChunkRuntime = time.time() - self.cpuTaskChunk.startedAt
                finishTaskChunkOnSisMargaret(self.cpuTaskChunk)
                self.cpuTaskChunk = None
            except Exception:
                traceback.print_exc()


myManager = Manager()
