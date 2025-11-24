from camera.Configs import Configs
import cv2
import numpy as np

def sort_corners(corners):
    sorted_corners = sorted(corners, key=lambda corner: corner[0][0][1])

    array1 = sorted_corners[0]
    array2 = sorted_corners[1]
    array3 = sorted_corners[2]
    array4 = sorted_corners[3]

    if array1[0][0][0] > array2[0][0][0]:
        array1, array2 = array2, array1

    if array3[0][0][0] < array4[0][0][0]:
        array3, array4 = array4, array3

    return [array1, array2, array3, array4]

def process_frame(frame):
    aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_250)
    aruco_params =  cv2.aruco.DetectorParameters()
    aruco_detector = cv2.aruco.ArucoDetector(aruco_dict, aruco_params)
    
   # frame = undistort_image (frame )
    grey = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    corners, ids, _ = aruco_detector.detectMarkers(grey)
    
    ref_points = []
    if ids is not None and 2 <= len(ids) <= 4:
        if len(ids) == 4:
            corners = sort_corners(corners)
        
        for corner in corners:
            pt = (int(corner[0][0][0]), int(corner[0][0][1]))
            cv2.putText(frame, f'({pt[0]}, {pt[1]})', pt, cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 1)
            corner_coord = {
                "x": pt[0],
                "y": pt[1]
            }
            ref_points.append(corner_coord)
        
        for i in range(len(ids) - 1):
            pt1 = (int(corners[i][0][0][0]), int(corners[i][0][0][1]))
            pt2 = (int(corners[i + 1][0][0][0]), int(corners[i + 1][0][0][1]))
            frame = cv2.line(frame, pt1, pt2, (0, 255, 0), 2)
        
        pt1 = (int(corners[0][0][0][0]), int(corners[0][0][0][1]))
        pt2 = (int(corners[-1][0][0][0]), int(corners[-1][0][0][1]))
        frame = cv2.line(frame, pt1, pt2, (0, 255, 0), 2)

    return frame, ref_points

class Analysis(Configs):
    

    def __init__(self):
        pass
    
    def main_analysis(self, image):
        image, ref_points = process_frame(image)
        return image, ref_points
