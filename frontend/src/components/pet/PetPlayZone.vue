<template>
  <div
    v-if="pet.state.adopted"
    id="pet-play-zone"
    class="zone"
    :class="{ active: pet.state.inPlayZone }"
  >
    <div class="zone-label">{{ t('pet.playZone') }}</div>
    <div class="toys" aria-hidden="true">
      <span class="ball"></span>
      <span class="yarn"></span>
      <span class="bone"></span>
    </div>
    <p>{{ pet.state.inPlayZone ? t('pet.playing') : t('pet.dragHere') }}</p>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { usePetStore } from '../../stores/pet'

const { t } = useI18n()
const pet = usePetStore()
</script>

<style scoped>
.zone {
  position: fixed;
  right: 24px;
  bottom: 24px;
  z-index: 35;
  width: 200px;
  height: 140px;
  border-radius: 20px;
  border: 2px dashed rgba(15, 143, 134, 0.35);
  background:
    radial-gradient(circle at 20% 30%, rgba(255, 196, 120, 0.25), transparent 45%),
    radial-gradient(circle at 80% 70%, rgba(15, 143, 134, 0.12), transparent 50%),
    rgba(255, 255, 255, 0.72);
  backdrop-filter: blur(10px);
  box-shadow: var(--shadow-soft);
  padding: 12px;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  transition: border-color 0.25s, background 0.25s, transform 0.25s;
  pointer-events: none;
}
.zone.active {
  border-style: solid;
  border-color: var(--teal);
  background:
    radial-gradient(circle at 30% 40%, rgba(255, 180, 90, 0.35), transparent 50%),
    rgba(15, 143, 134, 0.1);
  transform: scale(1.02);
}
.zone-label {
  position: absolute;
  top: 10px;
  left: 12px;
  font-size: 11px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--teal-deep);
  font-weight: 700;
}
.zone p {
  margin: 0;
  font-size: 12px;
  color: var(--mute);
}
.toys {
  position: absolute;
  inset: 28px 12px 36px;
}
.ball,
.yarn,
.bone {
  position: absolute;
  border-radius: 50%;
}
.ball {
  width: 18px;
  height: 18px;
  left: 18px;
  top: 12px;
  background: radial-gradient(circle at 30% 30%, #fff, #f0a04b);
  animation: floaty 2.2s ease-in-out infinite;
}
.yarn {
  width: 22px;
  height: 22px;
  right: 22px;
  top: 8px;
  background: conic-gradient(from 40deg, #7ec8c0, #0f8f86, #7ec8c0);
  opacity: 0.85;
  animation: floaty 2.8s ease-in-out infinite reverse;
}
.bone {
  width: 28px;
  height: 10px;
  left: 50%;
  bottom: 4px;
  margin-left: -14px;
  border-radius: 8px;
  background: #f3e6d2;
  box-shadow: -8px 0 0 #f3e6d2, 8px 0 0 #f3e6d2;
  animation: floaty 3s ease-in-out infinite;
}
@keyframes floaty {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-5px); }
}
@media (max-width: 900px) {
  .zone {
    right: 12px;
    bottom: 12px;
    width: 160px;
    height: 120px;
  }
}
</style>
