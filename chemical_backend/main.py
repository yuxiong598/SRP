import os
import pandas as pd
from weight_module import read_weight_from_balance,auto_detect_serial_port
from chemical_backend.camera_module import capture_chemical_image, capture_face_image
from time_module import get_current_time
from chemical_backend.excel_module import save_to_excel
from ocr_module import extract_text_from_image
from chemical_backend.face_module import FaceRecognizer
from chemical_backend.api_module import send_measurement_data

def main():
    print("=" * 50)
    print("化学品智能管理系统")
    print("=" * 50)
    # ---------- 1. 串口配置 ----------
    print("\n【1】配置电子天平串口")
    ports = auto_detect_serial_port()
    if ports:
        while True:
            try:
                choice = input(f"输入端口名: ")
                if choice.isdigit():
                    idx = int(choice) - 1
                    if 0 <= idx < len(ports):
                        port = ports[idx].device
                        break
                else:
                    port = choice
                    break
            except:
                print("无效输入")
    else:
        port = input("请输入串口号 (如COM3): ")
    baudrate = input("波特率 (默认9600): ").strip()
    baudrate = int(baudrate) if baudrate else 9600

    # ---------- 2. 读取重量 ----------
    print("\n【2】读取天平数据...")
    weight = read_weight_from_balance(port=port, baudrate=baudrate)
    if weight is None:
        print("重量读取失败，是否继续？(y/n)")
        if input().lower() != 'y':
            return
    else:
        print(f"当前重量: {weight} g")
    # ---------- 3. 拍摄化学品图片 ----------
    print("\n【3】拍摄化学品图片")
    input("请将化学品置于摄像头前，按Enter拍摄...")
    chem_image_path = capture_chemical_image()
    if chem_image_path is None:
        print("化学品拍照失败，退出")
        return
    # ---------- 4. OCR识别化学品标签 ----------
    print("\n【4】对化学品图片进行文字识别")
    ocr_text = extract_text_from_image(chem_image_path)
    print(f"识别结果: {ocr_text if ocr_text else '无'}")

    # ---------- 5. 人脸识别操作人 ----------
    print("\n【5】操作员人脸识别")
    recognizer = FaceRecognizer()

    # 如果模型未就绪，则先注册一个用户
    if not recognizer.is_model_ready():
        print("未找到有效的人脸识别模型。")
        if input("是否注册当前操作员？(y/n) ").lower() == 'y':
            if not recognizer.register_new_user():
                print("注册失败，将跳过人脸识别。")
                person_id = "Unknown"
                # 注意：这里需要跳过后面的拍照和识别步骤，可以直接用变量控制
            else:
                # 注册成功后，继续识别流程（可选：直接让注册的人作为当前操作人）
                print("注册成功，请重新面向摄像头以便识别当前操作人。")
                input("按Enter继续识别...")
                face_image_path = capture_face_image()
                if face_image_path is None:
                    person_id = "Unknown"
                    print("人脸拍照失败，操作人标记为 Unknown")
                else:
                    person_id = recognizer.recognize_face(face_image_path)
                    print(f"识别结果: {person_id}")
        else:
            print("未注册任何人员，将跳过人脸识别。")
            person_id = "Unknown"
    else:
        # 模型已就绪，正常识别
        input("请将脸部对准摄像头，按Enter拍摄人脸...")
        face_image_path = capture_face_image()
        if face_image_path is None:
            person_id = "Unknown"
            print("人脸拍照失败，操作人标记为 Unknown")
        else:
            person_id = recognizer.recognize_face(face_image_path)
            print(f"识别结果: {person_id}")

    # ---------- 6. 保存到本地Excel ----------
    current_time = get_current_time()
    excel_file = input("Excel文件名 (默认 measurement_log.xlsx): ").strip()
    if not excel_file:
        excel_file = 'measurement_log.xlsx'

    if weight is not None:
        save_to_excel(weight, chem_image_path, current_time, ocr_text, person_id, excel_file)
    else:
        # 重量为空时的应急保存
        dummy_data = pd.DataFrame([{
            '称量时间': current_time.strftime('%Y-%m-%d %H:%M:%S'),
            '重量(g)': '读取失败',
            '图片路径': chem_image_path,
            '图片文件名': os.path.basename(chem_image_path),
            'OCR识别结果': ocr_text,
            '操作人ID': person_id,
            '记录时间戳': current_time.timestamp()
        }])
        if os.path.exists(excel_file):
            old = pd.read_excel(excel_file, engine='openpyxl')
            dummy_data = pd.concat([old, dummy_data], ignore_index=True)
        dummy_data.to_excel(excel_file, sheet_name='称量记录', index=False, engine='openpyxl')
        print(f"数据已保存（重量缺失）至 {excel_file}")

    # ---------- 7. 发送到后端API ----------
    print("\n【7】上报数据到云端")
    api_url = input("请输入后端API地址 (例如 http://localhost:5000/api/measure, 直接回车跳过): ").strip()
    if api_url:
        success = send_measurement_data(api_url, weight, chem_image_path, ocr_text, person_id,
                                        current_time.strftime('%Y-%m-%d %H:%M:%S'))
        if success:
            print("上报成功")
        else:
            print("上报失败，请检查网络或API地址")
    else:
        print("已跳过上报")

    print("\n" + "=" * 50)
    print("全部流程完成！")
    print(f"化学品图片: {chem_image_path}")
    print(f"操作人: {person_id}")
    print(f"OCR文字: {ocr_text}")
    print("=" * 50)


if __name__ == "__main__":
    main()