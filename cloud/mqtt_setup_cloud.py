import json
import cv2
import base64
import paho.mqtt.client as mqtt
import numpy as np
import traceback
import ntplib
import time

class MQTTSetup:
    def __init__(self):
        self.mqttConfig = self.load_config('../util/mqtt_config.json')
        self.client = mqtt.Client()
        self.ntpClient = ntplib.NTPClient()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.latest_frame = None    
        self.empty_detection = 0
        self.occupied_detection = 0 
        self.frame_id = 1
        
    def load_config(self, path):
        with open(path, 'r', encoding='utf-8') as file:
            return json.load(file)

    def connect(self):
        self.client.connect(self.mqttConfig["HOST_ADDRESS"], self.mqttConfig["PORT"], keepalive=60)
        self.client.subscribe([(self.mqttConfig["TOPIC_FRAME"], self.mqttConfig["QOS"])])
        self.client.loop_start()

    def on_connect(self, client, userdata, flags, rc):
        print("Connecting MQTT to host: ", self.mqttConfig["HOST_ADDRESS"])
        if rc == 0:
            print("Connected to MQTT host !")
        else:
            print("Failed to connect, return code %d\n", rc)

    def on_disconnect(self, client, userdata, rc):
        print("Unexpected MQTT disconnection!")

    def on_message(self, client, userdata, message):
        try:
            server_timestamp = time.time()
            if message.topic == self.mqttConfig["TOPIC_FRAME"]:
                self.payload_size = len(message.payload)  # Get the size of the payload in bytes
                mqtt_message = json.loads(message.payload)
                
                # Extract the frame and timestamp
                self.frame_id = mqtt_message["id"]
                self.empty_detection = mqtt_message["empty_detection"]
                self.occupied_detection = mqtt_message["occupied_detection"]
                frame_base64 = mqtt_message["frame"]
                client_timestamp = mqtt_message["timestamp"]
                
                self.duration = f"{(server_timestamp - client_timestamp)*1000}"
                           
                print(f"Transmission duration for id {self.frame_id - 1} : {self.duration}")
                print(f"Payload size for id {self.frame_id - 1} : {self.payload_size / 1000} kilobytes")
 
                self.decode_frame_payload(frame_base64) 
                
            elif message.topic == self.mqttConfig["TOPIC_INFO"]: 
                print("Received info:", message.payload.decode('utf-8'))               
        except Exception:
            print(f"Error on_message:", print(traceback.format_exc()))


    def on_publish(self, client, userdata, mid):
        print(f"Message published successfully, Message ID: {mid}")

    def publish(self, topic, payload):
        result, mid = self.client.publish(topic, payload)
        if result == mqtt.MQTT_ERR_SUCCESS:
            print(f"Publish initiated for Message ID: {mid}")
        else:
            print(f"Failed to initiate publish, error code: {result}")
            
    def decode_frame_payload(self, payload):
        payload_decode = base64.b64decode(payload)
        frame_data = np.frombuffer(payload_decode, np.uint8)
        frame_decode = cv2.imdecode(frame_data, cv2.IMREAD_COLOR)
        self.latest_frame =  frame_decode