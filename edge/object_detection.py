import cv2
from ultralytics import YOLO
import os
import json
import traceback
import threading
import time

class Inference:
    def __init__(self):
        self.dirConfig= self.load_config('../util/dir_config.json')
        self.frameConfig= self.load_config('../util/frame_config.json')
        self.model_path = self.dirConfig["MODEL"]
        self.model = YOLO(self.model_path)
        self.class_list = self.load_labels(self.dirConfig["LABEL"])
        self.detection_colors = [(10, 255, 10), (10, 10, 255)] # green and red colors for bounding boxes
        self.total_object_detection = 0
        self.false_positive = 0
        self.false_negative = 0
        self.total_empty_detection = 0
        self.total_occupied_detection = 0
        self.frame = None
        self.last_model_update_time = os.path.getmtime(self.model_path)
        self.model_update_timer()
        
    def load_config(self, path):
        with open(path, 'r', encoding='utf-8') as file:
            return json.load(file)

    def load_labels(self, label_path):
        with open(label_path, "r") as file:
            return file.read().split("\n")  
        
    def model_update_timer(self):
        threading.Timer(self.frameConfig["UPDATE_DELAY"], self.model_update_timer).start()
        self.update_model()

    def update_model(self):
        try:
            current_time = os.path.getmtime(self.model_path)
            if current_time != self.last_model_update_time:
                self.last_model_update_time = current_time
                new_model = YOLO(self.model_path)  # Attempt to load the new model
                self.model = new_model  # Assign the new model only if loaded successfully
        except Exception:
                print("Error update model:", print(traceback.format_exc()))

    def detect(self, frame):
        self.total_empty_detection = 0
        self.total_occupied_detection = 0
        
        detections = self.model(source=frame, task="detect", imgsz=self.frameConfig["IMGSZ"], conf=self.frameConfig["CONFIDENCE"])
        self.total_object_detection += 1
        DP = detections[0].numpy()
        total_detection = len(DP)
        print("Total detection:", total_detection)
        
        for i in range(len(DP)):
            try:
                boxes = detections[0].boxes
                box = boxes[i]  # returns one box
                clsID = box.cls.numpy()[0]
                conf = box.conf.numpy()[0]
                bb = box.xyxy.numpy()[0]
                
                if clsID == 0:
                    self.total_empty_detection += 1
                else:
                    self.total_occupied_detection += 1
                
                cv2.rectangle(frame, (int(bb[0]), int(bb[1])), (int(bb[2]), int(bb[3])), self.detection_colors[int(clsID)], 3)
                cv2.putText(frame, f"{self.class_list[int(clsID)]} {conf:.3f}%", (int(bb[0]), int(bb[1]) - 10), cv2.FONT_HERSHEY_PLAIN, 1, (255, 255, 255), 2)
            except Exception:
                print("Error Inference:", print(traceback.format_exc()))
                break

        self.check_detection_anomalies(DP, frame)
        self.frame = frame

    def check_detection_anomalies(self, detections, frame):
        if len(detections) > 12:
            self.handle_false_positive(frame)
        elif len(detections) < 12:
            self.handle_false_negative(frame)

        print("Empty:", self.total_empty_detection)
        print("Occupied:", self.total_occupied_detection)

    def handle_false_positive(self, frame):
        self.false_positive += 1
        filename = f"fp_{self.false_positive}_empty{self.total_empty_detection}_occ{self.total_occupied_detection}.jpg"
        save_path = os.path.join(self.dirConfig["FALSEPOSITIVE"], filename)
        cv2.imwrite(save_path, frame)

    def handle_false_negative(self, frame):
        self.false_negative += 1
        filename = f"fn_{self.false_negative}_empty{self.total_empty_detection}_occ{self.total_occupied_detection}.jpg"
        save_path = os.path.join(self.dirConfig["FALSENEGATIVE"], filename)
        cv2.imwrite(save_path, frame)
