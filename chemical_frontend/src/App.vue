<template>
  <div class="app-shell">
    <section v-if="!user" class="auth-screen">
      <div class="auth-panel">
        <div class="brand">
          <div class="brand-mark">化</div>
          <div>
            <h1>化学品安全管理系统</h1>
            <p>库存、刷卡、OCR、审批和危化品管控一体化工作台</p>
          </div>
        </div>

        <el-tabs v-model="authMode" stretch>
          <el-tab-pane label="登录" name="login">
            <el-form :model="loginForm" label-position="top" @keyup.enter="login">
              <el-form-item label="用户名">
                <el-input v-model="loginForm.username" :prefix-icon="User" placeholder="admin" />
              </el-form-item>
              <el-form-item label="密码">
                <el-input v-model="loginForm.password" :prefix-icon="Lock" type="password" show-password placeholder="admin123" />
              </el-form-item>
              <el-button type="primary" class="wide-button" :icon="SwitchButton" :loading="authLoading" @click="login">
                登录系统
              </el-button>
            </el-form>
          </el-tab-pane>
          <el-tab-pane label="注册" name="register">
            <el-form :model="registerForm" label-position="top" @keyup.enter="register">
              <el-form-item label="用户名">
                <el-input v-model="registerForm.username" />
              </el-form-item>
              <el-form-item label="姓名">
                <el-input v-model="registerForm.name" />
              </el-form-item>
              <el-form-item label="密码">
                <el-input v-model="registerForm.password" type="password" show-password />
              </el-form-item>
              <el-alert title="注册账号默认为普通使用人；库管和安全管理员权限由管理员配置。" type="info" show-icon :closable="false" />
              <el-button type="success" class="wide-button" :icon="Plus" :loading="authLoading" @click="register">
                注册并登录
              </el-button>
            </el-form>
          </el-tab-pane>
        </el-tabs>
      </div>
    </section>

    <el-container v-else class="workspace">
      <el-aside width="236px" class="sidebar">
        <div class="sidebar-brand">
          <div class="brand-mark small">化</div>
          <div>
            <strong>化学品管理</strong>
            <span>{{ roleLabel(user.role) }}</span>
          </div>
        </div>
        <el-menu :default-active="activeView" class="nav-menu" @select="activeView = $event">
          <el-menu-item index="dashboard">总览</el-menu-item>
          <el-menu-item index="chemicals">化学品台账</el-menu-item>
          <el-menu-item index="inventory">出入库管理</el-menu-item>
          <el-menu-item index="hazard">危化品管控</el-menu-item>
          <el-menu-item index="cards">人员与刷卡</el-menu-item>
          <el-menu-item index="ocr">OCR 与称重</el-menu-item>
          <el-menu-item index="approvals">审批中心</el-menu-item>
          <el-menu-item index="records">记录审计</el-menu-item>
        </el-menu>
      </el-aside>

      <el-container>
        <el-header class="topbar">
          <div>
            <h2>{{ viewTitle }}</h2>
            <span>{{ user.name }}，{{ user.department || '未设置部门' }}</span>
          </div>
          <div class="topbar-actions">
            <el-button :icon="Refresh" @click="refreshAll">刷新</el-button>
            <el-button :icon="SwitchButton" @click="logout">退出</el-button>
          </div>
        </el-header>

        <el-main class="main-content">
          <section v-show="activeView === 'dashboard'" class="view-grid">
            <div class="metric-grid">
              <div class="metric-card">
                <span>化学品总数</span>
                <strong>{{ summary.total_chemicals || 0 }}</strong>
              </div>
              <div class="metric-card warning">
                <span>危化品</span>
                <strong>{{ summary.hazardous_count || 0 }}</strong>
              </div>
              <div class="metric-card low">
                <span>低库存</span>
                <strong>{{ summary.low_stock_count || 0 }}</strong>
              </div>
              <div class="metric-card approval">
                <span>待审批</span>
                <strong>{{ summary.pending_approvals || 0 }}</strong>
              </div>
              <div class="metric-card done">
                <span>今日流水</span>
                <strong>{{ summary.today_transactions || 0 }}</strong>
              </div>
            </div>

            <el-card header="业务流程">
              <el-steps :active="4" align-center>
                <el-step title="人员注册" description="系统账号、人员档案、卡号绑定" />
                <el-step title="入库建档" description="化学品信息、危险等级、库存位置" />
                <el-step title="领用申请" description="刷卡核验、OCR确认、用量填写" />
                <el-step title="危化审批" description="危险品自动进入安全审批" />
                <el-step title="出库归还" description="库存扣减、称重记录、审计留痕" />
              </el-steps>
            </el-card>

            <el-card header="库存预警">
              <el-table :data="lowStockChemicals" height="280" border>
                <el-table-column prop="name" label="名称" />
                <el-table-column prop="stock" label="库存" width="90" />
                <el-table-column prop="min_stock" label="下限" width="90" />
                <el-table-column prop="location" label="位置" width="120" />
              </el-table>
            </el-card>
          </section>

          <section v-show="activeView === 'chemicals'" class="view-grid">
            <el-card>
              <template #header>
                <div class="card-header">
                  <span>化学品台账</span>
                  <div class="inline-actions">
                    <el-input v-model="chemicalKeyword" placeholder="搜索名称、CAS、位置" clearable @keyup.enter="fetchChemicals">
                      <template #append>
                        <el-button :icon="Search" @click="fetchChemicals" />
                      </template>
                    </el-input>
                    <el-button v-if="canManage" type="primary" :icon="Plus" @click="openChemicalDialog()">新增</el-button>
                  </div>
                </div>
              </template>
              <el-table :data="chemicals" border stripe>
                <el-table-column prop="code" label="编号" width="130" />
                <el-table-column prop="name" label="名称" min-width="130" />
                <el-table-column prop="cas_no" label="CAS" width="120" />
                <el-table-column prop="stock" label="库存" width="80" />
                <el-table-column prop="unit" label="单位" width="70" />
                <el-table-column prop="danger_level" label="危险等级" width="100" />
                <el-table-column prop="control_level" label="管控" width="100" />
                <el-table-column prop="location" label="位置" width="100" />
                <el-table-column label="状态" width="95">
                  <template #default="{ row }">
                    <el-tag :type="row.is_hazardous ? 'danger' : 'success'">
                      {{ row.is_hazardous ? '危化品' : '普通' }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column v-if="canManage" label="操作" width="150" fixed="right">
                  <template #default="{ row }">
                    <el-button size="small" :icon="Check" @click="openChemicalDialog(row)">编辑</el-button>
                    <el-button size="small" type="danger" :icon="Close" @click="disableChemical(row)">停用</el-button>
                  </template>
                </el-table-column>
              </el-table>
            </el-card>
          </section>

          <section v-show="activeView === 'inventory'" class="split-grid">
            <el-card header="入库">
              <el-form :model="inboundForm" label-position="top">
                <el-form-item label="化学品">
                  <el-select v-model="inboundForm.chemical_id" filterable class="full-width">
                    <el-option v-for="item in chemicals" :key="item.id" :label="`${item.name} (${item.stock}${item.unit})`" :value="item.id" />
                  </el-select>
                </el-form-item>
                <el-form-item label="数量">
                  <el-input-number v-model="inboundForm.quantity" :min="0" :precision="2" class="full-width" />
                </el-form-item>
                <el-form-item label="项目">
                  <el-input v-model="inboundForm.project_name" />
                </el-form-item>
                <el-form-item label="备注">
                  <el-input v-model="inboundForm.remark" type="textarea" />
                </el-form-item>
                <el-button type="primary" :icon="Plus" :disabled="!canManage" @click="submitInbound">确认入库</el-button>
              </el-form>
            </el-card>

            <el-card header="出库 / 领用">
              <el-form :model="outboundForm" label-position="top">
                <el-form-item label="刷卡卡号">
                  <el-input v-model="outboundForm.card_no" placeholder="刷卡后自动填入，或手动输入">
                    <template #append>
                      <el-button :icon="Check" @click="verifyOutboundCard">验卡</el-button>
                    </template>
                  </el-input>
                </el-form-item>
                <el-alert v-if="outboundPerson" :title="`领用人：${outboundPerson.person_name}`" type="success" show-icon :closable="false" />
                <el-form-item label="化学品">
                  <el-select v-model="outboundForm.chemical_id" filterable class="full-width">
                    <el-option v-for="item in chemicals" :key="item.id" :label="`${item.name} (${item.stock}${item.unit})`" :value="item.id" />
                  </el-select>
                </el-form-item>
                <el-alert v-if="selectedOutboundChemical?.is_hazardous" title="该化学品受危化品流程管控，普通用户提交后将进入审批。" type="warning" show-icon :closable="false" />
                <el-form-item label="数量">
                  <el-input-number v-model="outboundForm.quantity" :min="0" :precision="2" class="full-width" />
                </el-form-item>
                <el-form-item label="用途">
                  <el-input v-model="outboundForm.purpose" />
                </el-form-item>
                <el-form-item label="项目">
                  <el-input v-model="outboundForm.project_name" />
                </el-form-item>
                <el-button type="warning" :icon="Check" @click="submitOutbound">提交出库</el-button>
              </el-form>
            </el-card>

            <el-card header="归还 / 盘点调整">
              <el-tabs>
                <el-tab-pane label="归还">
                  <el-form :model="returnForm" label-position="top">
                    <el-form-item label="化学品">
                      <el-select v-model="returnForm.chemical_id" filterable class="full-width">
                        <el-option v-for="item in chemicals" :key="item.id" :label="item.name" :value="item.id" />
                      </el-select>
                    </el-form-item>
                    <el-form-item label="归还数量">
                      <el-input-number v-model="returnForm.quantity" :min="0" :precision="2" class="full-width" />
                    </el-form-item>
                    <el-button type="success" :icon="Check" @click="submitReturn">确认归还</el-button>
                  </el-form>
                </el-tab-pane>
                <el-tab-pane label="盘点调整">
                  <el-form :model="adjustForm" label-position="top">
                    <el-form-item label="化学品">
                      <el-select v-model="adjustForm.chemical_id" filterable class="full-width">
                        <el-option v-for="item in chemicals" :key="item.id" :label="item.name" :value="item.id" />
                      </el-select>
                    </el-form-item>
                    <el-form-item label="调整后库存">
                      <el-input-number v-model="adjustForm.quantity" :min="0" :precision="2" class="full-width" />
                    </el-form-item>
                    <el-button :disabled="!canManage" :icon="Check" @click="submitAdjust">确认调整</el-button>
                  </el-form>
                </el-tab-pane>
              </el-tabs>
            </el-card>

            <el-card class="wide-card" header="库存流水">
              <el-table :data="transactions" border stripe height="360">
                <el-table-column prop="transaction_no" label="流水号" width="170" />
                <el-table-column prop="transaction_type" label="类型" width="90" :formatter="typeFormatter" />
                <el-table-column prop="chemical_name" label="化学品" />
                <el-table-column prop="quantity" label="数量" width="90" />
                <el-table-column prop="before_stock" label="变更前" width="90" />
                <el-table-column prop="after_stock" label="变更后" width="90" />
                <el-table-column prop="applicant_name" label="申请人" width="110" />
                <el-table-column prop="created_at" label="时间" width="170" />
              </el-table>
            </el-card>
          </section>

          <section v-show="activeView === 'hazard'" class="view-grid">
            <el-alert title="危化品管控规则：危险等级大于等于 3、标记危化品或管控级别不是 normal 时，普通用户出库会自动生成审批单，审批通过后才扣减库存。" type="warning" show-icon :closable="false" />
            <el-card header="危化品清单">
              <el-table :data="hazardSummary.chemicals || []" border stripe>
                <el-table-column prop="name" label="名称" />
                <el-table-column prop="cas_no" label="CAS" width="130" />
                <el-table-column prop="hazard" label="危险性" />
                <el-table-column prop="danger_level" label="等级" width="80" />
                <el-table-column prop="control_level" label="管控级别" width="110" />
                <el-table-column prop="storage_requirement" label="储存要求" />
                <el-table-column prop="location" label="位置" width="100" />
              </el-table>
            </el-card>
          </section>

          <section v-show="activeView === 'cards'" class="split-grid">
            <el-card header="人员注册">
              <el-form :model="personForm" label-position="top">
                <el-form-item label="姓名">
                  <el-input v-model="personForm.name" />
                </el-form-item>
                <el-form-item label="工号">
                  <el-input v-model="personForm.employee_no" />
                </el-form-item>
                <el-form-item label="部门">
                  <el-input v-model="personForm.department" />
                </el-form-item>
                <el-button type="primary" :icon="Plus" :disabled="!canManage" @click="submitPerson">保存人员</el-button>
              </el-form>
            </el-card>

            <el-card header="卡片注册">
              <el-form :model="cardForm" label-position="top">
                <el-form-item label="卡号">
                  <el-input v-model="cardForm.card_no" />
                </el-form-item>
                <el-form-item label="绑定已有人员">
                  <el-select v-model="cardForm.person_id" clearable filterable class="full-width">
                    <el-option v-for="item in people" :key="item.id" :label="`${item.name} ${item.employee_no || ''}`" :value="item.id" />
                  </el-select>
                </el-form-item>
                <el-form-item label="或创建新人员">
                  <el-input v-model="cardForm.newPersonName" placeholder="留空则使用上方人员" />
                </el-form-item>
                <el-button type="success" :icon="Check" :disabled="!canManage" @click="submitCard">注册卡片</el-button>
              </el-form>
            </el-card>

            <el-card header="刷卡校验">
              <el-input v-model="cardVerifyNo" placeholder="输入卡号">
                <template #append>
                  <el-button :icon="Check" @click="submitCardVerify">验卡</el-button>
                </template>
              </el-input>
              <el-result v-if="cardResult" :icon="cardResult.valid ? 'success' : 'warning'" :title="cardResult.valid ? '卡片有效' : '卡片不可用'" :sub-title="cardResult.valid ? cardResult.card.person_name : cardResult.reason" />
            </el-card>

            <el-card class="wide-card" header="人员与卡片">
              <el-table :data="cards" border stripe height="340">
                <el-table-column prop="card_no" label="卡号" width="150" />
                <el-table-column prop="person_name" label="姓名" />
                <el-table-column prop="employee_no" label="工号" width="120" />
                <el-table-column prop="department" label="部门" />
                <el-table-column prop="status" label="状态" width="90" />
                <el-table-column prop="last_seen_at" label="最近刷卡" width="170" />
              </el-table>
            </el-card>
          </section>

          <section v-show="activeView === 'ocr'" class="split-grid">
            <el-card header="瓶身 OCR 识别">
              <div class="upload-box">
                <input type="file" accept="image/*" @change="handleOcrFile" />
                <el-button :icon="Upload">选择瓶身照片</el-button>
              </div>
              <img v-if="ocrPreview" :src="ocrPreview" class="ocr-preview" alt="瓶身照片预览" />
              <el-descriptions v-if="ocrResult" :column="1" border>
                <el-descriptions-item label="识别名称">{{ ocrResult.name || '未识别' }}</el-descriptions-item>
                <el-descriptions-item label="置信度">{{ ocrResult.confidence }}</el-descriptions-item>
                <el-descriptions-item label="规格">{{ ocrResult.specification }}</el-descriptions-item>
                <el-descriptions-item label="危险性">{{ ocrResult.hazard }}</el-descriptions-item>
                <el-descriptions-item label="原始文本">{{ ocrResult.raw_text || ocrResult.extra }}</el-descriptions-item>
              </el-descriptions>
              <el-button v-if="ocrResult?.name" type="primary" :icon="Plus" :disabled="!canManage" @click="createChemicalFromOcr">保存为化学品</el-button>
            </el-card>

            <el-card header="称重与使用记录">
              <el-form :model="usageForm" label-position="top">
                <el-form-item label="化学品">
                  <el-select v-model="usageForm.chemical_id" filterable class="full-width">
                    <el-option v-for="item in chemicals" :key="item.id" :label="item.name" :value="item.id" />
                  </el-select>
                </el-form-item>
                <el-form-item label="卡号">
                  <el-input v-model="usageForm.card_no" />
                </el-form-item>
                <el-form-item label="使用前重量(g)">
                  <el-input-number v-model="usageForm.before_weight" :precision="2" class="full-width" />
                </el-form-item>
                <el-form-item label="使用后重量(g)">
                  <el-input-number v-model="usageForm.after_weight" :precision="2" class="full-width" />
                </el-form-item>
                <el-form-item label="当前天平读数">
                  <div class="weight-row">
                    <strong>{{ currentWeight === null ? '--' : `${currentWeight} g` }}</strong>
                    <el-button :icon="Refresh" @click="readScale">读取天平</el-button>
                  </div>
                </el-form-item>
                <el-alert v-if="usageAmount !== null" :title="`计算用量：${usageAmount.toFixed(2)} g`" type="info" show-icon :closable="false" />
                <el-button type="primary" :icon="Check" @click="submitUsageRecord">保存使用记录</el-button>
              </el-form>
            </el-card>
          </section>

          <section v-show="activeView === 'approvals'" class="view-grid">
            <el-card header="审批中心">
              <el-table :data="approvals" border stripe>
                <el-table-column prop="request_no" label="审批号" width="170" />
                <el-table-column prop="chemical_name" label="化学品" />
                <el-table-column prop="quantity" label="数量" width="90" />
                <el-table-column prop="applicant_name" label="申请人" width="110" />
                <el-table-column prop="purpose" label="用途" />
                <el-table-column prop="status" label="状态" width="100" />
                <el-table-column label="操作" width="190" fixed="right">
                  <template #default="{ row }">
                    <el-button size="small" type="success" :icon="Check" :disabled="!canReview || row.status !== 'pending'" @click="review(row, true)">通过</el-button>
                    <el-button size="small" type="danger" :icon="Close" :disabled="!canReview || row.status !== 'pending'" @click="review(row, false)">驳回</el-button>
                  </template>
                </el-table-column>
              </el-table>
            </el-card>
          </section>

          <section v-show="activeView === 'records'" class="view-grid">
            <el-card header="使用记录">
              <el-table :data="usageRecords" border stripe height="280">
                <el-table-column prop="timestamp" label="时间" width="170" />
                <el-table-column prop="person_name" label="人员" width="120" />
                <el-table-column prop="card_no" label="卡号" width="130" />
                <el-table-column prop="chemical_name" label="化学品" />
                <el-table-column prop="before_weight" label="前重(g)" width="100" />
                <el-table-column prop="after_weight" label="后重(g)" width="100" />
                <el-table-column prop="usage_weight" label="用量(g)" width="100" />
              </el-table>
            </el-card>
            <el-card v-if="canReview" header="审计日志">
              <el-table :data="auditLogs" border stripe height="280">
                <el-table-column prop="created_at" label="时间" width="170" />
                <el-table-column prop="action" label="动作" width="150" />
                <el-table-column prop="actor_name" label="操作人" width="120" />
                <el-table-column prop="target_type" label="对象" width="100" />
                <el-table-column prop="detail" label="详情" />
              </el-table>
            </el-card>
          </section>
        </el-main>
      </el-container>
    </el-container>

    <el-dialog v-model="chemicalDialogVisible" :title="chemicalForm.id ? '编辑化学品' : '新增化学品'" width="760px">
      <el-form :model="chemicalForm" label-width="110px" class="chemical-form">
        <el-form-item label="编号"><el-input v-model="chemicalForm.code" /></el-form-item>
        <el-form-item label="名称"><el-input v-model="chemicalForm.name" /></el-form-item>
        <el-form-item label="别名"><el-input v-model="chemicalForm.alias" /></el-form-item>
        <el-form-item label="CAS"><el-input v-model="chemicalForm.cas_no" /></el-form-item>
        <el-form-item label="分类"><el-input v-model="chemicalForm.category" /></el-form-item>
        <el-form-item label="规格"><el-input v-model="chemicalForm.specification" /></el-form-item>
        <el-form-item label="库存"><el-input-number v-model="chemicalForm.stock" :precision="2" class="full-width" /></el-form-item>
        <el-form-item label="单位"><el-input v-model="chemicalForm.unit" /></el-form-item>
        <el-form-item label="库存下限"><el-input-number v-model="chemicalForm.min_stock" :precision="2" class="full-width" /></el-form-item>
        <el-form-item label="危险性"><el-input v-model="chemicalForm.hazard" /></el-form-item>
        <el-form-item label="危险等级"><el-input-number v-model="chemicalForm.danger_level" :min="1" :max="5" class="full-width" /></el-form-item>
        <el-form-item label="危化品"><el-switch v-model="chemicalForm.is_hazardous" :active-value="1" :inactive-value="0" /></el-form-item>
        <el-form-item label="管控级别">
          <el-select v-model="chemicalForm.control_level" class="full-width">
            <el-option label="普通" value="normal" />
            <el-option label="需审批" value="approval" />
            <el-option label="严格管控" value="strict" />
            <el-option label="特殊管控" value="special" />
          </el-select>
        </el-form-item>
        <el-form-item label="存放位置"><el-input v-model="chemicalForm.location" /></el-form-item>
        <el-form-item label="储存要求"><el-input v-model="chemicalForm.storage_requirement" type="textarea" /></el-form-item>
        <el-form-item label="所属项目"><el-input v-model="chemicalForm.project_name" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="chemicalDialogVisible = false">取消</el-button>
        <el-button type="primary" :icon="Check" @click="submitChemical">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Check, Close, Lock, Plus, Refresh, Search, SwitchButton, Upload, User } from '@element-plus/icons-vue'
import {
  authLogin,
  authLogout,
  authMe,
  authRegister,
  createChemical,
  createPerson,
  deleteChemical,
  getApprovals,
  getAuditLogs,
  getCardPorts,
  getCards,
  getChemicalList,
  getCurrentWeight,
  getDashboardSummary,
  getHazardSummary,
  getInventoryTransactions,
  getPeople,
  getUsageRecords,
  inventoryAdjust,
  inventoryInbound,
  inventoryOutbound,
  inventoryReturn,
  ocrChemical,
  registerCard,
  reviewApproval,
  saveUsageRecord,
  setAuthToken,
  updateChemical,
  verifyCard,
} from './api'

const authMode = ref('login')
const authLoading = ref(false)
const user = ref(null)
const activeView = ref('dashboard')

const loginForm = reactive({ username: 'admin', password: 'admin123' })
const registerForm = reactive({ username: '', password: '', name: '', role: 'operator', department: '', phone: '' })

const summary = ref({})
const hazardSummary = ref({})
const chemicals = ref([])
const people = ref([])
const cards = ref([])
const transactions = ref([])
const approvals = ref([])
const usageRecords = ref([])
const auditLogs = ref([])
const ports = ref([])

const chemicalKeyword = ref('')
const chemicalDialogVisible = ref(false)
const chemicalForm = reactive(blankChemical())

const inboundForm = reactive({ chemical_id: null, quantity: 1, project_name: '', purpose: '采购入库', remark: '' })
const outboundForm = reactive({ card_no: '', chemical_id: null, quantity: 1, purpose: '', project_name: '', reason: '' })
const returnForm = reactive({ card_no: '', chemical_id: null, quantity: 1, project_name: '' })
const adjustForm = reactive({ chemical_id: null, quantity: 0, project_name: '', remark: '' })
const outboundPerson = ref(null)

const personForm = reactive({ name: '', employee_no: '', department: '', phone: '', role: 'operator' })
const cardForm = reactive({ card_no: '', person_id: null, newPersonName: '', card_type: 'ic', remark: '' })
const cardVerifyNo = ref('')
const cardResult = ref(null)

const ocrPreview = ref('')
const ocrResult = ref(null)
const currentWeight = ref(null)
const usageForm = reactive({ chemical_id: null, card_no: '', before_weight: 0, after_weight: 0 })

const canManage = computed(() => ['admin', 'keeper', 'safety_manager'].includes(user.value?.role))
const canReview = computed(() => ['admin', 'safety_manager'].includes(user.value?.role))
const selectedOutboundChemical = computed(() => chemicals.value.find((item) => item.id === outboundForm.chemical_id))
const usageAmount = computed(() => {
  if (usageForm.before_weight === null || usageForm.after_weight === null) return null
  return Number(usageForm.before_weight || 0) - Number(usageForm.after_weight || 0)
})
const lowStockChemicals = computed(() => chemicals.value.filter((item) => Number(item.stock || 0) <= Number(item.min_stock || 0)))
const viewTitle = computed(() => ({
  dashboard: '系统总览',
  chemicals: '化学品台账',
  inventory: '出入库管理',
  hazard: '危化品管控',
  cards: '人员与刷卡',
  ocr: 'OCR 与称重',
  approvals: '审批中心',
  records: '记录审计',
}[activeView.value] || '工作台'))

function blankChemical() {
  return {
    id: null,
    code: '',
    name: '',
    alias: '',
    cas_no: '',
    category: '',
    specification: '',
    stock: 0,
    unit: '瓶',
    min_stock: 0,
    max_stock: '',
    hazard: '',
    hazard_class: '',
    danger_level: 1,
    is_hazardous: 0,
    control_level: 'normal',
    storage_requirement: '',
    location: '',
    manufacturer: '',
    project_name: '',
    owner: '',
    status: 'active',
  }
}

function assign(target, source) {
  Object.assign(target, source)
}

function roleLabel(role) {
  return { admin: '系统管理员', keeper: '库管员', safety_manager: '安全管理员', operator: '普通使用人' }[role] || role
}

function typeFormatter(row) {
  return { inbound: '入库', outbound: '出库', return: '归还', adjust: '调整' }[row.transaction_type] || row.transaction_type
}

function notifyError(error, fallback) {
  ElMessage.error(error?.response?.data?.error || fallback)
}

async function login() {
  authLoading.value = true
  try {
    const res = await authLogin(loginForm)
    setAuthToken(res.data.token)
    user.value = res.data.user
    await refreshAll()
    ElMessage.success('登录成功')
  } catch (error) {
    notifyError(error, '登录失败')
  } finally {
    authLoading.value = false
  }
}

async function register() {
  authLoading.value = true
  try {
    const res = await authRegister(registerForm)
    setAuthToken(res.data.token)
    user.value = res.data.user
    await refreshAll()
    ElMessage.success('注册成功')
  } catch (error) {
    notifyError(error, '注册失败')
  } finally {
    authLoading.value = false
  }
}

async function logout() {
  try {
    await authLogout()
  } catch {
    // Ignore expired sessions.
  }
  setAuthToken('')
  user.value = null
}

async function bootstrap() {
  if (!localStorage.getItem('chemical_token')) return
  try {
    const res = await authMe()
    user.value = res.data
    await refreshAll()
  } catch {
    setAuthToken('')
  }
}

async function refreshAll() {
  await Promise.allSettled([
    fetchDashboard(),
    fetchChemicals(),
    fetchPeople(),
    fetchCards(),
    fetchTransactions(),
    fetchApprovals(),
    fetchHazard(),
    fetchRecords(),
    fetchAuditLogs(),
    fetchPorts(),
  ])
}

async function fetchDashboard() {
  summary.value = (await getDashboardSummary()).data
}

async function fetchChemicals() {
  chemicals.value = (await getChemicalList({ keyword: chemicalKeyword.value })).data
}

async function fetchPeople() {
  people.value = (await getPeople()).data
}

async function fetchCards() {
  cards.value = (await getCards()).data
}

async function fetchTransactions() {
  transactions.value = (await getInventoryTransactions({ limit: 200 })).data
}

async function fetchApprovals() {
  approvals.value = (await getApprovals()).data
}

async function fetchHazard() {
  hazardSummary.value = (await getHazardSummary()).data
}

async function fetchRecords() {
  usageRecords.value = (await getUsageRecords(100)).data
}

async function fetchAuditLogs() {
  if (!canReview.value) return
  auditLogs.value = (await getAuditLogs()).data
}

async function fetchPorts() {
  try {
    ports.value = (await getCardPorts()).data
  } catch {
    ports.value = []
  }
}

function openChemicalDialog(row) {
  assign(chemicalForm, blankChemical())
  if (row) assign(chemicalForm, { ...row, max_stock: row.max_stock ?? '' })
  chemicalDialogVisible.value = true
}

async function submitChemical() {
  try {
    if (chemicalForm.id) await updateChemical(chemicalForm.id, chemicalForm)
    else await createChemical(chemicalForm)
    chemicalDialogVisible.value = false
    await refreshAll()
    ElMessage.success('化学品已保存')
  } catch (error) {
    notifyError(error, '保存失败')
  }
}

async function disableChemical(row) {
  try {
    await ElMessageBox.confirm(`确认停用 ${row.name}？`, '停用化学品', { type: 'warning' })
    await deleteChemical(row.id)
    await refreshAll()
    ElMessage.success('已停用')
  } catch (error) {
    if (error !== 'cancel') notifyError(error, '停用失败')
  }
}

async function submitInbound() {
  try {
    await inventoryInbound(inboundForm)
    await refreshAll()
    ElMessage.success('入库完成')
  } catch (error) {
    notifyError(error, '入库失败')
  }
}

async function verifyOutboundCard() {
  try {
    const res = await verifyCard(outboundForm.card_no)
    if (!res.data.valid) {
      outboundPerson.value = null
      ElMessage.warning(res.data.reason || '卡片不可用')
      return
    }
    outboundPerson.value = res.data.card
    ElMessage.success(`卡片有效：${res.data.card.person_name}`)
  } catch (error) {
    notifyError(error, '验卡失败')
  }
}

async function submitOutbound() {
  try {
    const res = await inventoryOutbound(outboundForm)
    await refreshAll()
    if (res.data.approval_required) {
      ElMessage.warning(`已生成审批单：${res.data.approval.request_no}`)
    } else {
      ElMessage.success('出库完成')
    }
  } catch (error) {
    notifyError(error, '出库失败')
  }
}

async function submitReturn() {
  try {
    await inventoryReturn(returnForm)
    await refreshAll()
    ElMessage.success('归还完成')
  } catch (error) {
    notifyError(error, '归还失败')
  }
}

async function submitAdjust() {
  try {
    await inventoryAdjust(adjustForm)
    await refreshAll()
    ElMessage.success('库存已调整')
  } catch (error) {
    notifyError(error, '调整失败')
  }
}

async function submitPerson() {
  try {
    await createPerson(personForm)
    assign(personForm, { name: '', employee_no: '', department: '', phone: '', role: 'operator' })
    await refreshAll()
    ElMessage.success('人员已保存')
  } catch (error) {
    notifyError(error, '保存人员失败')
  }
}

async function submitCard() {
  const payload = {
    card_no: cardForm.card_no,
    person_id: cardForm.person_id,
    card_type: cardForm.card_type,
    remark: cardForm.remark,
  }
  if (cardForm.newPersonName) {
    payload.person = { name: cardForm.newPersonName, role: 'operator' }
    payload.person_id = null
  }
  try {
    await registerCard(payload)
    assign(cardForm, { card_no: '', person_id: null, newPersonName: '', card_type: 'ic', remark: '' })
    await refreshAll()
    ElMessage.success('卡片已注册')
  } catch (error) {
    notifyError(error, '注册卡片失败')
  }
}

async function submitCardVerify() {
  try {
    cardResult.value = (await verifyCard(cardVerifyNo.value)).data
  } catch (error) {
    notifyError(error, '验卡失败')
  }
}

async function handleOcrFile(event) {
  const file = event.target.files?.[0]
  if (!file) return
  ocrPreview.value = URL.createObjectURL(file)
  try {
    const res = await ocrChemical(file)
    ocrResult.value = res.data
    ElMessage.success('OCR 识别完成')
  } catch (error) {
    notifyError(error, 'OCR 识别失败')
  } finally {
    event.target.value = ''
  }
}

async function createChemicalFromOcr() {
  if (!ocrResult.value?.name) return
  try {
    await createChemical({
      name: ocrResult.value.name,
      alias: ocrResult.value.matched_token,
      cas_no: ocrResult.value.cas_no,
      specification: ocrResult.value.specification,
      hazard: ocrResult.value.hazard,
      ocr_text: ocrResult.value.raw_text || ocrResult.value.extra,
      stock: 0,
      unit: '瓶',
      danger_level: ocrResult.value.hazard ? 3 : 1,
      is_hazardous: ocrResult.value.hazard ? 1 : 0,
      control_level: ocrResult.value.hazard ? 'approval' : 'normal',
    })
    await refreshAll()
    ElMessage.success('已加入化学品台账')
  } catch (error) {
    notifyError(error, '保存 OCR 化学品失败')
  }
}

async function readScale() {
  try {
    const res = await getCurrentWeight()
    currentWeight.value = res.data.weight
    ElMessage.success('已读取天平')
  } catch (error) {
    notifyError(error, '读取天平失败')
  }
}

async function submitUsageRecord() {
  const chemical = chemicals.value.find((item) => item.id === usageForm.chemical_id)
  try {
    await saveUsageRecord({
      chemical,
      card_no: usageForm.card_no,
      before_weight: usageForm.before_weight,
      after_weight: usageForm.after_weight,
      usage_weight: usageAmount.value,
      ocr_text: ocrResult.value?.raw_text,
    })
    await fetchRecords()
    ElMessage.success('使用记录已保存')
  } catch (error) {
    notifyError(error, '保存使用记录失败')
  }
}

async function review(row, approved) {
  try {
    await reviewApproval(row.id, { approved, review_note: approved ? '同意领用' : '不符合领用要求' })
    await refreshAll()
    ElMessage.success(approved ? '已通过审批' : '已驳回审批')
  } catch (error) {
    notifyError(error, '审批失败')
  }
}

onMounted(bootstrap)
</script>

<style>
* {
  box-sizing: border-box;
}

body {
  margin: 0;
  background: #f4f6f8;
  color: #1f2933;
  font-family: Inter, "Microsoft YaHei", "PingFang SC", Arial, sans-serif;
}

.app-shell {
  min-height: 100vh;
}

.auth-screen {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 24px;
  background:
    linear-gradient(135deg, rgba(20, 105, 88, 0.16), rgba(63, 88, 130, 0.08)),
    #eef3f1;
}

.auth-panel {
  width: min(460px, 100%);
  padding: 28px;
  background: #ffffff;
  border: 1px solid #d9e1e6;
  border-radius: 8px;
  box-shadow: 0 18px 48px rgba(31, 41, 51, 0.12);
}

.brand,
.sidebar-brand,
.topbar,
.card-header,
.inline-actions,
.topbar-actions,
.weight-row {
  display: flex;
  align-items: center;
}

.brand {
  gap: 14px;
  margin-bottom: 24px;
}

.brand h1 {
  margin: 0 0 6px;
  font-size: 24px;
  letter-spacing: 0;
}

.brand p {
  margin: 0;
  color: #60707c;
  line-height: 1.5;
}

.brand-mark {
  width: 52px;
  height: 52px;
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  border-radius: 8px;
  background: #14795f;
  color: #fff;
  font-size: 26px;
  font-weight: 700;
}

.brand-mark.small {
  width: 38px;
  height: 38px;
  font-size: 20px;
}

.wide-button,
.full-width {
  width: 100%;
}

.workspace {
  min-height: 100vh;
}

.sidebar {
  background: #263238;
  color: #fff;
  border-right: 1px solid #172126;
}

.sidebar-brand {
  gap: 12px;
  height: 72px;
  padding: 16px;
}

.sidebar-brand strong,
.sidebar-brand span {
  display: block;
}

.sidebar-brand span {
  margin-top: 4px;
  color: #b7c5ca;
  font-size: 12px;
}

.nav-menu {
  border-right: none;
  background: transparent;
}

.nav-menu .el-menu-item {
  color: #dbe6ea;
}

.nav-menu .el-menu-item.is-active {
  color: #ffffff;
  background: #14795f;
}

.topbar {
  height: 72px;
  justify-content: space-between;
  padding: 0 24px;
  background: #ffffff;
  border-bottom: 1px solid #dde5ea;
}

.topbar h2 {
  margin: 0;
  font-size: 20px;
  letter-spacing: 0;
}

.topbar span {
  display: block;
  margin-top: 4px;
  color: #667784;
  font-size: 13px;
}

.topbar-actions {
  gap: 10px;
}

.main-content {
  padding: 20px;
}

.view-grid {
  display: grid;
  gap: 16px;
}

.split-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(240px, 1fr));
  gap: 16px;
  align-items: start;
}

.wide-card {
  grid-column: 1 / -1;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(140px, 1fr));
  gap: 14px;
}

.metric-card {
  padding: 18px;
  background: #ffffff;
  border: 1px solid #dce5e8;
  border-left: 4px solid #14795f;
  border-radius: 8px;
}

.metric-card span {
  display: block;
  color: #667784;
  font-size: 13px;
}

.metric-card strong {
  display: block;
  margin-top: 8px;
  font-size: 30px;
}

.metric-card.warning {
  border-left-color: #c2410c;
}

.metric-card.low {
  border-left-color: #b45309;
}

.metric-card.approval {
  border-left-color: #6d5bd0;
}

.metric-card.done {
  border-left-color: #2563eb;
}

.card-header {
  justify-content: space-between;
  gap: 16px;
}

.inline-actions {
  gap: 10px;
}

.inline-actions .el-input {
  width: 280px;
}

.chemical-form {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 2px 12px;
}

.chemical-form .el-form-item:last-child {
  grid-column: 1 / -1;
}

.upload-box {
  position: relative;
  display: inline-block;
  margin-bottom: 14px;
}

.upload-box input {
  position: absolute;
  inset: 0;
  opacity: 0;
  cursor: pointer;
}

.ocr-preview {
  width: 100%;
  max-height: 260px;
  object-fit: contain;
  margin: 10px 0 16px;
  border: 1px solid #dce5e8;
  border-radius: 8px;
  background: #f7faf9;
}

.weight-row {
  justify-content: space-between;
  width: 100%;
  gap: 12px;
}

.el-card {
  border-radius: 8px;
}

@media (max-width: 1100px) {
  .split-grid,
  .metric-grid {
    grid-template-columns: repeat(2, minmax(220px, 1fr));
  }

  .chemical-form {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .workspace {
    display: block;
  }

  .sidebar {
    width: 100% !important;
  }

  .topbar,
  .card-header {
    align-items: flex-start;
    flex-direction: column;
    height: auto;
    padding: 16px;
  }

  .split-grid,
  .metric-grid {
    grid-template-columns: 1fr;
  }

  .inline-actions {
    width: 100%;
    flex-direction: column;
    align-items: stretch;
  }

  .inline-actions .el-input {
    width: 100%;
  }
}
</style>
