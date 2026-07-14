<template>
  <div class="camera-container">
    <video ref="videoRef" autoplay playsinline></video>
    <div class="controls">
      <el-button type="primary" @click="capture">拍照</el-button>
      <el-button @click="switchCamera" v-if="hasMultipleCameras">切换摄像头</el-button>
    </div>
    <canvas ref="canvasRef" style="display: none;"></canvas>
    <div v-if="capturedImage" class="preview">
      <img :src="capturedImage" alt="预览" />
      <el-button type="success" size="small" @click="confirm">使用此照片</el-button>
      <el-button size="small" @click="clear">重新拍摄</el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'

const emit = defineEmits(['captured'])

const videoRef = ref(null)
const canvasRef = ref(null)
let stream = null
let currentDeviceId = ''
const hasMultipleCameras = ref(false)
const capturedImage = ref(null)
let capturedFile = null

async function getCameras() {
  const devices = await navigator.mediaDevices.enumerateDevices()
  const videoInputs = devices.filter(device => device.kind === 'videoinput')
  hasMultipleCameras.value = videoInputs.length > 1
  return videoInputs
}

async function startCamera(deviceId = null) {
  if (stream) {
    stream.getTracks().forEach(track => track.stop())
  }
  const constraints = {
    video: deviceId ? { deviceId: { exact: deviceId } } : true
  }
  try {
    stream = await navigator.mediaDevices.getUserMedia(constraints)
    videoRef.value.srcObject = stream
    await videoRef.value.play()
  } catch (err) {
    ElMessage.error('无法访问摄像头：' + err.message)
  }
}

function capture() {
  const video = videoRef.value
  const canvas = canvasRef.value
  canvas.width = video.videoWidth
  canvas.height = video.videoHeight
  const ctx = canvas.getContext('2d')
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height)
  canvas.toBlob(blob => {
    capturedFile = new File([blob], `photo_${Date.now()}.jpg`, { type: 'image/jpeg' })
    capturedImage.value = URL.createObjectURL(blob)
  }, 'image/jpeg', 0.9)
}

function clear() {
  capturedImage.value = null
  capturedFile = null
}

function confirm() {
  if (capturedFile) {
    emit('captured', capturedFile)
    clear()
  }
}

async function switchCamera() {
  const cameras = await getCameras()
  if (cameras.length <= 1) return
  const nextDevice = cameras.find(device => device.deviceId !== currentDeviceId) || cameras[0]
  currentDeviceId = nextDevice.deviceId
  startCamera(currentDeviceId)
}

onMounted(async () => {
  const cameras = await getCameras()
  if (cameras.length) {
    currentDeviceId = cameras[0].deviceId
    startCamera(currentDeviceId)
  }
})

onUnmounted(() => {
  if (stream) {
    stream.getTracks().forEach(track => track.stop())
  }
})
</script>

<style scoped>
.camera-container video {
  width: 100%;
  max-width: 500px;
  border-radius: 8px;
  background: #000;
}
.controls { margin-top: 12px; }
.preview { margin-top: 16px; }
.preview img { max-width: 200px; border-radius: 8px; margin-right: 12px; }
</style>