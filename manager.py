import time
import traceback
from threading import Lock, Thread
import random
import paho.mqtt.client as mqtt_client
import json
import uuid

from ecm import performECMViaYAFU, performECMViaCUDAECM, stopYAFU, stopCUDAECM
from api import submitSolutionToSisMargaret, getHeightFromSisMargaret
from api import getTaskChunkFromSisMargaret, finishTaskChunkOnSisMargaret, getMQTTCredentialsFromSisMargaret
from config import SIEVER_MODE
from taskChunk import TaskChunk


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

        self.mqttConnected = False
        self.mqttConnectionFailed = False
        self.mqttClient = None

        self.mqttUsername = None
        self.mqttPassword = None


    def connectToMQTT(self):
        if self.mqttUsername is None or self.mqttPassword is None:
            self.mqttUsername, self.mqttPassword = getMQTTCredentialsFromSisMargaret()

        BROKER = "sismargaret.fact0rn.io"
        PORT = 1883

        CLIENT_ID = str(uuid.uuid4())
        USERNAME = self.mqttUsername
        PASSWORD = self.mqttPassword

        while not self.mqttConnected or self.mqttConnectionFailed:
            if self.mqttClient is not None:
                try:
                    self.mqttClient.loop_stop()
                    self.mqttClient.disconnect()
                except Exception:
                    pass
                self.mqttClient = None
            self.mqttConnected = False
            self.mqttConnectionFailed = False

            self.mqttClient = mqtt_client.Client(mqtt_client.CallbackAPIVersion.VERSION2, CLIENT_ID)
            self.mqttClient.username_pw_set(USERNAME, PASSWORD)
            self.mqttClient.on_connect = self.onMQTTConnect
            self.mqttClient.on_disconnect = self.onMQTTDisconnect
            self.mqttClient.on_message = self.onMQTTMessage
            try:
                self.mqttClient.connect(BROKER, PORT, keepalive=120)
                self.mqttClient.loop_start()

                while not self.mqttConnected:
                    time.sleep(0.01)
            except Exception:
                traceback.print_exc()
                self.mqttConnected = False
                self.mqttConnectionFailed = True

                retryIn = random.randint(15, 60)
                print(f"MQTT connection failed. Retrying in {retryIn}s...")
                time.sleep(retryIn)


    def onMQTTConnect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0 and self.mqttClient.is_connected():
            print("Connected to MQTT Broker!")
            for topic in self.mqttTopicCallbacks.keys():
                self.mqttClient.subscribe(topic)
            self.mqttConnectionFailed = False
        else:
            print(f"Failed to connect, {reason_code = }")
            self.mqttConnectionFailed = True
        self.mqttConnected = True


    def onMQTTDisconnect(self, client, userdata, flags, reason_code, properties):
        self.mqttConnectionFailed = True

        FIRST_RECONNECT_DELAY = 1
        RECONNECT_RATE = 2
        MAX_RECONNECT_DELAY = 60

        print(f"Disconnected with {reason_code = }")
        reconnect_count, reconnect_delay = 0, FIRST_RECONNECT_DELAY
        while True:
            print(f"Reconnecting in {reconnect_delay}s...")
            time.sleep(reconnect_delay)

            try:
                self.mqttClient.reconnect()
                print("Reconnected successfully!")
                return
            except Exception:
                traceback.print_exc()
                print("Reconnect failed. Retrying...")

            reconnect_delay *= RECONNECT_RATE
            reconnect_delay = min(reconnect_delay, MAX_RECONNECT_DELAY)
            reconnect_count += 1


    def onMQTTMessage(self, client, userdata, msg):
        payload = msg.payload.decode()
        received_json = json.loads(payload)

        if msg.topic in self.mqttTopicCallbacks:
            self.mqttTopicCallbacks[msg.topic](received_json)
        else:
            print(f"onMQTTMessage: Ignoring unknown topic '{msg.topic}'")


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
        self.connectToMQTT()

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
                            submitThreads.append(Thread(target=submitSolutionToSisMargaret, args=(self.mqttClient, task.candidateIds[i], task.Ns[i], factor1, factor2),
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
