<template>
  <div class="weight-module">
    <el-card header="天平称重">
      <div class="weight-display">
        <span class="label">当前毛重：</span>
        <span class="value">{{ currentGrossWeight !== null ? currentGrossWeight.toFixed(2) : '--' }} 克</span>
        <el-button size="small" @click="manualFetchWeight" :loading="loading">读取重量</el-button>
      </div>
      <div class="weight-display" v-if="tareWeight > 0">
        <span class="label">当前净重：</span>
        <span class="value">{{ netWeight !== null ? netWeight.toFixed(2) : '--' }} 克</span>
      </div>
      <div class="actions">
        <el-button type="primary" @click="setTare" :loading="loading">去皮</el-button>
        <el-button @click="recordBefore" :loading="loading">使用前</el-button>
        <el-button @click="recordAfter" :loading="loading">使用后</el-button>
      </div>
      <div v-if="beforeWeight !== null" class="record">
        使用前净重: {{ beforeWeight.toFixed(2) }} 克
      </div>
      <div v-if="afterWeight !== null" class="record">
        使用后净重: {{ afterWeight.toFixed(2) }} 克
      </div>
      <div v-if="usage !== null" class="usage">
        用量: {{ usage.toFixed(2) }} 克
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { getCurrentWeight } from '../api'
import { ElMessage } from 'element-plus'

const emit = defineEmits(['beforeWeightRecorded', 'afterWeightRecorded'])

const currentGrossWeight = ref(null)   // 最后一次从天平读取的毛重（克）
const tareWeight = ref(0)              // 皮重（克）
const beforeWeight = ref(null)         // 使用前净重
const afterWeight = ref(null)          // 使用后净重
const usage = ref(null)                // 用量
const loading = ref(false)

const netWeight = computed(() => {
  if (currentGrossWeight.value === null) return null
  return currentGrossWeight.value - tareWeight.value
})

async function manualFetchWeight() {
  if (loading.value) return
  loading.value = true
  try {
    const res = await getCurrentWeight()
    currentGrossWeight.value = res.data.weight
    ElMessage.success(`读取成功：${currentGrossWeight.value.toFixed(2)} 克`)
  } catch (err) {
    console.error('获取天平数据失败', err)
    ElMessage.error('获取天平数据失败，请检查串口连接')
    currentGrossWeight.value = null
  } finally {
    loading.value = false
  }
}

async function setTare() {
  await manualFetchWeight()
  if (currentGrossWeight.value !== null) {
    tareWeight.value = currentGrossWeight.value
    ElMessage.success(`去皮完成，当前净重归零（皮重 ${tareWeight.value.toFixed(2)} 克）`)
  }
}

async function recordBefore() {
  await manualFetchWeight()
  if (netWeight.value !== null) {
    beforeWeight.value = netWeight.value
    emit('beforeWeightRecorded', beforeWeight.value)
    ElMessage.info(`记录使用前重量: ${beforeWeight.value.toFixed(2)} 克`)
  }
}

async function recordAfter() {
  if (beforeWeight.value === null) {
    ElMessage.warning('请先记录“使用前”重量')
    return
  }
  await manualFetchWeight()
  if (netWeight.value !== null) {
    afterWeight.value = netWeight.value
    usage.value = afterWeight.value - beforeWeight.value
    emit('afterWeightRecorded', { after: afterWeight.value, usage: usage.value })
    ElMessage.success(`记录使用后重量: ${afterWeight.value.toFixed(2)} 克，用量: ${usage.value.toFixed(2)} 克`)
  }
}
</script>

<style scoped>
.weight-module { margin-bottom: 20px; }
.weight-display { font-size: 20px; margin-bottom: 12px; }
.label { font-weight: bold; }
.value { color: #409eff; margin-left: 8px; }
.actions { margin-bottom: 12px; }
.record { margin-top: 8px; color: #666; }
.usage { margin-top: 12px; font-weight: bold; color: #e6a23c; }
</style>