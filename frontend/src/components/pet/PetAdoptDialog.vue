<template>
  <el-dialog
    v-model="open"
    :title="isSwitch ? t('pet.switchTitle') : t('pet.adoptTitle')"
    width="640px"
    align-center
    destroy-on-close
    append-to-body
  >
    <p class="tip">{{ isSwitch ? t('pet.switchTip') : t('pet.adoptTip') }}</p>
    <el-form label-position="top">
      <el-form-item :label="t('pet.name')" required>
        <el-input
          v-model="name"
          maxlength="12"
          show-word-limit
          clearable
          :placeholder="t('pet.namePh')"
        />
      </el-form-item>
      <el-form-item :label="t('pet.pickKind')">
        <div class="kind-grid">
          <button
            v-for="k in kinds"
            :key="k"
            type="button"
            class="kind-card"
            :class="{ active: kind === k }"
            @click="onPick(k)"
          >
            <PetAvatar :kind="k" :show-badge="false" size="md" />
            <span>{{ t(`pet.kinds.${k}`) }}</span>
          </button>
        </div>
      </el-form-item>
    </el-form>
    <template #footer>
      <div class="dialog-actions">
        <el-button @click="open = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" :disabled="!kind" @click="confirm">
          {{ isSwitch ? t('pet.switchConfirm') : t('pet.adoptConfirm') }}
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { usePetStore, type PetKind } from '../../stores/pet'
import PetAvatar from './PetAvatar.vue'

const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{ (e: 'update:modelValue', v: boolean): void }>()
const { t } = useI18n()
const pet = usePetStore()

const open = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const isSwitch = computed(() => pet.state.adopted)
const kinds: PetKind[] = ['boy', 'girl', 'cat', 'dog']
const kind = ref<PetKind | null>(null)
const name = ref('')

watch(open, (v) => {
  if (!v) return
  if (pet.state.adopted) {
    kind.value = pet.state.kind
    name.value = pet.state.name
  } else {
    kind.value = null
    name.value = ''
  }
})

function onPick(k: PetKind) {
  kind.value = k
  // only suggest a default nickname when the field is still empty
  if (!name.value.trim()) name.value = pet.defaultName(k)
}

function confirm() {
  if (!kind.value) return
  const custom = name.value.trim()
  if (!custom) {
    ElMessage.warning(t('pet.nameRequired'))
    return
  }
  const switching = pet.state.adopted
  pet.adopt(kind.value, custom)
  ElMessage.success(
    switching
      ? t('pet.switched', { name: pet.state.name })
      : t('pet.adopted', { name: pet.state.name }),
  )
  open.value = false
}
</script>

<style scoped>
.tip {
  margin: 0 0 14px;
  color: var(--mute);
  font-size: 13px;
  line-height: 1.5;
}
.kind-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
  width: 100%;
}
.kind-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 12px 8px;
  border-radius: 14px;
  border: 1px solid var(--line);
  background: rgba(255, 255, 255, 0.85);
  cursor: pointer;
  font: inherit;
  color: var(--ink-soft);
  transition: border-color 0.2s, transform 0.2s, background 0.2s;
}
.kind-card:hover {
  transform: translateY(-2px);
  border-color: rgba(15, 143, 134, 0.35);
}
.kind-card.active {
  border-color: var(--teal);
  background: var(--teal-soft);
  color: var(--teal-deep);
  font-weight: 650;
}
@media (max-width: 640px) {
  .kind-grid { grid-template-columns: repeat(2, 1fr); }
}
</style>
