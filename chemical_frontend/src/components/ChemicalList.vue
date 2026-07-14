<template>
  <el-card header="化学品动态清单">
    <div class="list-header">
      <el-input v-model="searchKeyword" placeholder="输入化学品名称搜索" style="width: 250px" clearable @clear="fetchData" @keyup.enter="fetchData">
        <template #append>
          <el-button @click="fetchData">搜索</el-button>
        </template>
      </el-input>
      <el-button type="success" @click="exportToExcel">导出 Excel</el-button>
    </div>
    <el-table :data="chemicalList" border stripe style="width: 100%; margin-top: 16px">
      <el-table-column prop="name" label="名称" />
      <el-table-column prop="specification" label="规格" />
      <el-table-column prop="stock" label="库存量" />
      <el-table-column prop="hazard" label="危害等级" />
      <el-table-column prop="location" label="存放位置" />
    </el-table>
  </el-card>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getChemicalList } from '../api'
import { ElMessage } from 'element-plus'
import * as XLSX from 'xlsx'

const chemicalList = ref([])
const searchKeyword = ref('')

async function fetchData() {
  try {
    const res = await getChemicalList(searchKeyword.value)
    chemicalList.value = res.data
  } catch (err) {
    ElMessage.error('获取清单失败')
  }
}

function exportToExcel() {
  const ws = XLSX.utils.json_to_sheet(chemicalList.value)
  const wb = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, ws, '化学品清单')
  XLSX.writeFile(wb, `chemicals_${new Date().toISOString().slice(0,19)}.xlsx`)
  ElMessage.success('导出成功')
}

onMounted(fetchData)
</script>

<style scoped>
.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>