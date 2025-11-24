import cv2
import matplotlib.pyplot as plt
import math

def draw_object_coords(center, img):
    x, y = center
    text = f"({x}, {y})"
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.5
    text_color = (255, 0, 0)
    text_thickness = 2
    text_size, _ = cv2.getTextSize(text, font, font_scale, text_thickness)
    text_origin = (x + 10, y - 10 - text_size[1])
    cv2.putText(img, text, text_origin, font, font_scale, text_color, text_thickness)

def draw_coords_system(image):
    height, width, _ = image.shape

    cv2.line(image, (0, 0), (width, 0), (255, 255, 0), 1)
    cv2.line(image, (0, 0), (0, height), (255, 255, 0), 1)

    x_origin = 0
    y_origin = 0
    x_text_offset = 15
    y_text_offset = 15
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 1.5
    text_color = (255, 87, 51)
    text_thickness = 1

    for x in range(0, width, 50):
        cv2.line(image, (x_origin + x, y_origin - 5), (x_origin + x, y_origin + 5), (0, 0, 255), 1)
        cv2.putText(image, str(x), (x_origin + x + x_text_offset +100, y_origin + y_text_offset),
                    font, font_scale, text_color, text_thickness)

    for y in range(0, height, 50):
        cv2.line(image, (x_origin - 5, y_origin + y), (x_origin + 5, y_origin + y), (0, 0, 255), 1)
        cv2.putText(image, str(y), (x_origin + x_text_offset, y_origin + y + y_text_offset),
                    font, font_scale, text_color, text_thickness)

    return image


def draw_contours_and_boxes(img, contour, box):
    cv2.drawContours(img, [contour], 0, (0, 255, 0), 2)
    cv2.drawContours(img, [box], 0, (0, 0, 255), 3)

def draw_angle_text(img, angle, center):
    angle_text = f"{angle:.2f} Grad"
    cv2.putText(img, angle_text, (center[0] + 45, center[1] - 45), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)

def draw_color_text(img, color, box):
    color_text = str(color)
    cv2.putText(img, color_text, (box[0][0], box[0][1]), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 1)


def calculate_rect_img_ratio(rect, image):
    image_area = image.shape[0] * image.shape[1]
    ratio = (rect / image_area) * 100
    return ratio

def calculate_distance(object1, object2):
    x1, y1 = object1
    x2, y2 = object2
    distance = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
    return distance

def sorted_obj_ref(center_coordinates_map, reference_point):
    sorted_objects_ref = []
    center_coordinates_map_copy = center_coordinates_map.copy()
    for _ in range(len(center_coordinates_map)):
        objects = sorted(center_coordinates_map_copy.keys(), key=lambda x: calculate_distance(center_coordinates_map_copy[x], reference_point))
        next_object = objects[0]
        reference_point = center_coordinates_map_copy[next_object]
        sorted_objects_ref.append(next_object)
        del center_coordinates_map_copy[next_object]
    return sorted_objects_ref
