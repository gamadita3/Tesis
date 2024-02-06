import json
import os
import psutil
import time
import cv2
import csv
import psutil
import threading
from PIL import Image
from ultralytics import YOLO
from functools import wraps
mqttConfig = json.load(open(file="./util/mqtt_config.json", encoding="utf-8"))
frameConfig = json.load(open(file="./util/frame_config.json", encoding="utf-8"))
dirConfig = json.load(open(file="./util/dir_config.json", encoding="utf-8"))


#----------------------------CV2 show image-----------------------------------------#   
def show_images_opencv(window, frame):
    cv2.imshow(window, frame)
    cv2.waitKey(1)
    
 #----------------------------OPENCV GET VIDEO-----------------------------------------#   
def get_video():
    video_folder = dirConfig['VIDEO']
    return cv2.VideoCapture(video_folder)

video = get_video()

#----------------------------INFERENCE ULTRALYTICS-----------------------------------------#
label_file = open(dirConfig["LABEL"], "r")
class_list = label_file.read().split("\n")
label_file.close()

model = YOLO(dirConfig["MODEL"])
detection_colors = []
detection_colors.append((10, 255, 10))
detection_colors.append((10, 10, 255))
    
def inference(frame):
    print("Start Inference !!")  
    detecting = model(source=frame, imgsz=frameConfig["IMGSZ"])            
    DP = detecting[0].numpy()
    print("total detection :",len(DP))
    if len(DP) != 0:
        for i in range(len(DP)):
            try:
                boxes = detecting[0].boxes
                box = boxes[i]  # returns one box
                clsID = box.cls.numpy()[0]
                conf = box.conf.numpy()[0]
                bb = box.xyxy.numpy()[0]

                cv2.rectangle(
                    frame,
                    (int(bb[0]), int(bb[1])),
                    (int(bb[2]), int(bb[3])),
                    detection_colors[int(clsID)],
                    3,
                )

                # Display class name and confidence
                font = cv2.FONT_HERSHEY_PLAIN
                cv2.putText(
                    frame,
                    class_list[int(clsID)] + " " + str(round(conf, 3)) + "%",
                    (int(bb[0]), int(bb[1]) - 10),
                    font,
                    1,
                    (255, 255, 255),
                    2,
                )
            except Exception as error:
                print("Error inference:", error)
                break
    return frame
    
   
#----------------------------MOTION DETECTION-----------------------------------------#
def motion_detection(old_frame, new_frame):
        global motion_detected
        global md_start_time
        global md_count
        old_frame_gray = cv2.cvtColor(old_frame, cv2.COLOR_BGR2GRAY)
        new_frame_gray = cv2.cvtColor(new_frame, cv2.COLOR_BGR2GRAY)
        frame_diff = cv2.absdiff(old_frame_gray, new_frame_gray)        
        _, thresh = cv2.threshold(frame_diff, frameConfig['THRESHOLD_MD'], 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE) 
        for contour in contours:           
            if cv2.contourArea(contour) > 100: #threshold sensitivity set 100
                x, y, w, h = cv2.boundingRect(contour)
                cv2.rectangle(new_frame, (x, y), (x + w, y + h), (10, 10, 255), 2)
                motion_detected = True
                md_start_time = time.time()      
        if motion_detected:
            print("Motion Detected : ", md_count)

#----------------------------MONITOR CPU RAM USAGE-----------------------------------------#
def capture_cpu_usage():
    global video_run_flag
    print("start capture cpu usage")
    with open(dirConfig["CSV_CPU"], mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Time', 'CPU Usage (%)','RAM Usage (%)'])
        while video_run_flag:
            cpu_percent = psutil.cpu_percent(interval=1)  # Set capture cpu interval to 1 second
            ram_percent = psutil.virtual_memory().percent
            #print("CPU : ",cpu_percent)
            writer.writerow([time.time(), cpu_percent,ram_percent])
        print("CAPTURE CPU RAM STOP")

##############################################################################################################################   

def video_run():  
    global motion_detected
    global md_start_time
    global md_count 
    global video_run_flag
    
    ret, initial_frame = video.read()
    if not ret:
        print("Failed to read video")
        return
    md_count = 0
    motion_detected = False # Motion detection
    skip_frame_count = 0  # Initialize skip frame count
    
    video_run_flag = True
    capture_cpu_usage_thread = threading.Thread(target=capture_cpu_usage)
    capture_cpu_usage_thread.start()
    while True: 
        masterloop_start_time = time.time()
        loop_start_time = time.time()  # Record start time of the loop
        try:
            if motion_detected:
                md_count += 1
                
                if skip_frame_count > 0:  # Check if there are frames to skip
                    skip_frame_count -= 1  # Decrement skip frame count
                    ret, initial_frame = video.read()  # Read next frame to skip
                    if not ret:
                        raise Exception("Failed to read frame during skip.")
                    continue  # Skip the rest of the loop
                
                inference_start_time = time.time()  # Record start time of inference
                inferenced_frame = inference(initial_frame)
                show_images_opencv("INFERENCE", inferenced_frame)
                inference_end_time = time.time()  # Record end time of inference
                
                inference_duration = inference_end_time - inference_start_time  # Calculate duration of inference  
                       
                if (time.time() - md_start_time) > frameConfig["INFERENCE_DURATION"]:
                    motion_detected = False
                    print("Reset detection")  
                    ret, initial_frame = video.read()  
                     
                skip_frame_count = int(inference_duration * frameConfig["FRAMERATE_TARGET"]) - 1 # Calculate number of frames to skip based on inference duration
            else:   
                md_count += 1
                ret, next_frame = video.read()
                if not ret:
                    raise Exception("Failed to read next frame.")
                
                motion_detection(initial_frame, next_frame)
                ret, initial_frame = ret, next_frame
                
            loop_end_time = time.time()  # Record end time of the loop
            loop_duration = loop_end_time - loop_start_time  # Calculate duration of the loop
            time_to_sleep = max(0, (1 / frameConfig["FRAMERATE_TARGET"]) - loop_duration)  # Calculate time to sleep to maintain target frame rate
            time.sleep(time_to_sleep)  # Sleep to maintain target frame rate
            print("FPS per loop : ", (1/(time.time() - masterloop_start_time)))
            
        except Exception as error:
            print("Error:", error)
            break
    video_run_flag = False

def main():        
    video_run()
    
if __name__ == '__main__':
    start_time = time.time()  
    print("START PARKING DETECTION")
    main()
    end_time = time.time()
    print("START : ", start_time)
    print("END : ", end_time)
    print("TOTAL TIME : ",(end_time-start_time))
    

