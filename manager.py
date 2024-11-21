import time
import traceback
from threading import Lock, Thread
import random

from ecm import performECMViaYAFU, performECMViaCUDAECM, stopYAFU, stopCUDAECM
from api import submitSolutionToSisMargaret, getHeightFromSisMargaret, areCandidatesActiveOnSisMargaret
from api import getTaskChunkFromSisMargaret, finishTaskChunkOnSisMargaret
from config import SIEVER_MODE
from taskChunk import TaskChunk


class Manager:
    def __init__(self):
        self.height = getHeightFromSisMargaret()
        self.taskChunk: TaskChunk = None
        self.taskChunkType = ["cpu", "gpu"][SIEVER_MODE]
        self.taskChunkLock = Lock()


    def heightCheckWorker(self):
        while True:
            try:
                height = getHeightFromSisMargaret()
                if height != self.height:
                    print("heightCheckWorker: Race lost. Aborting all candidates")
                    self.height = height
                    with self.taskChunkLock:
                        if self.taskChunk is not None and self.taskChunk.height != height:
                            self.taskChunk.abort()
                            [stopYAFU, stopCUDAECM][SIEVER_MODE]()
                time.sleep(5)
            except Exception:
                traceback.print_exc()


    def cpuCandidateActiveCheckWorker(self):
        while True:
            try:
                if self.taskChunk is not None:
                    ids = set(task.candidateIds[0] for task in self.taskChunk.tasks)
                    result = areCandidatesActiveOnSisMargaret(list(ids))
                    inactiveIds = set(id for id, active in result.items() if not active)

                    if len(inactiveIds) == 0:
                        time.sleep(5)
                        continue

                    with self.taskChunkLock:
                        if self.taskChunk is not None:
                            for task in self.taskChunk.tasks:
                                if task.candidateIds[0] in inactiveIds:
                                    print(f"cpuCandidateActiveCheckWorker: Candidate {task.candidateIds[0]} is no longer active, aborting relevant task")
                                    task.active = False
                                    if task.ongoing:
                                        print(f"cpuCandidateActiveCheckWorker: The relevant task is ongoing, stopping YAFU")
                                        stopYAFU()
                time.sleep(5)
            except Exception:
                traceback.print_exc()


    def start(self):
        Thread(target=self.heightCheckWorker, daemon=True).start()
        if SIEVER_MODE == 0:
            Thread(target=self.cpuCandidateActiveCheckWorker, daemon=True).start()

        while True:
            try:
                with self.taskChunkLock:
                    self.taskChunk = getTaskChunkFromSisMargaret(self.taskChunkType)

                self.taskChunk.startedAt = time.time()
                submitThreads = []
                for task in self.taskChunk.tasks:
                    if self.taskChunk.height != self.height:
                        break

                    if not task.active:
                        continue

                    factorsList = [performECMViaYAFU, performECMViaCUDAECM][SIEVER_MODE](task)
                    with self.taskChunkLock:
                        if not task.active:
                            continue

                        for i, factors in enumerate(factorsList):
                            if len(factors) < 2:
                                continue

                            factor1 = factors[0]
                            factor2 = task.Ns[i] // factor1
                            submitThreads.append(Thread(target=submitSolutionToSisMargaret, args=(task.candidateIds[i], task.Ns[i], factor1, factor2),
                                                        kwargs={"taskChunkId": self.taskChunk.taskChunkId}, daemon=True))
                            submitThreads[-1].start()

                self.taskChunk.taskChunkRuntime = time.time() - self.taskChunk.startedAt
                finishTaskChunkOnSisMargaret(self.taskChunk)
                self.taskChunk = None

                for t in submitThreads:
                    t.join()
            except Exception:
                traceback.print_exc()


myManager = Manager()
