# 化学品智能采集系统 - 统一自动化工作流设计
设计日期：2026-07-15  
设计者：MooNa  

## 背景与目标

### 项目背景
化学品智能采集系统已实现基础的自动领用功能（outbound），通过硬件集成（读卡器、摄像头、天平、OCR）简化了领用流程。当前需要将同样的自动化范式扩展到其他三个核心操作：入库（inbound）、归还（return）、出库（discard）。

### 设计目标
1. 创建统一的自动化框架，支持四种操作类型
2. 最大化代码复用，减少重复
3. 保持硬件接口一致性
4. 维护清晰的业务逻辑分离
5. 便于未来扩展新操作类型
6. 符合用户"简洁、避免复杂语法、详细注释"的要求

## 架构设计

### 整体架构
```text
auto_workflows.py (统一自动化核心模块)
├── auto_workflow()              # 主入口函数，接收操作类型参数
├── OperationType枚举类         # 定义四种操作类型常量
├── CommonHardwareLayer类       # 通用硬件调用层（复用现有模块）
└── BusinessLogicLayer类        # 业务逻辑层（各操作特有的数据处理）

app.py → 新增/auto/workflow端点，通过operation参数区分操作
前端 → 统一调用autoWorkflow API，传递operation参数
```

### 核心模块关系
```
┌─────────────────────────────────────────────┐
│                 前端界面                     │
│  入库按钮 领用按钮 归还按钮 出库按钮        │
└─────────────┬────────────────────────────────┘
              │ (operation参数)
              ▼
┌─────────────────────────────────────────────┐
│           统一API端点 /auto/workflow         │
└─────────────┬────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────┐
│     auto_workflow(operation_type, ...)      │
└────────────────┬───────────────┬────────────┘
                 │               │
             硬件层             业务逻辑层
   (读卡、拍照、OCR、称重)      (数据库操作)
```

## 数据流程设计

### 1. 通用硬件数据流
```
读卡器 → 卡片信息(person_id, person_name, card_no)
   ↓
摄像头 → 化学品图片(base64编码)
   ↓
OCR模块 → 化学品识别(name, confidence)
   ↓
天平 → 重量数据(grams)
```

### 2. 业务逻辑数据流（按操作类型）

#### 入库(inbound)：
```
硬件数据 → 匹配/创建化学品记录 → 增加库存数量
               ↓
         记录入库时间和操作人
```

#### 领用(outbound)：（已实现）
```
硬件数据 → 匹配化学品 → 减少库存数量
               ↓
         记录领用时间、领用人、领用重量
```

#### 归还(return)：
```
硬件数据 → 匹配化学品 → 增加库存数量
               ↓
         记录归还时间、归还人、归还重量
```

#### 出库(discard)：
```
硬件数据 → 匹配化学品 → 确认弃用 → 记录出库
               ↓
         记录出库时间、操作人、废弃原因
```

## API接口设计

### 后端API端点
```python
POST /auto/workflow
{
    "operation": "inbound" | "outbound" | "return" | "discard",
    "config": {
        "card_port": "COM3",
        "weight_port": "COM4",
        "camera_id": 0,
        "timeout": 10,
        "quantity": null,  # 可选，覆盖自动读取的重量
        "purpose": "",     # 用途说明
        "project_name": "", # 项目名称
        "discard_reason": "" # 出库专用：废弃原因
    }
}
```

### 前端API模块
```javascript
// 统一的API调用
export function autoWorkflow(operation, config = {}) {
    return request.post('/auto/workflow', {
        operation: operation,
        config: config
    });
}

// 各操作的便捷方法
export const autoInbound = (config) => autoWorkflow('inbound', config);
export const autoOutbound = (config) => autoWorkflow('outbound', config);
export const autoReturn = (config) => autoWorkflow('return', config);
export const autoDiscard = (config) => autoWorkflow('discard', config);
```

## 业务逻辑设计

### 数据库操作差异
| 操作类型 | 事务类型 | 库存变化 | 特殊字段 |
|----------|----------|----------|----------|
| 入库(inbound) | 'inbound' | 增加(+quantity) | - |
| 领用(outbound) | 'outbound' | 减少(-quantity) | 已实现 |
| 归还(return) | 'return' | 增加(+quantity) | 关联原领用记录 |
| 出库(discard) | 'discard' | 减少至0 | reason字段 |

### 业务逻辑函数签名
```python
def process_inbound_logic(hardware_data, user_data):
    """入库逻辑：增加库存，记录入库"""
    pass

def process_outbound_logic(hardware_data, user_data):
    """领用逻辑：减少库存，记录领用（已实现）"""
    pass

def process_return_logic(hardware_data, user_data):
    """归还逻辑：增加库存，关联原记录"""
    pass

def process_discard_logic(hardware_data, user_data):
    """出库逻辑：标记为废弃，记录原因"""
    pass
```

## 错误处理机制

### 错误级别
1. **硬件级错误**：串口连接失败、摄像头故障、OCR识别失败
2. **业务级错误**：化学品不匹配、库存不足、权限不足
3. **系统级错误**：数据库连接失败、API异常

### 处理策略
```python
error_strategies = {
    'hardware_error': {
        'action': 'retry_or_fallback',
        'max_retries':8753,
        'fallback': 'manual_input'
    },
    'business_error': {
        'action': 'user_intervention',
        'message': '友好错误提示，建议操作'
    },
    'system_error': {
        'action': 'log_and_alert',
        'recovery': '自动重试或等待修复'
    }
}
```

### 状态流转与回滚
```
开始 → 硬件采集 → 业务处理 → 数据库更新 → 完成
    ↓          ↓           ↓
硬件失败    业务验证失败  数据库失败
    ↓          ↓           ↓
重试/手动    提示用户     回滚事务
```

## 实施计划

### 第一阶段：框架搭建（1-2天）
1. 创建 `auto_workflows.py` 基础框架
2. 定义 `OperationType` 枚举和通用硬件层
3. 测试框架与现有outbound的兼容性

### 第二阶段：业务逻辑实现（2-3天）
1. 实现 `process_inbound_logic()` 入库逻辑
2. 实现 `process_return_logic()` 归还逻辑  
3. 实现 `process_discard_logic()` 出库逻辑
4. 添加相应的数据库操作方法

### 第三阶段：API集成（1天）
1. 修改 `app.py` 添加 `/auto/workflow` 端点
2. 创建前端统一API模块 `autoWorkflow.js`
3. 更新现有 `autoOutbound.js` 兼容新API

### 第四阶段：前端界面更新（1天）
1. 修改 `UserDashboard.vue` 四个按钮统一调用
2. 添加操作类型的提示和状态反馈
3. 测试完整流程

### 第五阶段：测试与优化（1-2天）
1. 硬件集成测试（模拟+真实设备）
2. 业务逻辑单元测试
3. 端到端流程测试
4. 性能优化和错误处理测试

## 测试方案

### 硬件模拟测试
```python
# 使用mock对象模拟硬件模块
hardware_mocks = {
    'card_module': MockCardReader(return_valid_card=True),
    'camera_module': MockCamera(return_image=True),
    'ocr_module': MockOCR(return_chemical='乙醇'),
    'weight_module': MockBalance(return_weight=500.0)
}
```

### 业务逻辑测试用例
1. 正常流程测试：四种操作类型完整流程
2. 边界条件测试：库存为0时的领用、重复归还等
3. 错误场景测试：硬件故障、识别失败、数据库异常
4. 并发测试：多用户同时操作同一化学品

### 前端测试
1. 按钮点击响应和状态更新
2. API调用错误处理和重试
3. 图片和数据显示正确性

## 迁移策略

### 向后兼容性
1. 保留原有 `/auto/outbound` 端点一段时间
2. 逐步迁移前端调用到新API
3. 并行运行验证新框架稳定性

### 数据迁移
无需数据迁移，新框架使用现有数据库结构

### 文档更新
1. 更新API文档说明统一接口
2. 更新用户操作手册
3. 维护版本的更新日志

## 扩展性考虑

### 未来硬件扩展
新硬件设备（如二维码扫描仪、RFID阅读器）只需：
1. 添加硬件模块到 `CommonHardwareLayer`
2. 在workflow中调用相应方法
3. 无需修改业务逻辑层

### 新操作类型扩展
添加新操作类型只需：
1. 扩展 `OperationType` 枚举
2. 实现对应的 `process_{new}_logic()` 函数
3. 更新前端调用

### 配置化管理
```python
# 未来可扩展为配置文件驱动
OPERATION_CONFIGS = {
    'inbound': {
        'hardware_needed': ['card', 'camera', 'ocr', 'weight'],
        'business_logic': process_inbound_logic,
        'confirm_required': True
    },
    # ...其他操作配置
}
```

## 风险与缓解措施

### 风险1：硬件集成复杂度
- **缓解**：保持模块化设计，每个硬件模块独立
- **测试**：充分的硬件模拟测试和真实设备测试

### 风险2：业务逻辑耦合
- **缓解**：清晰分层，硬件层与业务逻辑层分离
- **监控**：添加详细的日志记录操作流程

### 风险3：用户接受度
- **缓解**：渐进式迁移，保留原有功能，提供培训文档
- **反馈**：收集用户反馈，快速迭代优化

## 成功标准

1. **功能完整性**：四种操作类型全部实现自动化
2. **代码简洁度**：相比独立文件方案减少70%重复代码
3. **维护便利性**：单一入口修改硬件接口
4. **用户满意度**：操作流程更顺畅，错误处理更友好
5. **扩展便利性**：未来添加新操作类型可在1天内完成

---

*设计评审通过后，将创建详细的实施计划和代码实现。*