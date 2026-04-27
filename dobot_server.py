from dobot_handler import dobot_handler
from flask import Flask, request, jsonify, Response, send_from_directory
import time
import json
import threading
import os
import image_processing
import control
import glob
import re
import requests
from tensorflow import keras
import numpy as np
from PIL import Image
from config import DOBOT_PHOTO_POSITION, GRIPPER_ROTATION_OFFSET, MODEL_PATH, LABELS_PATH, DOBOT_MODES, IMAGE_DIR, GRIP_Z_POSITION, DETAIL_IMAGE_Z_POSITION, OVERVIEW_IMAGE_LENS_POSITION, DETAIL_IMAGE_LENS_POSITION
import inference_cnn

file_write_lock = threading.Lock()
app = Flask(__name__)

dobot = None
obj_pixel_coord = None
calib_values = None
get_position_flag = True
stop_process_flag = None

#model = None
#class_labels = None
#inference_results = []
dobot_modes = []

def load_dobot_modes():
    global dobot_modes
    try:
        with open(DOBOT_MODES, "r", encoding="utf-8") as f:
            dobot_modes = json.load(f)
    except Exception as e:
        print(f"Error loading Dobot modes: {e}")
        dobot_modes = []

# Function to write JSON data to a file
def write_to_file(data, filename):
    with file_write_lock:
        with open(filename, "w") as json_file:
            json.dump(data, json_file, indent=4)

# Set calibration values
def set_calibration_values():
    with open("files/calibration_file.json") as json_file:
        global calib_values
        calib_values = json.load(json_file)
    return jsonify({"message": "Calibration values set."})

def initialize_dobot(dobot_ip="192.168.1.6", speed=80):
    print("initialize_dobot")
    global dobot
    try:
        dobot = dobot_handler(dobot_ip)
        return True, "Connection established"
    except Exception as error:
        return False, "Connection failed"

# Initialize Dobot before the first request
def setup_dobot():
    print("setup_dobot")
    success, message = initialize_dobot()
    if success:
        dobot.start()
    else:
        return message
        
def delete_detail_images():
    for f in os.listdir(IMAGE_DIR):
        os.remove(os.path.join(IMAGE_DIR, f))

def setup_calibration():
     with open("files/calibration_file.json") as json_file:
        global calib_values
        calib_values = json.load(json_file)

@app.after_request
def add_header(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "*"
    return response

@app.route('/')
def index():
    return send_from_directory('html', 'index.html')

@app.route('/<path:path>')
def send_html(path):
    return send_from_directory('html', path)

""" # Stop the process
@app.route('/stop_process', methods=['GET'])
def stopProcess():
    global stop_process_flag
    stop_process_flag = True
    print(stop_process_flag, 'in the server')
    return jsonify({"message": "stop process."}) """
    
# get default Dobot position
@app.route("/photo_position", methods=["GET"])
def photoPosition():
    return jsonify(DOBOT_PHOTO_POSITION)

# Clear Dobot error
@app.route("/clear_error", methods=["GET"])
def clearError():
    dobot.dashboard.ClearError()
    time.sleep(2)
    return jsonify({"message": "Clear Error"})

# reset Dobot
@app.route("/reset_dobot", methods=["GET"])
def resetDobot():
    dobot.dashboard.ResetRobot()
    time.sleep(2)
    return jsonify({"message": "rest dobot"})


# Get Dobot error message
@app.route("/get_error_message", methods=["GET"])
def getError():
    return jsonify({"errorMessage": dobot.getErrorMessage()})

# Enable Dobot
@app.route("/enable", methods=["GET"])
def enableRobot():
    try:
        dobot.dashboard.ClearError ()
        dobot.dashboard.EnableRobot(0.325, 0.0, 0.0, 0.0)
        return jsonify({"message": "Dobot is enabled"})
    except Exception as e:
        return jsonify({"error": str(e)})

# Disable Dobot
@app.route("/disable", methods=["GET"])
def disableRobot():
    dobot.dashboard.DisableRobot()
    return jsonify({"message": "Dobot is disabled"})

# Get Dobot mode
@app.route("/get_dobot_mode", methods=["GET"])
def getDobotMode():
    raw_value = str(dobot.dashboard.RobotMode())
    match = re.search(r"\{(\d+)\}", raw_value)

    if not match:
        return jsonify({"error": "No mode value found", "raw_value": raw_value})

    mode_value = int(match.group(1))
    mode_info = next((item for item in dobot_modes if item["mode"] == mode_value), None)

    if not mode_info:
        return jsonify({"error": "Mode not found", "mode_value": mode_value})

    return jsonify({
        "mode_raw": raw_value,
        "mode_value": mode_value,
        "mode_info": mode_info
    })

@app.route("/open_gripper", methods=["GET"])
def open_gripper():
    dobot.setDO(8, 1)
    return jsonify({"message": "open gripper"})

@app.route("/close_gripper", methods=["GET"])
def close_gripper():
    dobot.setDO(8, 0)
    return jsonify({"message": "close Gripper"})

@app.route("/get_dobot_position", methods=["GET"])
def get_dobot_position():
    try:
        dobot_position = dobot.getPosition()
        return jsonify({"position": dobot_position})
    except Exception as e:
        return jsonify({"error": str(e)})
    
# Move to start photo position
@app.route("/move_to_start_foto_pos", methods=["POST"])
def move_to_start_foto_pos():
    requests.get("http://localhost:8000/set_lens_position/"+str(OVERVIEW_IMAGE_LENS_POSITION))
    dobot.dashboard.EnableRobot(0.325, 0.0, 0.0, 0.0)

    dobot_coords = request.get_json()
    if dobot_coords:
        dobot.moveToPoint([dobot_coords["x"], dobot_coords["y"], dobot_coords["z"], dobot_coords["r"]])
        time.sleep(2)
    else:
        x = float(calib_values['dobot_foto_pos']['x'])
        y = float(calib_values['dobot_foto_pos']['y'])
        z = float(calib_values['dobot_foto_pos']['z'])
        r = float(calib_values['dobot_foto_pos']['r'])
        dobot.moveToPoint([x, y, z, r])
        time.sleep(2)

    dobot.dashboard.DisableRobot()
    return jsonify({"message": "Moved to start photo position"})

# Save calibration file
@app.route("/save_calibration_file", methods=["POST"])
def save_calibration_file():
    data = request.get_json()
    threading.Thread(target=write_to_file, args=(data, "files/calibration_file.json")).start()
    response_data = {"message": "Received JSON object and started processing."}
    time.sleep(2)
    set_calibration_values()
    return jsonify(response_data), 200

# Save camera settings
@app.route("/save_camera_settings", methods=["POST"])
def save_camera_settings():
    data = request.get_json()
    threading.Thread(
        target=write_to_file, args=(data, "camera_settings_file.json")
    ).start()
    response_data = {"message": "Received JSON object and started processing."}
    return jsonify(response_data), 200

# Save Dobot settings
@app.route("/send_dobot_params", methods=["POST"])
def send_dobot_params():
    data = request.get_json()
    threading.Thread(target=write_to_file, args=(data, "dobot_settings.json")).start()
    response_data = {"message": "Received JSON object and started processing."}
    return jsonify(response_data), 200

# Get image by name
@app.route("/get_image/<path:image_path>", methods=["GET"])
def get_image(image_path):
    def generate():
        full_image_path = os.path.join("./images", image_path)
        with open(full_image_path, "rb") as img_file:
            chunk_size = 1024
            while True:
                chunk = img_file.read(chunk_size)
                if not chunk:
                    break
                yield chunk
    return Response(generate(), mimetype="image/jpeg")

# get all classified images
@app.route("/list_detail_images", methods=["GET"])
def list_detail_images():
    folder_path = './images/detail'
    files = os.listdir(folder_path)
    return jsonify(files)

# Find contours
@app.route("/find_contours", methods=["GET"])
def find_contours():
    set_calibration_values()
    response = requests.get("http://localhost:8000/get_aruco_marker")
    response.raise_for_status()
    marker_coord = response.json()
    print("marker_coord")
    print(marker_coord)
    global obj_pixel_coord
    trans_foto = image_processing.pres_crop_four_points(
        "./images/original_foto.jpg", marker_coord
    )
    
    obj_pixel_coord = image_processing.obj_recognition(trans_foto)
    return jsonify({"message": "Contours detection started."})

# Start the process
@app.route("/start_process", methods=["POST"])
def start_process():
    # Alte Bilder löschen
    delete_detail_images()

    # Dobot aktivieren
    dobot.dashboard.EnableRobot(0.500, 0.0, 0.0, 0.0)

    # Request-Daten
    data = request.get_json() or {}
    ai_detection = data.get("ai_detection", False)
    objects = data.get("objects", [])

    # Dobot-Status prüfen
    dobot_mode = dobot.dashboard.RobotMode()

    # --- AI Detection DEAKTIVIERT ---
    if not ai_detection:
        if not objects or len(objects) == 0:
            return jsonify({"error": "No drop position provided for default object."}), 400

        default_obj = objects[0]
        name = default_obj.get("name", "Unknown")
        drop_pos = default_obj.get("drop_position")

        if not drop_pos or len(drop_pos) != 3:
            return jsonify({"error": f"Invalid drop position for {name}."}), 400

        if dobot_mode == 9:
            return jsonify({"error": "Robot is currently in error mode and cannot move."}), 400

        # --- Bewegung starten ---
        print("obj_pixel_coord")
        print("obj_pixel_coord")
        print("obj_pixel_coord")
        print("obj_pixel_coord")
        print(obj_pixel_coord)
        print("---------------------------------------------")
        world_coord = control.prep_coords(list(obj_pixel_coord.values()), calib_values)
        foto_pos = calib_values["dobot_foto_pos"]

        # Übergibt jetzt auch objects
        control.move_to_object(world_coord, GRIP_Z_POSITION, -90.50, dobot, foto_pos, GRIPPER_ROTATION_OFFSET, objects)

        return jsonify({
            "status": "ok",
            "message": f"Moved to {name} (AI disabled)."
        })

    # --- AI Detection AKTIVIERT ---
    else:
        if not objects or len(objects) == 0:
            return jsonify({"error": "No objects selected for sorting."}), 400

        if dobot_mode == 9:
            return jsonify({"error": "Robot is currently in error mode and cannot move."}), 400

        invalids = [obj for obj in objects if "drop_position" not in obj or len(obj["drop_position"]) != 3]
        if invalids:
            names = ", ".join(o.get("name", "?") for o in invalids)
            return jsonify({"error": f"Invalid drop position(s) for: {names}"}), 400

        # --- AI-gestützten Prozess starten ---
        world_coord = control.prep_coords(list(obj_pixel_coord.values()), calib_values)
        foto_pos = calib_values["dobot_foto_pos"]

        # Übergibt ebenfalls die Objekte an capture_detail_picture
        control.capture_detail_picture(world_coord, GRIP_Z_POSITION, -90.50, dobot, foto_pos, DETAIL_IMAGE_Z_POSITION, OVERVIEW_IMAGE_LENS_POSITION, DETAIL_IMAGE_LENS_POSITION, GRIPPER_ROTATION_OFFSET, objects)
        return jsonify({
            "status": "ok",
            "message": "AI detection process started."
        })

@app.route("/get_inference_results", methods=["GET"])
def get_inference_results():
    inference_results_converted = convert_floats(inference_results)
    return jsonify(inference_results_converted)
    
def load_drop_positions():
    if not os.path.exists(LABELS_PATH):
        return {"classes": []}
    with open(LABELS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_drop_positions(data):
    with open(LABELS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

@app.route("/get_drop_positions", methods=["GET"])
def get_drop_positions():
    return jsonify(load_drop_positions())

@app.route("/set_drop_positions", methods=["POST"])
def set_drop_positions():
    new_data = request.get_json()
    if not new_data or "classes" not in new_data:
        return jsonify({"error": "Invalid JSON format"}), 400
    save_drop_positions(new_data)
    return jsonify({"message": "Drop positions updated"}), 200

def convert_floats(data):
    if isinstance(data, dict):
        # Convert the dictionary keys and values
        return {key: convert_floats(value) for key, value in data.items()}
    elif isinstance(data, list):
        # Convert each item in the list
        return [convert_floats(item) for item in data]
    elif isinstance(data, np.float32):
        # Convert np.float32 to Python float
        return float(data)
    else:
        return data

if __name__ == "__main__":
    load_dobot_modes()
    inference_cnn.model, inference_cnn.class_labels = inference_cnn.load_model_and_labels()
    setup_dobot()
    setup_calibration()
    delete_detail_images()
    app.run(host='0.0.0.0', port=5000, debug=True)