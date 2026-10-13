<template>
  <div class="tools" :class="{ embedded }">
    <div class="head" v-if="!embedded">
      <h3>{{ t('rembg.title') }}</h3>
      <p>{{ t('rembg.subtitle') }}</p>
    </div>
    <p v-else class="tip">{{ t('rembg.subtitle') }}</p>

    <div class="controls">
      <el-select v-model="model" style="width: 280px">
        <el-option v-for="m in models" :key="m.id" :label="m.label" :value="m.id" />
      </el-select>
      <el-checkbox v-model="alphaMatting">{{ t('rembg.alphaMatting') }}</el-checkbox>
      <el-upload
        :show-file-list="false"
        :auto-upload="false"
        accept="image/png,image/jpeg,image/webp,image/bmp"
        :on-change="onPick"
      >
        <el-button type="primary">{{ t('rembg.pick') }}</el-button>
      </el-upload>
      <el-button :disabled="!file || loading" :loading="loading" @click="run">
        {{ loading ? t('rembg.running') : t('rembg.run') }}
      </el-button>
      <el-button v-if="outUrl" @click="download">{{ t('rembg.download') }}</el-button>
    </div>

    <div class="preview">
      <div class="pane">
        <div class="pane-label">{{ t('rembg.before') }}</div>
        <div class="frame">
          <img v-if="inUrl" :src="inUrl" alt="before" />
          <span v-else class="placeholder">{{ t('rembg.emptyIn') }}</span>
        </div>
      </div>
      <div class="pane">
        <div class="pane-label">{{ t('rembg.after') }}</div>
        <div class="frame checker">
          <img v-if="outUrl" :src="outUrl" alt="after" />
          <span v-else class="placeholder">{{ t('rembg.emptyOut') }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import type { UploadFile } from 'element-plus'
import { api } from '../api'

defineProps<{ embedded?: boolean }>()

const { t } = useI18n()
const models = ref<{ id: string; label: string }[]>([])
const model = ref('u2netp')
// Alpha matting is very CPU-heavy; keep off by default.
const alphaMatting = ref(false)
const file = ref<File | null>(null)
const inUrl = ref('')
const outUrl = ref('')
const loading = ref(false)

onMounted(async () => {
  try {
    const data = await api.listRembgModels()
    models.value = data.models || []
    if (data.default) model.value = data.default
  } catch {
    models.value = [
      { id: 'u2netp', label: 'u2netp (fast / light)' },
      { id: 'isnet-anime', label: 'isnet-anime (anime / Q characters)' },
    ]
  }
})

onBeforeUnmount(() => {
  if (inUrl.value) URL.revokeObjectURL(inUrl.value)
  if (outUrl.value) URL.revokeObjectURL(outUrl.value)
})

function onPick(upload: UploadFile) {
  const raw = upload.raw
  if (!raw) return
  file.value = raw
  if (inUrl.value) URL.revokeObjectURL(inUrl.value)
  if (outUrl.value) URL.revokeObjectURL(outUrl.value)
  outUrl.value = ''
  inUrl.value = URL.createObjectURL(raw)
}

async function run() {
  if (!file.value || loading.value) return
  loading.value = true
  try {
    const blob = await api.removeBg(file.value, model.value, alphaMatting.value)
    if (outUrl.value) URL.revokeObjectURL(outUrl.value)
    outUrl.value = URL.createObjectURL(blob)
    ElMessage.success(t('rembg.ok'))
  } catch (e: any) {
    let msg = e?.message || t('rembg.fail')
    const data = e?.response?.data
    if (data instanceof Blob) {
      try {
        const text = await data.text()
        const j = JSON.parse(text)
        if (j?.detail) msg = j.detail
      } catch {
        /* keep msg */
      }
    } else if (typeof data?.detail === 'string') {
      msg = data.detail
    }
    ElMessage.error(msg)
  } finally {
    loading.value = false
  }
}

function download() {
  if (!outUrl.value) return
  const a = document.createElement('a')
  a.href = outUrl.value
  a.download = 'rembg-output.png'
  a.click()
}
</script>

<style scoped>
.tip {
  margin: 0 0 14px;
  color: var(--mute);
  font-size: 13px;
}
.controls {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
  margin-bottom: 16px;
}
.preview {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}
@media (max-width: 900px) {
  .preview {
    grid-template-columns: 1fr;
  }
}
.pane-label {
  font-size: 12px;
  font-weight: 650;
  color: var(--ink-soft);
  margin-bottom: 8px;
}
.frame {
  min-height: 280px;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.7);
  display: grid;
  place-items: center;
  overflow: hidden;
  padding: 12px;
}
.frame.checker {
  background:
    linear-gradient(45deg, #e8eef1 25%, transparent 25%) 0 0 / 16px 16px,
    linear-gradient(-45deg, #e8eef1 25%, transparent 25%) 0 8px / 16px 16px,
    linear-gradient(45deg, transparent 75%, #e8eef1 75%) 8px -8px / 16px 16px,
    linear-gradient(-45deg, transparent 75%, #e8eef1 75%) -8px 0 / 16px 16px,
    #f7fafb;
}
.frame img {
  max-width: 100%;
  max-height: 420px;
  object-fit: contain;
}
.placeholder {
  color: var(--mute);
  font-size: 13px;
}
</style>
