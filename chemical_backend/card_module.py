import time
import serial
import serial.tools.list_ports
import database_moudle as db  # 数据库模块，提供 verify_card 和 register_card 方法


def normalize_card_no(value):
    """
    规范化卡号：去除空白字符、转为大写、拼接为连续字符串

    Args:
        value: 原始卡号（可能为 None，数字或字符串）

    Returns:
        str: 规范化后的卡号字符串，若输入为 None 则返回空字符串
    """
    if value is None:
        return ""
    # 去除首尾空白、移除中间空白（如空格、换行等）、转为大写
    return "".join(str(value).strip().split()).upper()


def list_reader_ports():
    """
    列出当前系统所有可用的串口设备

    Returns:
        list of dict: 每个元素包含 {"device": 端口名, "description": 描述信息}
    """
    return [
        {"device": port.device, "description": port.description}
        for port in serial.tools.list_ports.comports()
    ]


def read_card_from_serial(port="COM3", baudrate=9600, timeout=5, command=None):
    """
    通过串口读取一次卡片数据

    Args:
        port (str): 串口号，如 "COM3" 或 "/dev/ttyUSB0"
        baudrate (int): 波特率，默认 9600
        timeout (int/float): 串口读取超时时间（秒）
        command (str, optional): 发送给读卡器的命令（如 "READ"），若为 None 则直接读取

    Returns:
        str: 规范化后的卡号

    Raises:
        TimeoutError: 未收到任何有效卡号数据时抛出
    """
    # 打开串口，使用上下文管理器确保资源释放
    with serial.Serial(port=port, baudrate=baudrate, timeout=timeout) as ser:
        # 等待串口稳定
        time.sleep(0.2)
        # 清空输入缓冲区，避免残留数据干扰
        ser.reset_input_buffer()

        # 如果提供了命令，则写入命令（添加回车换行）
        if command:
            ser.write(command.encode("ascii") + b"\r\n")
            ser.flush()

        # 读取一行数据，忽略解码错误
        line = ser.readline().decode("utf-8", errors="ignore").strip()

    # 规范化读取到的字符串
    card_no = normalize_card_no(line)
    if not card_no:
        raise TimeoutError("no card data received")
    return card_no


def read_card(card_no=None, port=None, baudrate=9600, timeout=5):
    """
    读取卡片并验证其有效性（主入口函数）

    两种使用方式：
    1. 直接传入 card_no 字符串，仅做验证
    2. 指定串口 port，自动从串口读取卡号后再验证

    Args:
        card_no (str, optional): 手动指定的卡号，若提供则不再从串口读取
        port (str, optional): 串口号，当 card_no 为 None 时必须提供
        baudrate (int): 串口波特率
        timeout (int/float): 串口读取超时时间

    Returns:
        dict: 包含卡号及数据库验证结果的字典，形如：
              {"card_no": "12345678", "is_valid": True, "person_id": ...}

    Raises:
        ValueError: 既未提供 card_no 也未提供 port 时抛出
    """
    # 如果已提供卡号，直接规范化
    if card_no:
        detected = normalize_card_no(card_no)
    else:
        # 否则必须提供串口号，从串口读取
        if not port:
            raise ValueError("port or card_no is required")
        detected = read_card_from_serial(port=port, baudrate=baudrate, timeout=timeout)

    # 调用数据库模块验证该卡号是否已注册/合法
    verification = db.verify_card(detected)
    return {"card_no": detected, **verification}


def register_card(card_no, person_id=None, person=None, card_type="ic", status="active", remark=None):
    """
    将一张新卡注册到数据库

    Args:
        card_no (str): 原始卡号（将自动规范化）
        person_id (str/int, optional): 关联的人员 ID
        person (str, optional): 关联的人员姓名
        card_type (str): 卡片类型，默认 "ic"
        status (str): 卡片状态，默认 "active"
        remark (str, optional): 备注信息

    Returns:
        由数据库模块返回的注册结果（通常是 bool 或 dict）
    """
    normalized = normalize_card_no(card_no)
    return db.register_card(
        card_no=normalized,
        person_id=person_id,
        person=person,
        card_type=card_type,
        status=status,
        remark=remark,
    )