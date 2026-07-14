import serial
import serial.tools.list_ports
import time
import re

def read_weight_from_balance(port='COM3', baudrate=9600, timeout=2):
    try:
        # 使用 with 上下文，退出时自动关闭串口
        with serial.Serial(port=port,
                           baudrate=baudrate,
                           bytesize=serial.EIGHTBITS,
                           stopbits=serial.STOPBITS_ONE,
                           parity=serial.PARITY_NONE,
                           timeout=timeout) as ser:
            time.sleep(0.5)  # 等待串口就绪

            # 清空缓冲区
            ser.reset_input_buffer()
            ser.reset_output_buffer()

            # 发送指令 R（注意 CR/LF 根据天平要求调整）
            ser.write(b'R\r\n')
            ser.flush()  # 等待发送完成

            # 读取响应
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            print("RAW:", repr(line))
            if not line:
                print("未收到数据")
                return None

            return parse_weight_data(line)

    except Exception as e:
        print(f"串口错误: {e}")
        return None


def parse_weight_data(data_string):
    """
    解析天平返回的数据，提取重量值
    """
    weight_pattern = r'([-+]?\d+\.?\d*)'
    match = re.search(weight_pattern, data_string)

    if match:
        weight_value = float(match.group(1))
        return weight_value

    cleaned = re.sub(r'[a-zA-Z]', '', data_string)
    cleaned = cleaned.strip()

    if cleaned:
        try:
            weight_value = float(cleaned)
            return weight_value
        except ValueError:
            pass

    print(f"无法解析的重量数据: {data_string}")
    return None

def auto_detect_serial_port():
    """自动检测并返回可用的串口号列表"""
    ports = list(serial.tools.list_ports.comports())
    port_names = [port.device for port in ports]
    if port_names:
        print("可用的串口设备:")
        for i, name in enumerate(port_names, 1):
            print(f"  {i}. {name}")
        return port_names
    else:
        return []