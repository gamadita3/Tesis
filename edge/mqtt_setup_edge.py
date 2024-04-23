import json
import cv2
import paho.mqtt.client as mqtt
import time
import base64

class MQTTSetup:
    def __init__(self):
        self.mqttConfig = self.load_config('../util/mqtt_config.json')
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.frame_count = 0
        
    def load_config(self, path):
        with open(path, 'r', encoding='utf-8') as file:
            return json.load(file)

    def connect(self):
        self.client.connect(self.mqttConfig["HOST_ADDRESS"], self.mqttConfig["PORT"], keepalive=60)
        self.client.loop_start()

    def on_connect(self, client, userdata, flags, rc):
        print("Connecting MQTT to host : ", self.mqttConfig["HOST_ADDRESS"])
        if rc == 0:
            print("Connected to MQTT host !")
        else:
            print("Failed to connect, return code %d\n", rc)

    def on_disconnect(self, client, userdata, rc):
        print("Unexpected MQTT disconnection!")

    def on_message(self, client, userdata, message):
        pass

    def on_publish(self, client, userdata, mid):
        print(f"Message published successfully, Message ID: {mid}")

    def publish(self, topic, payload):
        result, mid = self.client.publish(topic, payload, qos=0)
        if result == mqtt.MQTT_ERR_SUCCESS:
            print(f"Publish initiated for Message ID: {mid} for topic {topic}")
        else:
            print(f"Failed to initiate publish for topic {topic}, error code: {result}")
        
    def publish_frame(self, frame):
        encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), 50]
        height, width = frame.shape[:2]
        print(f"Publishing frame with resolution: {width}x{height}")
        
        _, frame_encoded = cv2.imencode(".jpg", frame, encode_params)
        
        # Convert frame to bytes for publishing
        frame_bytes = frame_encoded.tobytes()
        print("Size of byte array:", len(frame_bytes), "bytes")
        frame_base64 = base64.b64encode(frame_bytes).decode("utf-8")
        
        timestamp = time.time()
        print("Publish timestamp: ", timestamp)
        
        mqtt_message = {
            "frame": frame_base64,
            "timestamp": timestamp
        }
        
        # Serialize the data to JSON
        mqtt_payload = json.dumps(mqtt_message)
        
        #print("encode:", frame_encoded)
        self.publish(self.mqttConfig["TOPIC_FRAME"], mqtt_payload)
        self.frame_count += 1
        print("Total frame sent:", self.frame_count)

    def publish_detection(self, total_detections):
        print(f'Publishing total detections')
        self.publish(self.mqttConfig["TOPIC_INFO"], total_detections)
        
    def publish_timestamp(self):
        timestamp = time.time()
        print("Publish timestamp")
        self.publish(self.mqttConfig["TOPIC_FRAME"], timestamp)