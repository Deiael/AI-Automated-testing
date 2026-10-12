<template>
  <div class="quest-panel">
    <div class="head">
      <div>
        <div class="foot-label">{{ t('pet.questsTitle') }}</div>
        <div class="legs">
          <span class="drum">🍗</span>
          <strong>{{ pet.state.legs }}</strong>
          <span class="mute">{{ t('pet.legs') }}</span>
        </div>
      </div>
      <el-button v-if="!pet.state.adopted" size="small" type="primary" @click="emit('adopt')">
        {{ t('pet.adopt') }}
      </el-button>
      <div v-else class="head-actions">
        <el-button size="small" @click="emit('adopt')">{{ t('pet.switch') }}</el-button>
        <el-button size="small" type="primary" plain :disabled="!pet.pendingClaims.length" @click="claimAll">
          {{ t('pet.claimAll') }}
        </el-button>
      </div>
    </div>

    <div v-if="pet.state.adopted" class="pet-stats">
      <button type="button" class="avatar-btn" :title="t('pet.switch')" @click="emit('adopt')">
        <PetAvatar :kind="pet.state.kind!" :level="pet.state.level" size="sm" />
      </button>
      <div class="stats">
        <div class="name-row">
          <el-input
            v-if="renaming"
            ref="nameInputRef"
            v-model="editName"
            size="small"
            maxlength="12"
            :placeholder="t('pet.namePh')"
            @keyup.enter="saveName"
            @blur="saveName"
          />
          <button v-else type="button" class="name-display" :title="t('pet.renameHint')" @click="startRename">
            {{ pet.state.name }}
          </button>
          <span class="lv-text">Lv.{{ pet.state.level }}</span>
        </div>
        <div class="bar"><i :style="{ width: expPct + '%' }"></i></div>
        <div class="meta">
          <span>{{ t('pet.hunger') }} {{ pet.state.hunger }}</span>
          <span>{{ t('pet.mood') }} {{ pet.state.mood }}</span>
        </div>
        <div class="stat-actions">
          <el-button size="small" type="primary" plain :disabled="pet.state.legs < pet.feedCost" @click="onFeed">
            {{ t('pet.feed', { n: pet.feedCost }) }}
          </el-button>
          <el-button size="small" link type="primary" @click="emit('adopt')">{{ t('pet.switch') }}</el-button>
        </div>
      </div>
    </div>

    <ul class="quests">
      <li v-for="q in pet.activeQuests" :key="q.id" :class="{ done: q.done, claimed: q.claimed }">
        <div class="q-main">
          <span class="check">{{ q.claimed ? '✓' : q.done ? '●' : '○' }}</span>
          <span>{{ t(`pet.quest.${q.id}`) }}</span>
        </div>
        <button
          v-if="q.done && !q.claimed"
          type="button"
          class="reward"
          @click="claimOne(q.id)"
        >
          +{{ q.reward }}🍗
        </button>
        <span v-else-if="q.claimed" class="got">{{ t('pet.claimed') }}</span>
        <span v-else class="reward mute">+{{ q.reward }}</span>
      </li>
    </ul>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, type InputInstance } from 'element-plus'
import { usePetStore, type QuestId } from '../../stores/pet'
import PetAvatar from './PetAvatar.vue'

const emit = defineEmits<{ (e: 'adopt'): void }>()
const { t } = useI18n()
const pet = usePetStore()
const editName = ref(pet.state.name)
const renaming = ref(false)
const nameInputRef = ref<InputInstance>()

watch(
  () => pet.state.name,
  (v) => {
    if (!renaming.value) editName.value = v
  },
)

const expPct = computed(() => {
  const next = pet.nextExp
  return Math.min(100, Math.round((pet.state.exp / next) * 100))
})

async function startRename() {
  editName.value = pet.state.name
  renaming.value = true
  await nextTick()
  nameInputRef.value?.focus()
  nameInputRef.value?.select?.()
}

function saveName() {
  if (!renaming.value) return
  const next = editName.value.trim()
  if (!next) {
    editName.value = pet.state.name
    renaming.value = false
    ElMessage.warning(t('pet.nameRequired'))
    return
  }
  renaming.value = false
  if (next === pet.state.name) return
  if (pet.rename(next)) ElMessage.success(t('pet.renamed', { name: pet.state.name }))
}

function claimOne(id: QuestId) {
  if (pet.claimQuest(id)) ElMessage.success(t('pet.claimOk'))
}

function claimAll() {
  const n = pet.claimAllReady()
  if (n > 0) ElMessage.success(t('pet.claimAllOk', { n }))
}

function onFeed() {
  const res = pet.feed()
  if (!res.ok) {
    ElMessage.warning(t('pet.needLegs'))
    return
  }
  ElMessage.success(t('pet.fed'))
}
</script>

<style scoped>
.quest-panel {
  margin-top: auto;
  padding: 12px;
  border-radius: 14px;
  border: 1px dashed var(--line-strong);
  background: rgba(255, 255, 255, 0.55);
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 8px;
}
.foot-label {
  font-size: 11px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--mute);
  margin-bottom: 4px;
}
.legs {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
}
.legs strong { color: var(--teal-deep); }
.mute { color: var(--mute); font-size: 12px; }
.drum { font-size: 14px; }

.head-actions {
  display: flex;
  flex-direction: column;
  gap: 4px;
  align-items: stretch;
}
.pet-stats {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 8px;
  align-items: center;
  padding: 8px;
  border-radius: 12px;
  background: rgba(15, 143, 134, 0.06);
}
.avatar-btn {
  border: none;
  background: transparent;
  padding: 0;
  cursor: pointer;
  border-radius: 12px;
}
.avatar-btn:hover {
  filter: brightness(1.05);
}
.stat-actions {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;
}
.name-row {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 4px;
}
.name-row :deep(.el-input) {
  flex: 1;
  min-width: 0;
}
.name-row :deep(.el-input__wrapper) {
  padding: 0 8px;
  min-height: 26px;
}
.name-display {
  flex: 1;
  min-width: 0;
  border: none;
  background: transparent;
  padding: 2px 0;
  text-align: left;
  font: inherit;
  font-size: 13px;
  font-weight: 650;
  color: var(--ink);
  cursor: pointer;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  border-radius: 4px;
}
.name-display:hover {
  color: var(--teal-deep);
  text-decoration: underline;
  text-underline-offset: 3px;
}
.lv-text {
  flex-shrink: 0;
  font-size: 11px;
  font-weight: 700;
  color: var(--teal-deep);
  font-family: var(--font-mono);
}
.bar {
  height: 6px;
  border-radius: 999px;
  background: rgba(18, 32, 43, 0.08);
  overflow: hidden;
  margin-bottom: 4px;
}
.bar i {
  display: block;
  height: 100%;
  background: linear-gradient(90deg, #0f8f86, #3aaea6);
  border-radius: inherit;
}
.meta {
  display: flex;
  gap: 8px;
  font-size: 11px;
  color: var(--mute);
  margin-bottom: 6px;
}

.quests {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 180px;
  overflow: auto;
}
.quests li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  font-size: 12px;
  color: var(--ink-soft);
  padding: 4px 0;
}
.quests li.claimed { opacity: 0.55; }
.q-main {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  min-width: 0;
}
.check {
  color: var(--teal-deep);
  font-weight: 700;
  line-height: 1.3;
}
.reward {
  border: none;
  background: rgba(240, 160, 75, 0.18);
  color: #b86a1e;
  border-radius: 999px;
  padding: 2px 8px;
  font-size: 11px;
  font-weight: 700;
  cursor: pointer;
  white-space: nowrap;
}
.reward.mute {
  background: transparent;
  color: var(--mute);
  cursor: default;
}
.got {
  font-size: 11px;
  color: var(--ok);
}
</style>
