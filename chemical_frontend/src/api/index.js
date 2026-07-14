import axios from 'axios'

const request = axios.create({
  baseURL: 'http://localhost:8000/api',
  timeout: 20000,
})

request.interceptors.request.use((config) => {
  const token = localStorage.getItem('chemical_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export const setAuthToken = (token) => {
  if (token) localStorage.setItem('chemical_token', token)
  else localStorage.removeItem('chemical_token')
}

export const authLogin = (data) => request.post('/auth/login', data)
export const authRegister = (data) => request.post('/auth/register', data)
export const authLogout = () => request.post('/auth/logout')
export const authMe = () => request.get('/auth/me')

export const getDashboardSummary = () => request.get('/dashboard/summary')

export const ocrChemical = (imageFile) => {
  const formData = new FormData()
  formData.append('image', imageFile)
  return request.post('/ocr/chemical', formData)
}

export const getChemicalList = (params = {}) => request.get('/chemicals', { params })
export const createChemical = (data) => request.post('/chemicals', data)
export const updateChemical = (id, data) => request.put(`/chemicals/${id}`, data)
export const deleteChemical = (id) => request.delete(`/chemicals/${id}`)
export const exportChemicalList = (params = {}) => request.get('/chemicals/export', { params, responseType: 'blob' })

export const getPeople = (keyword = '') => request.get('/people', { params: { keyword } })
export const createPerson = (data) => request.post('/people', data)

export const getCardPorts = () => request.get('/card/ports')
export const readCard = (data) => request.post('/card/read', data)
export const verifyCard = (card_no) => request.post('/card/verify', { card_no })
export const registerCard = (data) => request.post('/card/register', data)
export const getCards = (keyword = '') => request.get('/card/cards', { params: { keyword } })

export const getCurrentWeight = (params = {}) => request.get('/weight/current', { params })

export const inventoryInbound = (data) => request.post('/inventory/inbound', data)
export const inventoryOutbound = (data) => request.post('/inventory/outbound', data)
export const inventoryReturn = (data) => request.post('/inventory/return', data)
export const inventoryAdjust = (data) => request.post('/inventory/adjust', data)
export const getInventoryTransactions = (params = {}) => request.get('/inventory/transactions', { params })

export const getApprovals = (params = {}) => request.get('/approvals', { params })
export const reviewApproval = (id, data) => request.post(`/approvals/${id}/review`, data)

export const getHazardSummary = () => request.get('/hazard/summary')
export const getAuditLogs = (limit = 200) => request.get('/audit/logs', { params: { limit } })
export const saveUsageRecord = (data) => request.post('/record/usage', data)
export const getUsageRecords = (limit = 100) => request.get('/records', { params: { limit } })

export default request
