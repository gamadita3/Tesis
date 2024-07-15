import json
import traceback
import time
import argparse
import threading
from mqtt_setup_edge import MQTTSetup
from http_client import httpSetup
from camera_setup import CameraSetup
from motion_detection import MotionDetection
from object_detection import Inference
from system_monitor import SystemMonitor
from sampling import Sampling

###############################-EDGE-###############################################

def parse_args():
    parser = argparse.ArgumentParser(description='Run edge device with optional parameters')
    parser.add_argument('--inference', action='store_true', help='Enable inference code')
    parser.add_argument('--http', action='store_true', help='Using HTTP protocol')
    parser.add_argument('--monitor', action='store_true', help='Monitor CPU and RAM usage')
    parser.add_argument('--dataset', action='store_true', help='Run using dataset')
    parser.add_argument('--store', action='store_true', help='enable store frame')
    parser.add_argument('--FPS', action='store_true', help='enable FPS counter')
    return parser.parse_args()

def main():
    motion_detected = False 
    camera = CameraSetup(dataset_enabled)
    inference = Inference(store_enabled)
    motiondetection = MotionDetection()
    systemmonitor = SystemMonitor(monitor_enabled)
    sampling = Sampling()
    
    initial_frame = camera.get_frame()
    if monitor_enabled :   
        system_monitor_thread = threading.Thread(target=systemmonitor.start_monitoring)
        system_monitor_thread.start()
    
    print("\nEdge start parking detection !")
    
    while True: 
        loop_start_time = time.time()  # Record start time of the loop
        try:   
            sampling.save_sample(initial_frame, loop_start_time)                           
            if motion_detected:
                print("\nMotion Detected !")
                if inference_enabled:
                    print("\n---Inference---")
                    inference.detect(initial_frame)   
                    inferenced_frame = inference.frame    
                    print("\n---resize frame---")
                    inferenced_frame = camera.compress_resize(inferenced_frame)             
                    print("\n---Publishing---")
                    protocol.send_frame(inferenced_frame, inference.total_empty_detection, inference.total_occupied_detection)
                    #camera.show_images_opencv("EDGE_INFERENCE", inferenced_frame)
                else:
                    protocol.send_frame(frame=initial_frame)
                    #camera.show_images_opencv("EDGE_RAW", initial_frame)     
                motion_detected = False
                initial_frame = camera.get_frame()
                print("##################################################")              
            else:   
                next_frame = camera.get_frame()         
                motion_detected = motiondetection.detect_motion(initial_frame, next_frame)
                initial_frame = next_frame
                #camera.show_images_opencv("RAW",initial_frame)              
            loop_end_time = time.time()
            if fps_enabled :
                total_loop_time = loop_end_time - loop_start_time            
                FPS = float('inf') if total_loop_time == 0 else 1 / total_loop_time
                print("FPS per loop : ", FPS)                                   
        except Exception :
            print("Error:", print(traceback.format_exc()))
            break

if __name__ == '__main__':
    args = parse_args() 
    http_check = args.http
    if http_check :
        print("Protocol : HTTP")
        protocol = httpSetup()
    else : 
        print("Protocol : MQTT")    #Default MQTT  
        protocol = MQTTSetup()
        protocol.connect()
    inference_enabled = args.inference
    print(f"Inference : {inference_enabled}")
    monitor_enabled = args.monitor
    print(f"Monitoring : {monitor_enabled}")
    dataset_enabled = args.dataset
    print(f"Using Dataset : {dataset_enabled}")
    store_enabled = args.store
    print(f"Store : {store_enabled}")
    fps_enabled = args.FPS
    print(f"FPS : {fps_enabled}")
    main()
    

