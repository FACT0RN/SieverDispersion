import time
from threading import Lock
import json
import traceback
import random
import uuid

import paho.mqtt.client as mqtt_client


class ThreadsafeMQTTClient():
    def __init__(self, mqttTopicCallbacks):
        self.mqttTopicCallbacks = mqttTopicCallbacks

        self.mqttConnected = False
        self.mqttConnectionFailed = False
        self.mqttClient = None
        self.mqttClientLock = Lock()

        self.mqttUsername = None
        self.mqttPassword = None


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
        if msg.topic in self.mqttTopicCallbacks:
            self.mqttTopicCallbacks[msg.topic](json.loads(msg.payload.decode()))
        else:
            print(f"onMQTTMessage: Ignoring unknown topic '{msg.topic}'")


    def connectToMQTT(self):
        if self.mqttUsername is None or self.mqttPassword is None:
            from api import getMQTTCredentialsFromSisMargaret
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


    def publishThreadsafe(self, topic, payload):
        while not self.mqttConnected or self.mqttConnectionFailed:
            time.sleep(0.01)

        with self.mqttClientLock:
            self.mqttClient.publish(topic, payload)
