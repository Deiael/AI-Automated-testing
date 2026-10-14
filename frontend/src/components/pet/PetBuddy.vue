<template>
  <div
    v-if="pet.state.adopted && pet.state.kind"
    ref="el"
    class="buddy"
    :class="{ dragging, playing: pet.state.inPlayZone }"
    :style="{ left: `${pet.state.pos.x}px`, top: `${pet.state.pos.y}px` }"
    @pointerdown="onDown"
  >
    <div class="bubble" v-if="bubble">{{ bubble }}</div>
    <PetAvatar
      :kind="pet.state.kind"
      :name="pet.state.name"
      :level="pet.state.level"
      :bounce="pet.state.inPlayZone && !dragging"
      size="md"
    />
    <div class="tag">{{ pet.state.name }}</div>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { usePetStore } from '../../stores/pet'
import PetAvatar from './PetAvatar.vue'

const pet = usePetStore()
const { t } = useI18n()
const el = ref<HTMLElement | null>(null)
const dragging = ref(false)
const bubble = ref('')
let ox = 0
let oy = 0
let bubbleTimer: number | undefined

function showBubble(text: string) {
  bubble.value = text
  window.clearTimeout(bubbleTimer)
  bubbleTimer = window.setTimeout(() => {
    bubble.value = ''
  }, 1800)
}

const RAIL_SAFE = 260
let activePointerId: number | null = null

function onDown(e: PointerEvent) {
  if (!el.value || e.button !== 0) return
  e.preventDefault()
  dragging.value = true
  activePointerId = e.pointerId
  try {
    el.value.setPointerCapture(e.pointerId)
  } catch {
    /* ignore */
  }
  ox = e.clientX - pet.state.pos.x
  oy = e.clientY - pet.state.pos.y
  window.addEventListener('pointermove', onMove)
  window.addEventListener('pointerup', onUp)
  window.addEventListener('pointercancel', onUp)
}

function onMove(e: PointerEvent) {
  if (!dragging.value) return
  const maxX = window.innerWidth - 100
  const maxY = window.innerHeight - 120
  // Never cover the left navigation rail
  const x = Math.min(maxX, Math.max(RAIL_SAFE, e.clientX - ox))
  const y = Math.min(maxY, Math.max(8, e.clientY - oy))
  pet.setPos(x, y)

  const zone = document.getElementById('pet-play-zone')
  if (zone) {
    const r = zone.getBoundingClientRect()
    const cx = e.clientX
    const cy = e.clientY
    const inside = cx >= r.left && cx <= r.right && cy >= r.top && cy <= r.bottom
    if (inside !== pet.state.inPlayZone) {
      pet.setInPlayZone(inside)
      if (inside) showBubble(t('pet.playYay'))
    }
  }
}

function onUp(e?: PointerEvent) {
  if (el.value && activePointerId != null) {
    try {
      el.value.releasePointerCapture(activePointerId)
    } catch {
      /* ignore */
    }
  }
  activePointerId = null
  dragging.value = false
  window.removeEventListener('pointermove', onMove)
  window.removeEventListener('pointerup', onUp)
  window.removeEventListener('pointercancel', onUp)
  if (e) e.preventDefault()
}

let decayTimer: number | undefined

onMounted(() => {
  decayTimer = window.setInterval(() => pet.tickDecay(), 60000)
  // Nudge pets that were saved over the left rail
  if (pet.state.pos.x < RAIL_SAFE) {
    pet.setPos(Math.max(RAIL_SAFE, window.innerWidth - 140), pet.state.pos.y)
  }
})

onBeforeUnmount(() => {
  onUp()
  window.clearInterval(decayTimer)
  window.clearTimeout(bubbleTimer)
})
</script>

<style scoped>
.buddy {
  position: fixed;
  z-index: 40;
  cursor: grab;
  touch-action: none;
  filter: drop-shadow(0 8px 16px rgba(18, 32, 43, 0.18));
  transition: filter 0.2s;
}
.buddy.dragging {
  cursor: grabbing;
  z-index: 60;
  filter: drop-shadow(0 14px 24px rgba(15, 143, 134, 0.28));
}
.tag {
  margin-top: 2px;
  text-align: center;
  font-size: 11px;
  font-weight: 650;
  color: var(--teal-deep);
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid var(--line);
  border-radius: 999px;
  padding: 2px 8px;
  max-width: 88px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.bubble {
  position: absolute;
  left: 50%;
  bottom: calc(100% + 6px);
  transform: translateX(-50%);
  white-space: nowrap;
  font-size: 12px;
  padding: 6px 10px;
  border-radius: 12px;
  background: #fff;
  border: 1px solid var(--line);
  color: var(--ink-soft);
  box-shadow: var(--shadow-soft);
  animation: pop 0.25s ease;
}
@keyframes pop {
  from { opacity: 0; transform: translateX(-50%) translateY(4px); }
  to { opacity: 1; transform: translateX(-50%) translateY(0); }
}
</style>
