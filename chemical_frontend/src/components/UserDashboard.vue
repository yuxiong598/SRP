<template>
  <div class="user-dashboard">
    <!-- 顶部栏 -->
    <div class="header">
      <div class="header-left">
        <div class="logo-icon">化</div>
        <h2>化学品智能采集系统</h2>
      </div>
      <div class="header-right">
        <span>{{ user.name }}</span>
        <el-button size="small" @click="$emit('logout')">退出</el-button>
      </div>
    </div>

    <!-- 四个功能按钮 -->
    <div class="button-grid">
      <div class="action-card" @click="openDialog('inbound')">
        <div class="icon-wrapper" style="background: #10b981;">
          <el-icon size="40"><Plus /></el-icon>
        </div>
        <h3>入库</h3>
        <p>新增化学品入库</p>
      </div>

      <div class="action-card" @click="startAutoOutbound">
        <div class="icon-wrapper" style="background: #3b82f6;">
          <el-icon size="40"><ShoppingCart /></el-icon>
        </div>
        <h3>领用</h3>
        <p>自动识别并领取化学品</p>
      </div>

      <div class="action-card" @click="openDialog('return')">
        <div class="icon-wrapper" style="background: #8b5cf6;">
          <el-icon size="40"><RefreshLeft /></el-icon>
        </div>
        <h3>归还</h3>
        <p>归还已使用化学品</p>
      </div>

      <div class="action-card" @click="openDialog('discard')">
        <div class="icon-wrapper" style="background: #ef4444;">
          <el-icon size="40"><Delete /></el-icon>
        </div>
        <h3>出库</h3>
        <p>废弃化学品出库</p>
      </div>
    </div>

    <!-- 底部信息 -->
    <div class="footer">
      <p>当前库存总数: <strong>{{ summary.total_chemicals || 0 }}</strong> 种化学品</p>
    </div>

    <!-- 入库对话框 -->
    <el-dialog
      v-model="dialogVisible.inbound"
      title="化学品入库"
      width="400px"
      :close-on-click-modal="false"
    >
      <el-form :model="inboundForm" label-width="80px">
        <el-form-item label="化学品">
          <el-select v-model="inboundForm.chemical_id" placeholder="选择化学品" filterable style="width: 100%;">
            <el-option
              v-for="item in chemicals"
              :key="item.id"
              :label="`${item.name} (库存: ${item.stock}${item.unit})`"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="入库数量">
          <el-input-number v-model="inboundForm.quantity" :min="0" :precision="2" style="width: 100%;" />
        </el-form-item>
        <el-form-item label="项目名称">
          <el-input v-model="inboundForm.project_name" placeholder="可选" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="inboundForm.remark" type="textarea" placeholder="可选" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible.inbound = false">取消</el-button>
        <el-button type="primary" @click="submitInbound">确认入库</el-button>
      </template>
    </el-dialog>

    <!-- 领用对话框 -->
    <el-dialog
      v-model="dialogVisible.outbound"
      title="化学品领用"
      width="400px"
      :close-on-click-modal="false"
    >
      <el-form :model="outboundForm" label-width="80px">
        <el-form-item label="刷卡卡号">
          <el-input v-model="outboundForm.card_no" placeholder="请刷卡或输入卡号">
            <template #append>
              <el-button @click="verifyCard">验卡</el-button>
            </template>
          </el-input>
        </el-form-item>
        <el-alert
          v-if="cardInfo"
          :title="`领用人: ${cardInfo.person_name}`"
          type="success"
          :closable="false"
          style="margin-bottom: 16px;"
        />
        <el-form-item label="化学品">
          <el-select v-model="outboundForm.chemical_id" placeholder="选择化学品" filterable style="width: 100%;">
            <el-option
              v-for="item in chemicals"
              :key="item.id"
              :label="`${item.name} (库存: ${item.stock}${item.unit})`"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="领用数量">
          <el-input-number v-model="outboundForm.quantity" :min="0" :precision="2" style="width: 100%;" />
        </el-form-item>
        <el-form-item label="用途">
          <el-input v-model="outboundForm.purpose" placeholder="请说明用途" />
        </el-form-item>
        <el-form-item label="项目名称">
          <el-input v-model="outboundForm.project_name" placeholder="可选" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible.outbound = false">取消</el-button>
        <el-button type="primary" @click="submitOutbound">确认领用</el-button>
      </template>
    </el-dialog>

    <!-- 归还对话框 -->
    <el-dialog
      v-model="dialogVisible.return"
      title="化学品归还"
      width="400px"
      :close-on-click-modal="false"
    >
      <el-form :model="returnForm" label-width="80px">
        <el-form-item label="化学品">
          <el-select v-model="returnForm.chemical_id" placeholder="选择化学品" filterable style="width: 100%;">
            <el-option
              v-for="item in chemicals"
              :key="item.id"
              :label="item.name"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="归还数量">
          <el-input-number v-model="returnForm.quantity" :min="0" :precision="2" style="width: 100%;" />
        </el-form-item>
        <el-form-item label="项目名称">
          <el-input v-model="returnForm.project_name" placeholder="可选" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible.return = false">取消</el-button>
        <el-button type="primary" @click="submitReturn">确认归还</el-button>
      </template>
    </el-dialog>

    <!-- 出库(弃用)对话框 -->
    <el-dialog
      v-model="dialogVisible.discard"
      title="化学品出库(弃用)"
      width="400px"
      :close-on-click-modal="false"
    >
      <el-form label-width="80px">
        <el-form-item label="化学品">
          <el-select v-model="discardChemicalId" placeholder="选择化学品" filterable style="width: 100%;">
            <el-option
              v-for="item in chemicals"
              :key="item.id"
              :label="`${item.name} (库存: ${item.stock}${item.unit})`"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <el-alert
        type="warning"
        :closable="false"
        style="margin-top: 16px;"
      >
        <template #title>注意：出库将删除该化学品记录</template>
      </el-alert>
      <template #footer>
        <el-button @click="dialogVisible.discard = false">取消</el-button>
        <el-button type="danger" @click="submitDiscard">确认出库</el-button>
      </template>
    </el-dialog>

    <!-- 自动领用确认对话框 -->
    <el-dialog
      v-model="dialogVisible.autoOutboundConfirm"
      title="自动领用确认"
      width="450px"
      :close-on-click-modal="false"
    >
      <div v-if="autoOutboundResult" class="auto-result">
        <el-alert v-if="!autoOutboundResult.success" :title="`自动领用失败: ${autoOutboundResult.error}`" type="error" :closable="false" />
        <div v-else>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="领用人">{{ autoOutboundResult.person_name }}</el-descriptions-item>
            <el-descriptions-item label="卡号">{{ autoOutboundResult.card_no }}</el-descriptions-item>
            <el-descriptions-item label="化学品">{{ autoOutboundResult.chemical_name || '未识别' }}</el-descriptions-item>
            <el-descriptions-item label="重量(g)">{{ autoOutboundResult.weight ?? '--' }}</el-descriptions-item>
            <el-descriptions-item label="置信度">{{ autoOutboundResult.confidence ?? '--' }}</el-descriptions-item>
          </el-descriptions>
          <img
            v-if="autoOutboundResult.image_base64"
            :src="autoOutboundResult.image_base64"
            class="chemical-preview"
            alt="化学品照片"
          />
        </div>
      </div>
      <template #footer>
        <el-button @click="dialogVisible.autoOutboundConfirm = false">取消</el-button>
        <el-button type="primary" @click="confirmAutoOutboundSubmit">确认领用</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox, ElLoading } from 'element-plus'
import { Plus, ShoppingCart, RefreshLeft, Delete } from '@element-plus/icons-vue'
import {
  getChemicalList,
  getDashboardSummary,
  inventoryInbound,
  inventoryOutbound,
  inventoryReturn,
  deleteChemical,
  verifyCard as verifyCardApi,
} from '../api'
import {
  autoOutbound,
  confirmAutoOutbound
} from '../api/autoOutbound'

defineEmits(['logout'])

const props = defineProps({
  user: Object
})

// 状态
const chemicals = ref([])
const summary = ref({})
const cardInfo = ref(null)
const autoOutboundResult = ref(null)

// 对话框显示状态
const dialogVisible = reactive({
  inbound: false,
  outbound: false,
  return: false,
  discard: false,
  autoOutboundConfirm: false
})

// 入库表单
const inboundForm = reactive({
  chemical_id: null,
  quantity: 1,
  project_name: '',
  remark: ''
})

// 领用表单
const outboundForm = reactive({
  card_no: '',
  chemical_id: null,
  quantity: 1,
  purpose: '',
  project_name: ''
})

// 归还表单
const returnForm = reactive({
  chemical_id: null,
  quantity: 1,
  project_name: ''
})

// 出库化学品ID
const discardChemicalId = ref(null)

// 获取数据
async function fetchData() {
  try {
    const [chemRes, summaryRes] = await Promise.all([
      getChemicalList(),
      getDashboardSummary()
    ])
    chemicals.value = chemRes.data
    summary.value = summaryRes.data
  } catch (error) {
    ElMessage.error('获取数据失败')
  }
}

// 打开对话框
function openDialog(type) {
  // 重置表单
  if (type === 'inbound') {
    Object.assign(inboundForm, { chemical_id: null, quantity: 1, project_name: '', remark: '' })
  } else if (type === 'outbound') {
    Object.assign(outboundForm, { card_no: '', chemical_id: null, quantity: 1, purpose: '', project_name: '' })
    cardInfo.value = null
  } else if (type === 'return') {
    Object.assign(returnForm, { chemical_id: null, quantity: 1, project_name: '' })
  } else if (type === 'discard') {
    discardChemicalId.value = null
  }
  dialogVisible[type] = true
}

// 启动自动领用流程
async function startAutoOutbound() {
  let loading = null
  try {
    loading = ElLoading.service({
      lock: true,
      text: '正在自动读取卡片、拍照识别、读取重量...',
      background: 'rgba(0, 0, 0, 0.7)'
    })

    const res = await autoOutbound({
      card_port: 'COM3',
      weight_port: 'COM4',
      camera_id: 0,
      timeout: 15
    })

    loading.close()

    autoOutboundResult.value = res.data
    dialogVisible.autoOutboundConfirm = true
  } catch (error) {
    loading && loading.close()
    ElMessage.error(error?.response?.data?.error || '自动领用失败')
  }
}

// 确认自动领用并提交
async function confirmAutoOutboundSubmit() {
  if (!autoOutboundResult.value || !autoOutboundResult.value.success) {
    ElMessage.warning('自动领用数据无效')
    return
  }

  let loading = null
  try {
    loading = ElLoading.service({
      lock: true,
      text: '正在提交领用记录...',
      background: 'rgba(0, 0, 0, 0.7)'
    })

    await confirmAutoOutbound(
      autoOutboundResult.value,
      autoOutboundResult.value.weight,
      '自动领用',
      ''
    )

    loading.close()
    dialogVisible.autoOutboundConfirm = false
    await fetchData()
    ElMessage.success('自动领用成功')
  } catch (error) {
    loading && loading.close()
    ElMessage.error(error?.response?.data?.error || '领用提交失败')
  }
}

// 验证卡片
async function verifyCard() {
  if (!outboundForm.card_no) {
    ElMessage.warning('请输入卡号')
    return
  }
  try {
    const res = await verifyCardApi(outboundForm.card_no)
    if (res.data.valid) {
      cardInfo.value = res.data.card
      ElMessage.success(`验卡成功: ${res.data.card.person_name}`)
    } else {
      cardInfo.value = null
      ElMessage.warning(res.data.reason || '卡片无效')
    }
  } catch (error) {
    ElMessage.error(error?.response?.data?.error || '验卡失败')
  }
}

// 提交入库
async function submitInbound() {
  if (!inboundForm.chemical_id) {
    ElMessage.warning('请选择化学品')
    return
  }
  try {
    await inventoryInbound(inboundForm)
    dialogVisible.inbound = false
    await fetchData()
    ElMessage.success('入库成功')
  } catch (error) {
    ElMessage.error(error?.response?.data?.error || '入库失败')
  }
}

// 提交领用
async function submitOutbound() {
  if (!outboundForm.card_no) {
    ElMessage.warning('请刷卡或输入卡号')
    return
  }
  if (!outboundForm.chemical_id) {
    ElMessage.warning('请选择化学品')
    return
  }
  try {
    await inventoryOutbound(outboundForm)
    dialogVisible.outbound = false
    await fetchData()
    ElMessage.success('领用成功')
  } catch (error) {
    ElMessage.error(error?.response?.data?.error || '领用失败')
  }
}

// 提交归还
async function submitReturn() {
  if (!returnForm.chemical_id) {
    ElMessage.warning('请选择化学品')
    return
  }
  try {
    await inventoryReturn(returnForm)
    dialogVisible.return = false
    await fetchData()
    ElMessage.success('归还成功')
  } catch (error) {
    ElMessage.error(error?.response?.data?.error || '归还失败')
  }
}

// 提交出库(弃用)
async function submitDiscard() {
  if (!discardChemicalId.value) {
    ElMessage.warning('请选择化学品')
    return
  }
  try {
    await ElMessageBox.confirm('确认要出库(弃用)该化学品吗？此操作不可恢复。', '确认出库', {
      type: 'warning'
    })
    await deleteChemical(discardChemicalId.value)
    dialogVisible.discard = false
    await fetchData()
    ElMessage.success('出库成功')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error?.response?.data?.error || '出库失败')
    }
  }
}

onMounted(fetchData)
</script>

<style scoped>
.user-dashboard {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f5f7fa;
}

.header {
  height: 70px;
  background: white;
  border-bottom: 1px solid #e5e7eb;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 40px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 15px;
}

.logo-icon {
  width: 40px;
  height: 40px;
  display: grid;
  place-items: center;
  background: #667eea;
  color: white;
  border-radius: 8px;
  font-size: 20px;
  font-weight: 700;
}

.header-left h2 {
  margin: 0;
  font-size: 20px;
  color: #333;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 15px;
}

.header-right span {
  color: #666;
}

/* 功能按钮网格 */
.button-grid {
  flex: 1;
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 30px;
  padding: 60px 40px;
  max-width: 1400px;
  margin: 0 auto;
  width: 100%;
}

.action-card {
  background: white;
  border-radius: 16px;
  padding: 40px 30px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.action-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
}

.icon-wrapper {
  width: 80px;
  height: 80px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 20px;
  border-radius: 50%;
  color: white;
}

.action-card h3 {
  font-size: 22px;
  color: #333;
  margin: 0 0 10px;
}

.action-card p {
  font-size: 14px;
  color: #999;
  margin: 0;
}

/* 底部信息 */
.footer {
  padding: 20px 40px;
  text-align: center;
  color: #999;
  font-size: 14px;
}

.footer strong {
  color: #667eea;
}

/* 自动领用结果 */
.auto-result {
  max-height: 60vh;
  overflow-y: auto;
}

.chemical-preview {
  width: 100%;
  max-height: 250px;
  object-fit: contain;
  margin-top: 16px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #f9fafb;
}
@media (max-width: 1100px) {
  .button-grid {
    grid-template-columns: repeat(2, 1fr);
    padding: 40px 30px;
  }
}

@media (max-width: 600px) {
  .button-grid {
    grid-template-columns: 1fr;
    gap: 20px;
    padding: 30px 20px;
  }

  .header {
    padding: 0 20px;
  }

  .header-left h2 {
    font-size: 16px;
  }
}
</style>