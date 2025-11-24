from tensorflow import keras
import image_processing
import cv2
import numpy as np
import os
import re
import json
from PIL import Image
from config import MODEL_PATH, LABELS_PATH, DOBOT_MODES, IMAGE_DIR

inference_results = []
model = None
class_labels = None

def load_model_and_labels():
    global model, class_labels
    model = keras.models.load_model(MODEL_PATH, compile=False)
    try:
        with open(LABELS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            class_labels = [
                item["name"] 
                for item in data.get("classes", [])
                if item.get("name", "").strip().lower() != "default"
            ]

    except Exception as e:
        print(f"Could not load lable file: {e}")
        class_labels = None

    print("Model and labels loaded.")
    return model, class_labels
    
def preprocess_image(image_path, img_size=(180, 180)):
    isolated_object = image_processing.obj_classification(image_path)
    img = Image.open(isolated_object).convert("RGB")
    #img = img.resize(img_size)
    x = np.array(img, dtype=np.float32) / 255.0
    return np.expand_dims(x, axis=0)

def infer_image(image_name):
    global model
    img = preprocess_image(IMAGE_DIR + image_name)  
    preds = model.predict(img, verbose=0)[0]

    results = []
    for idx, prob in enumerate(preds):
        label = class_labels[idx] if class_labels else f"class_{idx}"
        results.append({"class": label, "probability": prob})

    results = sorted(results, key=lambda x: x["probability"], reverse=True)

    top_class = results[0]["class"]
    top_prob = round(results[0]["probability"], 2)

    inference_results.append({
        "image_name": image_name,
        "top_class": top_class,
        "top_probability": top_prob,
        "results": results
    })

    return top_class, top_prob
