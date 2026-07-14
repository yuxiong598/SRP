import cv2
import os
import numpy as np

class FaceRecognizer:
    def __init__(self, known_faces_dir='known_faces', model_file='face_model.yml', cascade_path=None):
        self.known_faces_dir = known_faces_dir
        self.model_file = model_file
        if cascade_path is None:
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        self.face_cascade = cv2.CascadeClassifier(cascade_path)
        self.recognizer = cv2.face.LBPHFaceRecognizer_create()
        self.labels = []
        self.label_to_id = {}
        self.load_or_train()

    def is_model_ready(self):
        """检查模型文件及标签映射文件是否存在"""
        return os.path.exists(self.model_file) and os.path.exists(self.model_file.replace('.yml', '_labels.txt'))

    def load_or_train(self):
        if self.is_model_ready():
            self.recognizer.read(self.model_file)
            map_file = self.model_file.replace('.yml', '_labels.txt')
            with open(map_file, 'r') as f:
                self.label_to_id = {int(k): v for line in f for k, v in [line.strip().split(',')]}
            self.labels = list(self.label_to_id.values())
            print(f"已加载模型，共 {len(self.labels)} 个人注册")
        else:
            self.train()

    def train(self):
        """遍历 known_faces_dir，支持子文件夹分组，训练并保存模型"""
        if not os.path.exists(self.known_faces_dir):
            os.makedirs(self.known_faces_dir)
            raise RuntimeError(f"文件夹 {self.known_faces_dir} 不存在且已自动创建，请先放入人脸照片后重新运行。")

        image_paths = []
        labels_int = []
        current_label = 0

        # 遍历 known_faces 下的所有子文件夹
        for person_id in os.listdir(self.known_faces_dir):
            person_dir = os.path.join(self.known_faces_dir, person_id)
            if not os.path.isdir(person_dir):
                continue  # 跳过不是文件夹的文件（如旧的单张图片）

            # 为该人员分配一个标签（如果已存在则用旧的）
            if person_id not in self.label_to_id.values():
                self.label_to_id[current_label] = person_id
                person_label = current_label
                current_label += 1
            else:
                # 找到已有的标签
                for label, pid in self.label_to_id.items():
                    if pid == person_id:
                        person_label = label
                        break

            # 遍历该人员文件夹下的所有图片
            for filename in os.listdir(person_dir):
                if not filename.lower().endswith(('.jpg', '.png', '.jpeg')):
                    continue
                filepath = os.path.join(person_dir, filename)
                img = cv2.imread(filepath)
                if img is None:
                    continue
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))
                if len(faces) == 0:
                    print(f"警告：{filepath} 中未检测到人脸，跳过")
                    continue
                (x, y, w, h) = faces[0]
                face_roi = gray[y:y + h, x:x + w]
                face_roi = cv2.resize(face_roi, (100, 100))
                image_paths.append(face_roi)
                labels_int.append(person_label)

        if len(image_paths) == 0:
            raise RuntimeError(
                f"在 {self.known_faces_dir} 中没有找到可训练的人脸图片（可能未检测到人脸）。请检查图片质量，或先注册一个人脸。")

        faces_np = np.array(image_paths, dtype=np.uint8)
        labels_np = np.array(labels_int, dtype=np.int32)
        self.recognizer.train(faces_np, labels_np)
        self.recognizer.write(self.model_file)

        map_file = self.model_file.replace('.yml', '_labels.txt')
        with open(map_file, 'w') as f:
            for label, pid in self.label_to_id.items():
                f.write(f"{label},{pid}\n")
        print(f"训练完成，共 {len(self.label_to_id)} 个人员，模型已保存至 {self.model_file}")

    def register_new_user(self, person_id=None):
        """注册新用户：输入用户名，创建同名子文件夹，拍摄人脸并保存到该文件夹，然后重新训练"""
        from chemical_backend.camera_module import capture_face_image  # 确保导入正确
        import time
        import shutil

        # 1. 获取用户ID
        if person_id is None:
            person_id = input("请输入操作员ID（例如姓名或工号）: ").strip()
            if not person_id:
                print("ID无效，取消注册")
                return False

        # 2. 创建该用户的子文件夹（如果已存在则复用）
        user_dir = os.path.join(self.known_faces_dir, person_id)
        os.makedirs(user_dir, exist_ok=True)
        print(f"用户文件夹：{user_dir}")

        # 3. 拍照（可改为循环多张，这里先拍一张）
        print(f"请将 {person_id} 的脸对准摄像头，按Enter拍摄...")
        face_img_path = capture_face_image()
        if face_img_path is None:
            print("人脸拍照失败")
            return False

        # 4. 保存照片到该用户的子文件夹中，文件名包含时间戳避免覆盖
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        dest_path = os.path.join(user_dir, f"{person_id}_{timestamp}.jpg")
        shutil.copy(face_img_path, dest_path)
        print(f"已保存人脸照片到 {dest_path}")

        # 5. 重新训练模型（train() 会自动遍历子文件夹）
        try:
            self.train()
            print("模型训练成功，新用户已注册。")
            return True
        except RuntimeError as e:
            print(f"训练失败：{e}")
            return False
    def recognize_face(self, face_image_path, tolerance=80):
        if not os.path.exists(face_image_path):
            print("人脸图片不存在")
            return "Unknown"
        img = cv2.imread(face_image_path)
        if img is None:
            print("无法读取图片")
            return "Unknown"
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))
        if len(faces) == 0:
            print("未检测到人脸")
            return "Unknown"
        (x, y, w, h) = faces[0]
        face_roi = gray[y:y+h, x:x+w]
        face_roi = cv2.resize(face_roi, (100, 100))

        label, confidence = self.recognizer.predict(face_roi)
        if confidence < tolerance:
            person_id = self.label_to_id.get(label, "Unknown")
            print(f"识别成功：{person_id} (置信度={confidence})")
            return person_id
        else:
            print(f"识别失败，最佳匹配距离={confidence} > {tolerance}")
            return "Unknown"