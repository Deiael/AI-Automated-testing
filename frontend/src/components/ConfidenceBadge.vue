<template>
  <span class="conf-badge" :class="band" :title="hint">
    <span class="pct">{{ pct }}%</span>
    <span class="lab">{{ label }}</span>
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const props = defineProps<{ value?: number | null; compact?: boolean }>()
const { t } = useI18n()

const score = computed(() => {
  const n = Number(props.value ?? 0)
  if (Number.isNaN(n)) return 0
  return Math.max(0, Math.min(1, n))
})
const pct = computed(() => Math.round(score.value * 100))
const band = computed(() => (score.value >= 0.8 ? 'high' : score.value >= 0.6 ? 'medium' : 'low'))
const label = computed(() => t(`confidence.band.${band.value}`))
const hint = computed(() => t('confidence.hint', { n: pct.value }))
</script>

<style scoped>
.conf-badge {
  display: inline-flex;
  align-items: baseline;
  gap: 4px;
  padding: 2px 8px;
  border-radius: 999px;
  font-family: var(--font-mono);
  font-size: 12px;
  font-weight: 700;
  white-space: nowrap;
}
.conf-badge.high {
  color: var(--ok);
  background: rgba(47, 157, 106, 0.12);
}
.conf-badge.medium {
  color: var(--amber);
  background: rgba(201, 133, 45, 0.14);
}
.conf-badge.low {
  color: var(--rose);
  background: rgba(196, 91, 91, 0.12);
}
.lab {
  font-family: var(--font-body);
  font-weight: 600;
  font-size: 11px;
}
</style>
