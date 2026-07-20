/**
 * 自动领用对接模块
 * 整合卡片读取、摄像头拍照、OCR识别、重量读取等硬件模块
 * 自动完成领用流程
 */
import request from './index'

/**
 * 执行自动领用流程
 * 从串口读取卡片、摄像头拍照、OCR识别、读取重量
 * 返回所有领用信息供前端确认
 *
 * @param {Object} config - 配置参数
 * @param {string} config.card_port - 读卡器串口号，默认COM3
 * @param {string} config.weight_port - 天平串口号，默认COM4
 * @param {number} config.camera_id - 摄像头ID，默认0
 * @param {number} config.card_baudrate - 读卡器波特率，默认9600
 * @param {number} config.weight_baudrate - 天平波特率，默认9600
 * @param {number} config.timeout - 超时时间(秒)，默认10
 * @returns {Promise} 包含所有领用信息的Promise
 */
export function autoOutbound(config = {}) {
  return request.post('/auto/outbound', {
    card_port: config.card_port || 'COM3',
    weight_port: config.weight_port || 'COM4',
    camera_id: config.camera_id || 0,
    card_baudrate: config.card_baudrate || 9600,
    weight_baudrate: config.weight_baudrate || 9600,
    timeout: config.timeout || 10
  })
}

/**
 * 确认自动领用并写入数据库
 *
 * @param {Object} autoResult - autoOutbound返回的结果
 * @param {number} quantity - 领用数量(可选，默认使用重量数据)
 * @param {string} purpose - 用途
 * @param {string} projectName - 项目名称
 * @returns {Promise} 包含transaction信息的Promise
 */
export function confirmAutoOutbound(autoResult, quantity = null, purpose = '', projectName = '') {
  return request.post('/auto/outbound/confirm', {
    auto_result: autoResult,
    quantity: quantity,
    purpose: purpose,
    project_name: projectName
  })
}

/**
 * 完整的自动领用流程(带确认)
 * 自动执行整个流程，包括确认和写入数据库
 *
 * @param {Object} config - 配置参数
 * @param {number} quantity - 领用数量(可选)
 * @param {string} purpose - 用途
 * @param {string} projectName - 项目名称
 * @returns {Promise} 包含transaction信息的Promise
 */
export async function fullAutoOutbound(config = {}, quantity = null, purpose = '', projectName = '') {
  // 执行自动领用流程
  const autoResult = await autoOutbound(config)

  if (!autoResult.data.success) {
    throw new Error(autoResult.data.error || '自动领用流程失败')
  }

  // 确认并写入数据库
  const confirmResult = await confirmAutoOutbound(
    autoResult.data,
    quantity,
    purpose,
    projectName
  )

  return confirmResult.data
}

export default {
  autoOutbound,
  confirmAutoOutbound,
  fullAutoOutbound
}