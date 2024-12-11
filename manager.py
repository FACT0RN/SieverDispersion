import time
import traceback
from threading import Lock, Thread

from ecm import performECMViaYAFU, performECMViaCUDAECM, stopYAFU, stopCUDAECM
from api import submitSolutionToSisMargaret, getHeightFromSisMargaret
from api import getTaskChunkFromSisMargaret, finishTaskChunkOnSisMargaret
from config import SIEVER_MODE
from taskChunk import TaskChunk
from mqttClient import ThreadsafeMQTTClient


class Manager:
    def __init__(self):
        self.height = getHeightFromSisMargaret()
        self.taskChunk: TaskChunk = None
        self.taskChunkType = ["cpu", "gpu"][SIEVER_MODE]
        self.taskChunkLock = Lock()

        self.mqttTopicCallbacks = {
            "height": self.onHeightChanged,
            "solved": self.onCandidateSolved
        }
        self.mqtt = ThreadsafeMQTTClient(self.mqttTopicCallbacks)


    def onHeightChanged(self, obj):
        height = int(obj["height"])
        if height > self.height:
            print("onHeightChanged: Race lost. Aborting all candidates")
            self.height = height
            with self.taskChunkLock:
                if self.taskChunk is not None and self.taskChunk.height < height:
                    self.taskChunk.abort()
                    [stopYAFU, stopCUDAECM][SIEVER_MODE]()


    def onCandidateSolved(self, obj):
        if SIEVER_MODE != 0:
            return

        candidateId = int(obj["candidateId"])

        with self.taskChunkLock:
            if self.taskChunk is not None:
                for task in self.taskChunk.tasks:
                    if task.candidateIds[0] == candidateId:
                        print(f"onCandidateSolved: Candidate {task.candidateIds[0]} is no longer active, aborting relevant task")
                        task.active = False
                        if task.ongoing:
                            print(f"onCandidateSolved: The relevant task is ongoing, stopping YAFU")
                            stopYAFU()


    def start(self):
        self.mqtt.connectToMQTT()

        while True:
            try:
                with self.taskChunkLock:
                    self.taskChunk = getTaskChunkFromSisMargaret(self.taskChunkType)

                self.taskChunk.startedAt = time.time()
                submitThreads = []
                for task in self.taskChunk.tasks:
                    if self.taskChunk.height < self.height:
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

                            factor1 = factors[-2]
                            factor2 = task.Ns[i] // factor1
                            submitThreads.append(Thread(target=submitSolutionToSisMargaret, args=(self.mqtt, task.candidateIds[i], task.Ns[i], factor1, factor2),
                                                        kwargs={"taskChunkId": self.taskChunk.taskChunkId}, daemon=True))
                            submitThreads[-1].start()

                self.taskChunk.taskChunkRuntime = time.time() - self.taskChunk.startedAt
                finishTaskChunkOnSisMargaret(self.mqtt, self.taskChunk)
                self.taskChunk = None

                for t in submitThreads:
                    t.join()
            except Exception:
                traceback.print_exc()


myManager = Manager()
