<template>
  <el-card header="化学品识别结果">
    <el-form :model="chemical" label-width="100px" v-if="chemical">
      <el-form-item label="化学品名称">
        <el-input v-model="chemical.name" />
      </el-form-item>
      <el-form-item label="规格">
        <el-input v-model="chemical.specification" />
      </el-form-item>
      <el-form-item label="危害信息">
        <el-input v-model="chemical.hazard" />
      </el-form-item>
      <el-form-item label="其他信息">
        <el-input v-model="chemical.extra" placeholder="如：批号、有效期" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="confirm">确认并提交</el-button>
        <el-button @click="reset">重置为识别结果</el-button>
      </el-form-item>
    </el-form>
    <el-empty v-else description="还未识别试剂瓶标签，请先拍照上传" />
  </el-card>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  originalResult: {
    type: Object,
    default: null
  }
})
const emit = defineEmits(['confirm'])

const chemical = ref(null)

watch(() => props.originalResult, (newVal) => {
  if (newVal) {
    chemical.value = { ...newVal }
  } else {
    chemical.value = null
  }
}, { immediate: true, deep: true })

function reset() {
  if (props.originalResult) {
    chemical.value = { ...props.originalResult }
  }
}

function confirm() {
  emit('confirm', chemical.value)
}
</script>