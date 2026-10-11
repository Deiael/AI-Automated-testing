<template>
  <div class="chat panel">
    <div class="chat-head">
      <div>
        <div class="kicker">Multi-turn · SSE</div>
        <div class="title">{{ t('chat.title') }}</div>
      </div>
      <div class="model-badge" :class="{ live: llmLive, mock: llmLive === false }">
        <span>{{ modelLabel }}</span>
      </div>
    </div>

    <div ref="box" class="messages">
      <div v-if="!messages.length && !streaming" class="empty">
        <div class="empty-mark"></div>
        <p>{{ t('chat.empty') }}</p>
      </div>

      <div v-for="(m, i) in messages" :key="i" class="msg" :class="m.role">
        <div class="bubble">
          <div class="role">{{ m.role === 'user' ? t('chat.you') : t('chat.engine') }}</div>
          <div class="content">{{ m.content }}</div>
        </div>
      </div>

      <div v-if="streaming" class="msg assistant">
        <div class="bubble">
          <div class="role">{{ t('chat.engine') }}</div>
          <div class="content">{{ streamText }}<span class="cursor" /></div>
        </div>
      </div>

      <div v-if="questions.length" class="ask panel-soft">
        <div class="ask-title">{{ t('chat.needMore') }}</div>
        <ul>
          <li v-for="(q, i) in questions" :key="i">{{ q }}</li>
        </ul>
      </div>

      <div v-if="artifacts.length" class="arts">
        <div v-for="a in artifacts" :key="a.id" class="art">
          <span class="kind">{{ a.kind }}</span>
          <span class="name">{{ a.title }}</span>
          <span class="mono">{{ a.id.slice(0, 8) }}</span>
        </div>
      </div>
    </div>

    <div class="composer">
      <el-input
        v-model="input"
        type="textarea"
        :rows="3"
        resize="none"
        :placeholder="t('chat.placeholder')"
        @keydown.ctrl.enter="send"
      />
      <el-button type="primary" size="large" :loading="streaming" @click="send">{{ t('chat.send') }}</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { api, streamChat } from '../api'

const { t } = useI18n()

const props = defineProps<{
  sessionId: string
  engineProfileId?: string
  testPointIds?: string[]
  testCaseIds?: string[]
}>()
const emit = defineEmits<{ (e: 'artifact', payload: any): void; (e: 'done'): void }>()

const messages = ref<{ role: string; content: string }[]>([])
const input = ref('')
const streaming = ref(false)
const streamText = ref('')
const questions = ref<string[]>([])
const artifacts = ref<{ id: string; kind: string; title: string }[]>([])
const box = ref<HTMLElement>()
const modelName = ref('')
const llmLive = ref<boolean | null>(null)
const modelLabel = computed(() => {
  if (!modelName.value && llmLive.value === null) return t('chat.waitingModel')
  if (llmLive.value === false) return t('chat.mock', { model: modelName.value || 'unknown' })
  return t('chat.live', { model: modelName.value || 'unknown' })
})

onMounted(async () => {
  const list = await api.listMessages(props.sessionId)
  messages.value = list.map((m: any) => ({ role: m.role, content: m.content }))
  await nextTick()
  scrollBottom()
})

async function send() {
  if (!input.value.trim() || streaming.value) return
  const text = input.value.trim()
  input.value = ''
  messages.value.push({ role: 'user', content: text })
  streaming.value = true
  streamText.value = ''
  questions.value = []
  try {
    await streamChat(
      props.sessionId,
      {
        message: text,
        engine_profile_id: props.engineProfileId,
        test_point_ids: props.testPointIds,
        test_case_ids: props.testCaseIds,
      },
      (ev) => {
        if (ev.event === 'meta') {
          modelName.value = ev.data?.model || ''
          llmLive.value = !!ev.data?.llm_enabled
        }
        if (ev.event === 'token') streamText.value += ev.data?.delta || ''
        if (ev.event === 'message') {
          const content = ev.data?.content || streamText.value
          messages.value.push({ role: 'assistant', content })
          streamText.value = ''
        }
        if (ev.event === 'ask_user') questions.value = ev.data?.questions || []
        if (ev.event === 'artifact') {
          const kind = ev.data?.kind
          const payload = ev.data?.payload || {}
          const id = ev.data?.artifact_id || ''
          if (id) {
            artifacts.value.push({ id, kind, title: payload.title || kind })
            emit('artifact', { ...ev.data })
          }
        }
        if (ev.event === 'error') ElMessage.error(ev.data?.message || t('chat.engineError'))
        if (ev.event === 'done') emit('done')
        scrollBottom()
      },
    )
  } catch (e: any) {
    ElMessage.error(e.message || t('chat.sendFail'))
  } finally {
    streaming.value = false
  }
}

function scrollBottom() {
  nextTick(() => {
    if (box.value) box.value.scrollTop = box.value.scrollHeight
  })
}
</script>

<style scoped>
.chat {
  display: flex;
  flex-direction: column;
  height: 620px;
  overflow: hidden;
}

.chat-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 16px;
  border-bottom: 1px solid var(--line);
}

.kicker {
  font-size: 11px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--teal-deep);
  font-weight: 600;
}

.title {
  font-family: var(--font-brand);
  font-weight: 650;
  margin-top: 2px;
}

.model-badge {
  font-family: var(--font-mono);
  font-size: 11px;
  padding: 5px 10px;
  border-radius: 999px;
  border: 1px solid var(--line);
  color: var(--mute);
  background: rgba(255, 255, 255, 0.7);
}
.model-badge.live {
  color: var(--teal-deep);
  border-color: rgba(15, 143, 134, 0.35);
  background: var(--teal-soft);
}
.model-badge.mock {
  color: var(--amber);
  border-color: rgba(201, 133, 45, 0.35);
  background: rgba(201, 133, 45, 0.1);
}

.messages {
  flex: 1;
  overflow: auto;
  padding: 16px;
  background:
    radial-gradient(500px 180px at 10% 0%, rgba(15, 143, 134, 0.08), transparent 60%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.35), rgba(247, 250, 251, 0.65));
}

.empty {
  height: 100%;
  min-height: 220px;
  display: grid;
  place-content: center;
  justify-items: center;
  gap: 10px;
  color: var(--mute);
  text-align: center;
}

.empty-mark {
  width: 48px;
  height: 48px;
  border-radius: 16px;
  border: 1px dashed rgba(15, 143, 134, 0.45);
  background: var(--teal-soft);
  animation: pulse 2.4s ease-in-out infinite;
}

@keyframes pulse {
  0%,
  100% {
    transform: scale(1);
    opacity: 0.8;
  }
  50% {
    transform: scale(1.05);
    opacity: 1;
  }
}

.msg {
  display: flex;
  margin-bottom: 12px;
}

.msg.user {
  justify-content: flex-end;
}

.bubble {
  max-width: min(86%, 520px);
  padding: 10px 12px;
  border-radius: 14px;
  border: 1px solid var(--line);
  background: rgba(255, 255, 255, 0.88);
}

.msg.user .bubble {
  background: linear-gradient(145deg, rgba(15, 143, 134, 0.16), rgba(15, 143, 134, 0.08));
  border-color: rgba(15, 143, 134, 0.22);
}

.role {
  font-size: 11px;
  color: var(--mute);
  margin-bottom: 4px;
  letter-spacing: 0.04em;
}

.content {
  white-space: pre-wrap;
  line-height: 1.55;
  font-size: 14px;
}

.cursor {
  display: inline-block;
  width: 7px;
  height: 1em;
  margin-left: 2px;
  vertical-align: text-bottom;
  background: var(--teal);
  animation: blink 1s steps(1) infinite;
}

@keyframes blink {
  50% {
    opacity: 0;
  }
}

.ask {
  margin-top: 8px;
  padding: 12px 14px;
  border-radius: 12px;
  border: 1px solid rgba(201, 133, 45, 0.25);
  background: rgba(201, 133, 45, 0.08);
}

.ask-title {
  font-weight: 650;
  margin-bottom: 6px;
  color: var(--amber);
}

.ask ul {
  margin: 0;
  padding-left: 18px;
  color: var(--ink-soft);
}

.arts {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.art {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(47, 157, 106, 0.1);
  border: 1px solid rgba(47, 157, 106, 0.2);
  font-size: 12px;
}

.kind {
  font-weight: 700;
  color: var(--ok);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.name {
  max-width: 180px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.composer {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 10px;
  padding: 12px;
  border-top: 1px solid var(--line);
  background: rgba(255, 255, 255, 0.65);
  align-items: end;
}
</style>
