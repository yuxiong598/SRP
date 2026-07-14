import cv2
import time
import os
from datetime import datetime

def capture_chemical_image(camera_id=0, save_dir='chemical_images'):
    """
    通过摄像头拍摄化学品图片
    使用OpenCV调用摄像头并保存图片
    """
    try:
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        cap = cv2.VideoCapture(camera_id)

        if not cap.isOpened():
            print("无法打开摄像头")
            return None

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        time.sleep(0.5)

        ret, frame = cap.read()
        cap.release()

        if not ret:
            print("无法读取摄像头图像")
            return None

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        image_filename = f"chemical_{timestamp}.jpg"
        image_path = os.path.join(save_dir, image_filename)

        cv2.imwrite(image_path, frame)
        print(f"图片已保存: {image_path}")

        return image_path

    except Exception as e:
        print(f"摄像头拍照时发生错误: {e}")
        return None
def capture_face_image(camera_id=0, save_dir='face_images'):
    """单独拍摄人脸照片，用于人脸识别"""
    try:
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        cap = cv2.VideoCapture(camera_id)
        if not cap.isOpened():
            print("无法打开摄像头")
            return None
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        time.sleep(0.5)
        ret, frame = cap.read()
        cap.release()
        if not ret:
            print("无法读取人脸图像")
            return None
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"face_{timestamp}.jpg"
        path = os.path.join(save_dir, filename)
        cv2.imwrite(path, frame)
        print(f"人脸图片已保存: {path}")
        return path
    except Exception as e:
        print(f"拍照错误: {e}")
        return None