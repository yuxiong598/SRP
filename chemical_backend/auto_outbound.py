"""
自动领用对接模块
整合卡片读取、摄像头拍照、OCR识别、重量读取等硬件模块
自动完成领用流程
"""
import base64
import time
import tempfile
import os
import card_module
import weight_module
import camera_module
import ocr_module
import database_moudle as db


def auto_outbound_workflow(
    card_port='COM3',
    weight_port='COM4',
    camera_id=0,
    card_baudrate=9600,
    weight_baudrate=9600,
    timeout=10
):
    """
    自动领用完整流程

    流程：
    1. 从串口自动读取卡片信息（领用人）
    2. 从摄像头拍摄化学品照片
    3. OCR识别化学品信息
    4. 从串口读取重量数据
    5. 自动匹配数据库中的化学品
    6. 返回所有领用信息供前端确认

    Args:
        card_port: 读卡器串口号
        weight_port: 天平串口号
        camera_id: 摄像头ID
        card_baudrate: 读卡器波特率
        weight_baudrate: 天平波特率
        timeout: 超时时间（秒）

    Returns:
        dict: 包含所有领用信息的字典，包括：
            - card_no: 卡号
            - person_name: 领用人姓名
            - person_id: 人员ID
            - chemical_name: 化学品名称
            - chemical_id: 化学品ID（如果匹配到）
            - weight: 重量（克）
            - ocr_result: OCR识别结果
            - image_path: 图片路径
            - confidence: OCR置信度
    """
    result = {
        'success': False,
        'card_no': None,
        'person_name': None,
        'person_id': None,
        'chemical_name': None,
        'chemical_id': None,
        'weight': None,
        'ocr_result': None,
        'image_base64': None,
        'image_path': None,
        'confidence': None,
        'error': None
    }

    try:
        # 1. 读取卡片信息（领用人）
        print("步骤1: 读取卡片...")
        card_data = card_module.read_card(
            port=card_port,
            baudrate=card_baudrate,
            timeout=timeout
        )

        if not card_data.get('valid'):
            result['error'] = f"卡片验证失败: {card_data.get('reason', '未知原因')}"
            return result

        result['card_no'] = card_data['card_no']
        card_info = card_data.get('card', {})
        result['person_name'] = card_info.get('person_name')
        result['person_id'] = card_info.get('person_id')
        print(f"  卡号: {result['card_no']}, 领用人: {result['person_name']}")

        # 2. 拍摄化学品照片
        print("步骤2: 拍摄化学品照片...")
        image_path = camera_module.capture_chemical_image(
            camera_id=camera_id,
            save_dir=tempfile.gettempdir()
        )

        if not image_path:
            result['error'] = "无法拍摄化学品照片"
            return result

        result['image_path'] = image_path

        # 将图片转为 base64
        try:
            with open(image_path, 'rb') as f:
                image_base64 = base64.b64encode(f.read()).decode('utf-8')
                result['image_base64'] = f"data:image/jpeg;base64,{image_base64}"
        except Exception as e:
            print(f"  图片转base64失败: {e}")

        print(f"  图片已保存: {image_path}")

        # 3. OCR识别化学品信息
        print("步骤3: OCR识别...")
        ocr_result = ocr_module.recognize_chemical_label(
            image_path,
            db.find_chemical_candidates()
        )

        result['ocr_result'] = ocr_result
        result['chemical_name'] = ocr_result.get('name')
        result['confidence'] = ocr_result.get('confidence')
        print(f"  识别结果: {result['chemical_name']} (置信度: {result['confidence']})")

        # 4. 匹配数据库中的化学品
        if result['chemical_name']:
            # 尝试通过名称匹配
            chemicals = db.list_chemicals(keyword=result['chemical_name'])
            if chemicals:
                # 找到第一个匹配的化学品
                matched = chemicals[0]
                result['chemical_id'] = matched['id']
                result['chemical_name'] = matched['name']
                print(f"  匹配到化学品: {matched['name']} (ID: {matched['id']})")

        # 5. 读取重量数据
        print("步骤4: 读取重量...")
        weight = weight_module.read_weight_from_balance(
            port=weight_port,
            baudrate=weight_baudrate
        )

        if weight is not None:
            result['weight'] = weight
            print(f"  重量: {weight} 克")
        else:
            print("  警告: 未能读取到重量数据")

        result['success'] = True
        return result

    except Exception as e:
        result['error'] = str(e)
        print(f"自动领用流程出错: {e}")
        return result


def confirm_auto_outbound(user_id, auto_result, quantity=None, purpose='', project_name=''):
    """
    确认自动领用并写入数据库

    Args:
        user_id: 操作人ID
        auto_result: auto_outbound_workflow返回的结果
        quantity: 领用数量（如果为None，使用重量数据）
        purpose: 用途
        project_name: 项目名称

    Returns:
        dict: 包含transaction信息的字典
    """
    if not auto_result.get('success'):
        raise ValueError("自动领用流程未成功完成")

    if not auto_result.get('chemical_id'):
        raise ValueError("未匹配到化学品，请手动选择")

    # 如果没有指定数量，使用重量
    if quantity is None:
        quantity = auto_result.get('weight')
        if quantity is None:
            raise ValueError("未指定数量且无法读取重量")

    # 创建出库记录
    tx = db.create_inventory_transaction(
        transaction_type='outbound',
        chemical_id=auto_result['chemical_id'],
        quantity=quantity,
        applicant={
            'id': auto_result['person_id'],
            'name': auto_result['person_name']
        },
        handler=db.get_user(user_id),
        card_no=auto_result['card_no'],
        project_name=project_name,
        purpose=purpose or '自动领用',
        remark=f"OCR识别: {auto_result.get('chemical_name')}, 置信度: {auto_result.get('confidence')}"
    )

    # 记录操作日志
    db.log_action(
        'auto_outbound.complete',
        db.get_user(user_id),
        'transaction',
        tx['id'],
        tx['transaction_no']
    )

    return tx


# 测试函数
def test_workflow():
    """测试自动领用流程"""
    print("=" * 50)
    print("开始测试自动领用流程")
    print("=" * 50)

    result = auto_outbound_workflow(
        card_port='COM3',
        weight_port='COM4',
        camera_id=0,
        timeout=10
    )

    print("\n" + "=" * 50)
    print("测试结果:")
    print("=" * 50)
    for key, value in result.items():
        print(f"{key}: {value}")

    return result


if __name__ == '__main__':
    test_workflow()