import requests
import base64
import json

def send_measurement_data(api_url, weight, image_path, ocr_text, person_id, timestamp_str):
    """
    将测量数据通过POST请求发送到后端API
    图片会转换为base64编码后传输
    """
    try:
        # 读取图片并转为base64
        with open(image_path, 'rb') as f:
            image_base64 = base64.b64encode(f.read()).decode('utf-8')
        payload = {
            'weight_g': weight,
            'image_base64': image_base64,
            'ocr_text': ocr_text,
            'operator_id': person_id,
            'timestamp': timestamp_str
        }
        headers = {'Content-Type': 'application/json'}
        response = requests.post(api_url, data=json.dumps(payload), headers=headers, timeout=10)
        if response.status_code == 200:
            print("数据已成功发送到后端")
            return True
        else:
            print(f"后端返回错误: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"API通信失败: {e}")
        return False