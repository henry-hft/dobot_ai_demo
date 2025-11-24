import cv2 as cv2
import matplotlib.pyplot as plt
import numpy as np
import os
import draw
from PIL import Image
import math
import imutils
import random
import os
from pathlib import Path

def pres_crop_four_points(image_or_path, marker_coord):
    marker_coord_array = []
    img =cv2.imread (image_or_path)
    
    for marker in marker_coord:
        inner_array = [marker["x"], marker["y"]]
        marker_coord_array.append(inner_array)
    
    print(marker_coord_array)
    rectangle = np.array(marker_coord_array, dtype=np.float32)
    (tl, tr, br, bl) = rectangle

    # Calculate the width and height of the new image
    widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
    widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
    max_width = max(int(widthA), int(widthB))

    heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
    heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
    max_height = max(int(heightA), int(heightB))

    dst = np.array([
        [0, 0],
        [max_width - 1, 0],
        [max_width - 1, max_height - 1],
        [0, max_height - 1]], dtype="float32")

    M = cv2.getPerspectiveTransform(rectangle, dst)
    transformed = cv2.warpPerspective(img, M, (max_width, max_height))

    #transformed_image_path = "./images/"+ 'transformed_image.jpg' 
    #cv2.imwrite(transformed_image_path, transformed)
    return transformed

def undistort_image(image_or_path, output_path):
    if isinstance(image_or_path, str):
        img = Image.open(image_or_path)
    elif isinstance(image_or_path, Image.Image):
        img = image_or_path
    else:
        raise ValueError("Invalid input type. Expected image path or PIL Image object.")

    img_array = np.array(img)
    
    camera_matrix = np.array([[4.74169317e+03, 0.00000000e+00, 9.65718408e+02],
                              [0.00000000e+00, 1.47888291e+03, 5.50285164e+02],
                              [0.00000000e+00, 0.00000000e+00, 1.00000000e+00]], dtype=np.float64)

    distortion_coeffs = np.array([0.0, 0.0, 0, 0, 0])

    h, w = img_array.shape[:2]
    new_camera_matrix, _ = cv2.getOptimalNewCameraMatrix(camera_matrix, distortion_coeffs, (w, h), 1, (w, h))
    undistorted_image = cv2.undistort(img_array, camera_matrix, distortion_coeffs, None, new_camera_matrix)
				
    return undistorted_image


def Grayscale(ImageSrc, Classify=False):
  gray_im = cv2.cvtColor(ImageSrc, cv2.COLOR_RGB2GRAY)
  
  if not Classify:
      cv2.imwrite("./images/" + 'gray_im.jpg' , gray_im)
			
  return(gray_im)

def GammaCorrection(ImageSrc, Classify=False, Y=0.4):
    gammaCorrection = np.array(255 * (ImageSrc / 255) ** Y, dtype='uint8')
    
    if not Classify:
        filename = "./images/gammaCorrection.jpg"
        cv2.imwrite(filename, gammaCorrection)
				
    return gammaCorrection

def Threshold(ImageSrc, Classify=False, MaxValue = 255, BlockSize = 255, C = 19):
  thresh = cv2.adaptiveThreshold(ImageSrc, MaxValue, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, BlockSize, C)
  thresh = cv2.bitwise_not(thresh)
  
  if not Classify:
      cv2.imwrite("./images/" + 'thresh.jpg' , thresh)
			
  return(thresh)

def MorphOperation(ImageSrc, Classify=False, Size = 15, BlurSize = 7):
  kernel = np.ones((Size, Size), np.uint8)
  img_dilation = cv2.dilate(ImageSrc, kernel, iterations=1)
  img_erode = cv2.erode(img_dilation, kernel, iterations=1)

  # clean all noise after dilatation and erosion
  img_erode = cv2.medianBlur(img_erode, BlurSize)
  if not Classify:
    cv2.imwrite("./images/" + 'morphOperation.jpg' , img_erode)
    
  return(img_erode)
  

def AutoCanny(ImageSrc, Classify=False, sigma=0.33):
	# compute the median of the single channel pixel intensities
	v = np.median(ImageSrc)
	# apply automatic Canny edge detection using the computed median
	lower = int(max(10, (1.0 - sigma) * v))
	#print("lower: " + str(lower))
	upper = int(min(255, (1.0 + sigma) * v))
        
	edged = cv2.Canny(ImageSrc, lower, upper)
	if not Classify:
		cv2.imwrite("./images/" + 'autoCanny.jpg' , edged)
		
	return(edged)
    
def FindDetailContours(ImageSrc, OrgImageSrc, MinSize=10000):
    img = OrgImageSrc.copy()
    contours, _ = cv2.findContours(ImageSrc, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    center_points = []
    boxes = []

    if len(contours) == 0:
        print(f"[INFO] No contours found")
        return img

    for i, c in enumerate(contours):
        area = cv2.contourArea(c)
        rect = cv2.minAreaRect(c)
        box = cv2.boxPoints(rect)
        box = np.intp(box)

        center = (int(rect[0][0]), int(rect[0][1]))
        width = int(rect[1][0])
        height = int(rect[1][1])
        angle = int(rect[2])

        if width * height > MinSize:
            cv2.drawContours(img, [c], 0, (0, 255, 0), 5)
            cv2.drawContours(img, [box], 0, (0, 0, 255), 2)
            cv2.circle(img, center, radius=0, color=(0, 0, 255), thickness=20)
            center_points.append(center)
            boxes.append(box)
            print(width * height)

    h, w, _ = img.shape

    if len(center_points) > 0:
        centerObj = FindCenterObject(center_points, (w / 2, h / 2), boxes)
        screw = ExtractScrew(OrgImageSrc, centerObj)
        result = IsolateObject(screw)
    else:
        print(f"[INFO] No screw found")
        result = img  # or: result = None

    return result

def ExtractScrew(OrgImageSrc, arr, padding = 10):
  img = OrgImageSrc.copy()
  for i in range(4):
    arr[i][0] -= padding
    arr[i][1] += padding

  bounding_boxes = []
  print("shape of arr: {}".format(arr.shape))
  rect = cv2.minAreaRect(arr)
  print("rect: {}".format(rect))
  box = cv2.boxPoints(rect)
  box = np.intp(box)
  print("bounding box: {}".format(box))

  width = int(rect[1][0])
  height = int(rect[1][1])

  src_pts = box.astype("float32")

  dst_pts = np.array([[0, height-1],
                      [0, 0],
                      [width-1, 0],
                      [width-1, height-1]], dtype="float32")

  M = cv2.getPerspectiveTransform(src_pts, dst_pts)
  warped = cv2.warpPerspective(img, M, (width, height))
  return warped

def IsolateObject(img, image_size=180):
    h, w = img.shape[:2]

    if h > image_size:
        img = imutils.resize(img, height=image_size)

    h, w = img.shape[:2]

    top = int(math.ceil((image_size - h) / 2))
    bottom = int(math.floor((image_size - h) / 2))
    color = [255, 255, 255] # background color
    return cv2.copyMakeBorder(img, top, bottom, 0, 0, cv2.BORDER_CONSTANT, value=color)

def FindContours(image_src, org_image_src, min_ratio=0.001):
    img = org_image_src.copy()
    contours, _ = cv2.findContours(image_src, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)

    center_coordinates_map = {}
    line_midpoints_map = {}

    center_points = []
    boxes = []

    for i, c in enumerate(contours):
        rect = cv2.minAreaRect(c)
        box = cv2.boxPoints(rect)
        box = np.int0(box)

        center = (int(rect[0][0] + 1), int(rect[0][1] + 1))
        width = int(rect[1][0])
        height = int(rect[1][1])
        angle = int(rect[2])

        if width < height:
            angle = 90 - angle
        else:
            angle = -angle

        ratio = calculate_rect_img_ratio((width * height), img)
        if ratio > min_ratio:
            draw.draw_contours_and_boxes(img, c, box)
            draw.draw_object_coords(center, img)
            cv2.circle(img, center, 3, (0, 0, 255), -1)
            draw.draw_angle_text(img, angle, center)

            center_coordinates_map[i + 1] = (center, angle, 0)
            center_points.append(center)
            boxes.append(box)

            # 1) lange Seite finden
            edges = []
            for j in range(4):
                p1 = box[j]
                p2 = box[(j + 1) % 4]
                length = np.linalg.norm(p1 - p2)
                edges.append((length, p1, p2, j))

            edges.sort(key=lambda x: x[0], reverse=True)
            _, long_p1, long_p2, idx_long = edges[0]

            # 2) Mittelpunkt der langen Seite
            mid_long = (
                int((long_p1[0] + long_p2[0]) / 2),
                int((long_p1[1] + long_p2[1]) / 2),
            )
            cv2.circle(img, mid_long, 4, (255, 0, 0), -1)  # blau

            # 3) Richtung der kurzen Seite bestimmen
            short_p1 = box[(idx_long + 1) % 4]
            short_p2 = box[(idx_long + 2) % 4]

            v_short = short_p2.astype(np.float32) - short_p1.astype(np.float32)
            norm = np.linalg.norm(v_short)
            if norm == 0:
                continue
            v_short /= norm  # Einheitsvektor in Richtung der kurzen Seite

            # 4) Linie durch mid_long parallel zur kurzen Seite
            h, w = img.shape[:2]
            line_len = max(h, w)

            pt1 = (
                int(mid_long[0] - v_short[0] * line_len),
                int(mid_long[1] - v_short[1] * line_len),
            )
            pt2 = (
                int(mid_long[0] + v_short[0] * line_len),
                int(mid_long[1] + v_short[1] * line_len),
            )

            cv2.line(img, pt1, pt2, (0, 255, 255), 1)  # gelbe Linie

            # 5) Schnittpunkte der Linie mit der Kontur
            mask_line = np.zeros(img.shape[:2], dtype=np.uint8)
            mask_contour = np.zeros_like(mask_line)

            cv2.line(mask_line, pt1, pt2, 255, 2)
            cv2.drawContours(mask_contour, [c], -1, 255, 2)

            intersections = cv2.bitwise_and(mask_line, mask_contour)
            ys, xs = np.where(intersections > 0)

            if len(xs) >= 2:
                pts = np.stack([xs, ys], axis=1).astype(np.float32)

                # Projektion auf Kurzseiten-Richtung
                proj = pts.dot(v_short)

                idx_min = np.argmin(proj)
                idx_max = np.argmax(proj)

                p_a = pts[idx_min]
                p_b = pts[idx_max]

                # neuer Mittelpunkt zwischen den beiden Schnittpunkten
                mid_new = (
                    int((p_a[0] + p_b[0]) / 2),
                    int((p_a[1] + p_b[1]) / 2),
                )

                # Visualisierung
                cv2.circle(img, (int(p_a[0]), int(p_a[1])), 4, (0, 255, 0), -1)  # grün
                cv2.circle(img, (int(p_b[0]), int(p_b[1])), 4, (0, 255, 0), -1)  # grün
                cv2.circle(img, mid_new, 5, (255, 0, 255), -1)  # magenta

                line_midpoints_map[i + 1] = {
                    "rect_center": center,
                    "mid_long_side": mid_long,
                    "contour_line_mid": mid_new,
                }

    return img, center_coordinates_map, line_midpoints_map

def calculate_rect_img_ratio(area, img):
    image_area = img.shape[0] * img.shape[1]
    return area / image_area

def EuclideanDistance(point1, point2):
    x1, y1 = point1
    x2, y2 = point2
    return math.sqrt((x1 - x2)**2 + (y1 - y2)**2)

def FindCenterObject(coordinates, image_center, boxes):
    min_distance = float('inf')
    closest_pair = None
    closest_box = None
    for index, coordinate in enumerate(coordinates):
        distance = EuclideanDistance(coordinate, image_center)
        if distance < min_distance:
            min_distance = distance
            closest_pair = coordinate
            closest_box = boxes[index]
    #print("Euklidische Distanz: " + str(closest_pair[0]) + ", " + str(closest_pair[1]))
    return closest_box

def ExtractObject(OrgImageSrc, arr, padding=20):
    img = OrgImageSrc.copy()

    rect = cv2.minAreaRect(arr)
    box = cv2.boxPoints(rect)
    box = np.int0(box)

    width = int(rect[1][0])
    height = int(rect[1][1])

    src_pts = box.astype("float32")

    # Adding padding to the destination points
    dst_pts = np.array([[padding, height - 1 - padding],
                        [padding, padding],
                        [width - 1 - padding, padding],
                        [width - 1 - padding, height - 1 - padding]], dtype="float32")

    M = cv2.getPerspectiveTransform(src_pts, dst_pts)

    # Calculate the new width and height considering the padding
    new_width = width + 2 * padding
    new_height = height + 2 * padding

    warped = cv2.warpPerspective(img, M, (new_width, new_height))

    return warped

def IsolateObject(img, image_size = 180):
  h, w = img.shape[:2]
  print(h)
  print(w)

  if w > image_size:
    img = imutils.resize(img, width=image_size)

  h, w = img.shape[:2]
  print(h)
  print(w)

  if h > image_size:
    img = imutils.resize(img, height=image_size)

  h, w = img.shape[:2]
  print(h)
  print(w)
  left = int(math.ceil((image_size - w) / 2))
  right = int(math.floor((image_size - w) / 2))
  top = int(math.ceil((image_size - h) / 2))
  bottom = int(math.floor((image_size - h) / 2))
  color = [255, 255, 255] # white
  return cv2.copyMakeBorder(img, top, bottom, left, right, cv2.BORDER_CONSTANT, value=color)

def obj_recognition(image_or_path):
    if isinstance(image_or_path, str):
        img = cv2.imread(image_or_path)
        if img is None:
              raise ValueError("The image could not be read.")
    elif isinstance(image_or_path, np.ndarray):
        img = image_or_path
    else:
        raise ValueError("Invalid type for the 'image_or_path' parameter.")

    gray = Grayscale(img)
    gamma = GammaCorrection(gray)
    thresh = Threshold(gamma)
    morph = MorphOperation(thresh)
    canny = AutoCanny(morph)
    contours, center_coordinates_map, line_midpoints_map = FindContours(canny, img)
    cv2.imwrite("./images/contours.jpg", contours)
    return center_coordinates_map
    
def resize_with_padding(img, target_size=(180,180), pad_value=0):
    h, w = img.shape[:2]
    if h > w:
        img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
        h, w = img.shape[:2]

    target_h, target_w = target_size
    scale = min(target_w / w, target_h / h)
    new_w, new_h = int(w * scale), int(h * scale)
    resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)

    delta_w = target_w - new_w
    delta_h = target_h - new_h
    top, bottom = delta_h // 2, delta_h - delta_h // 2
    left, right = delta_w // 2, delta_w - delta_w // 2

    padded = cv2.copyMakeBorder(
        resized, top, bottom, left, right,
        cv2.BORDER_CONSTANT, value=[pad_value]*3
    )

    return padded

def obj_classification(path):
    print(path)
    if isinstance(path, str):
        img = cv2.imread(path)
        if img is None:
              raise ValueError("The image could not be read.")
    else:
        raise ValueError("Invalid type for the 'path' parameter.")

    gray = Grayscale(img, True)
    gamma = GammaCorrection(gray, True, 1.2)
    thresh = Threshold(gamma, True, 255, 255, 14)
    morph = MorphOperation(thresh, True)
    canny = AutoCanny(morph, True)
    contours = FindDetailContours(canny, img)
    padding = resize_with_padding(contours)
    #p = Path(path)
    #filename = p.with_name(p.stem + "_preprocessed" + p.suffix)
    new_path = path.replace("unclassified", "preprocessed")
    cv2.imwrite(new_path, padding)
    return new_path
