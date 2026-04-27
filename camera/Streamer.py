from camera.Configs import Configs
from camera.Analysis import Analysis
import threading
import cv2
from flask import Flask, request, jsonify, Response, send_file
import subprocess
import os
from picamera2 import Picamera2
import time
from libcamera import controls
import uuid

ref_points = None
save_current_frame = False
save_current_frame_detail = False
frame_detail_index = 0
current_lens_position = 0
new_lens_position = 2.0

storage_path = "/home/pi/dobot_screw_demo/images/"
storage_path_detail = "/home/pi/dobot_screw_demo/images/detail/"
image_name = 'original_foto.jpg'

if not os.path.exists(storage_path):
    os.makedirs(storage_path)

class Streamer(Configs):

    def __init__(self):
        self.camera = Picamera2()
        resolution = (1920, 1080)
        camera_config = self.camera.create_still_configuration(main={"format": 'XRGB8888', "size": resolution})
        self.camera.configure(camera_config)
        self.camera.start()
        self.camera.set_controls({"AfMode": controls.AfModeEnum.Manual, "LensPosition": 2.0})
        self.analysis= Analysis()

        app = Flask(__name__)
    
    def capture_frames_neu(self):
        while True:
            global ref_points
            global current_lens_position
            global save_current_frame
            global save_current_frame_detail
            global new_lens_position

            frames = self.camera.capture_array()

            if current_lens_position != new_lens_position:
                self.camera.set_controls({"AfMode": controls.AfModeEnum.Manual, "LensPosition": new_lens_position})
                current_lens_position = new_lens_position

        # Speichern in Originalauflösung
            if save_current_frame:
                save_current_frame = False
                #cv2.imwrite(os.path.join(storage_path, f"{uuid.uuid4().hex}.jpg"), frames)
                cv2.imwrite(os.path.join(storage_path, image_name), frames)
            elif save_current_frame_detail:
                global frame_detail_index
                frame_detail_index += 1
                cv2.imwrite(os.path.join(storage_path_detail, str(frame_detail_index) + "_unclassified.jpg"), frames)
                save_current_frame_detail = False
            else:
                # Nur für Streamen: Verkleinern
                small_frame = cv2.resize(frames, (960, 540))  # Beispiel: FullHD → 640x360

            # Analyse auf verkleinertem Bild (kannst du ggf. auf Original machen, je nach Bedarf)
                image, ref_points = self.analysis.main_analysis(small_frame)

                with threading.Lock():
                    return_key, encoded_image = cv2.imencode(self.videoEncoding, image)
                    yield (b"--frame\r\n"
                           b"Content-Type: image/jpg\r\n\r\n" + bytearray(encoded_image) + b"\r\n")

    def capture_frames(self):
        while True:
            global ref_points
            global current_lens_position
            global save_current_frame
            global save_current_frame_detail
            global new_lens_position

            frames = self.camera.capture_array()
            
            if current_lens_position != new_lens_position:
                self.camera.set_controls({"AfMode": controls.AfModeEnum.Manual, "LensPosition": new_lens_position})
                current_lens_position = new_lens_position
                
            if save_current_frame:
                save_current_frame = False
                #cv2.imwrite(os.path.join(storage_path, f"{uuid.uuid4().hex}.jpg"), frames)
                cv2.imwrite(os.path.join(storage_path, image_name), frames)
            elif save_current_frame_detail:
                global frame_detail_index
                frame_detail_index += 1
                cv2.imwrite(os.path.join(storage_path_detail, str(frame_detail_index) + "_unclassified.jpg"), frames)
                
                save_current_frame_detail = False

            else:
                image, ref_points = self.analysis.main_analysis(frames)
                with threading.Lock():
                    return_key, encoded_image = cv2.imencode(self.videoEncoding, image)
                    yield(b"--frame\r\n' b'Content-Type: image/jpg\r\n\r\n" + bytearray(encoded_image) + b"\r\n")

    def runStream(self):

        app = Flask(__name__)

        @app.after_request
        def add_header(response): 
            response.headers["Access-Control-Allow-Origin"] = '*'
            response.headers["Access-Control-Allow-Headers"] = '*'
            response.headers["Access-Control-Allow-Methods"] = '*'
            return response

        @app.route('/save_current_frame', methods=['GET'])
        def write_image():
            global save_current_frame 
            save_current_frame = True 
            return jsonify({"message": "write image."})

        @app.route('/save_current_frame_detail', methods=['GET'])
        def write_detail_image():
            global save_current_frame_detail
            save_current_frame_detail = True 
            global frame_detail_index
            
            return jsonify({"message": "write image.", "filename": str(frame_detail_index+1) + "_unclassified.jpg"})
            
        @app.route('/set_lens_position/<float:lens_pos>', methods=['GET'])
        def set_lens_position(lens_pos):
            global new_lens_position
            new_lens_position = lens_pos
            return jsonify({"message": f"lens position set to {lens_pos}"})

        @app.route('/get_aruco_marker', methods=['GET'])
        def get_ref_points():
            global ref_points
            return jsonify(ref_points)
            
            
        @app.route('/viewer', methods=['GET'])
        def viewer():
            return """
            <html>
            <body style="margin: 0; background: black; display: flex; justify-content: center; align-items: center;">
                <img src="/" style="width:100%; height:100%; object-fit:contain;">
            </body>
            </html>
            """

        @app.route("/")
        def streamFrames():
            return Response(self.capture_frames(), mimetype="multipart/x-mixed-replace; boundary=frame")

        process_thread = threading.Thread(target=self.capture_frames)
        process_thread.daemon = True
        process_thread.start()
        app.run(self.RaspberryIP, port=self.port, threaded=True)
