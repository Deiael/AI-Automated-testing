<template>
  <div
    class="avatar"
    :class="[sizeClass, { bounce, idle: isHuman, playing: bounce && isHuman }]"
    :title="name"
  >
    <template v-if="isHuman">
      <div class="stage">
        <div class="shadow" aria-hidden="true" />
        <div class="actor">
          <img class="art portrait" :src="portraitSrc" :alt="name || kind" draggable="false" />
        </div>
        <span v-if="bounce" class="spark s1" aria-hidden="true" />
        <span v-if="bounce" class="spark s2" aria-hidden="true" />
        <span v-if="bounce" class="spark s3" aria-hidden="true" />
      </div>
    </template>

    <svg v-else-if="kind === 'cat'" class="art" viewBox="0 0 120 130" xmlns="http://www.w3.org/2000/svg">
      <ellipse cx="60" cy="120" rx="30" ry="5" fill="rgba(18,32,43,0.12)" />
      <path class="tail" d="M88 78c18-4 24-20 18-32" stroke="#e2b574" stroke-width="10" stroke-linecap="round" fill="none" />
      <path d="M88 78c18-4 24-20 18-32" stroke="#f0c890" stroke-width="5" stroke-linecap="round" fill="none" opacity="0.5" />
      <ellipse cx="60" cy="86" rx="34" ry="24" :fill="`url(#${uid}-catFur)`" />
      <g class="paw-l">
        <ellipse cx="38" cy="104" rx="11" ry="8" fill="#f0c890" />
        <ellipse cx="38" cy="106" rx="8" ry="5" fill="#ffe8d2" />
        <path d="M32 102v4M38 101v5M44 102v4" stroke="#e0b080" stroke-width="1.8" stroke-linecap="round" />
      </g>
      <g class="paw-r">
        <ellipse cx="82" cy="104" rx="11" ry="8" fill="#f0c890" />
        <ellipse cx="82" cy="106" rx="8" ry="5" fill="#ffe8d2" />
        <path d="M76 102v4M82 101v5M88 102v4" stroke="#e0b080" stroke-width="1.8" stroke-linecap="round" />
      </g>
      <ellipse cx="48" cy="108" rx="7" ry="4" fill="#e2b574" opacity="0.85" />
      <ellipse cx="72" cy="108" rx="7" ry="4" fill="#e2b574" opacity="0.85" />
      <circle cx="60" cy="48" r="30" :fill="`url(#${uid}-catFur)`" />
      <path d="M36 28 L42 8 L54 26z" fill="#efc48a" />
      <path d="M40 26 L44 14 L50 25z" fill="#f7c4b0" />
      <path d="M84 28 L78 8 L66 26z" fill="#efc48a" />
      <path d="M80 26 L76 14 L70 25z" fill="#f7c4b0" />
      <ellipse cx="60" cy="58" rx="14" ry="10" fill="#ffe8d2" opacity="0.55" />
      <ellipse cx="48" cy="46" rx="7" ry="9" fill="#fff" />
      <ellipse cx="72" cy="46" rx="7" ry="9" fill="#fff" />
      <ellipse cx="49" cy="47" rx="4" ry="5.5" fill="#1f8a5a" />
      <ellipse cx="73" cy="47" rx="4" ry="5.5" fill="#1f8a5a" />
      <ellipse cx="49" cy="47" rx="2" ry="3" fill="#0d3d2a" />
      <ellipse cx="73" cy="47" rx="2" ry="3" fill="#0d3d2a" />
      <circle cx="50.5" cy="45" r="1.3" fill="#fff" />
      <circle cx="74.5" cy="45" r="1.3" fill="#fff" />
      <path d="M56 56c2 3 6 3 8 0" stroke="#d4786a" stroke-width="1.5" fill="none" />
      <ellipse cx="60" cy="54" rx="4" ry="3" fill="#d4786a" />
      <path d="M60 57v5" stroke="#c07060" stroke-width="1.4" />
      <path d="M30 52h14M30 56h12M90 52h-14M90 56h-12" stroke="rgba(80,50,20,0.35)" stroke-width="1.4" stroke-linecap="round" />
      <defs>
        <linearGradient :id="`${uid}-catFur`" x1="60" y1="18" x2="60" y2="110">
          <stop offset="0%" stop-color="#f6d7a8" />
          <stop offset="100%" stop-color="#e2b574" />
        </linearGradient>
      </defs>
    </svg>

    <svg v-else class="art" viewBox="0 0 120 130" xmlns="http://www.w3.org/2000/svg">
      <ellipse cx="60" cy="120" rx="30" ry="5" fill="rgba(18,32,43,0.12)" />
      <path class="tail" d="M90 80c16 2 22-10 18-22" stroke="#d4a56e" stroke-width="11" stroke-linecap="round" fill="none" />
      <ellipse cx="60" cy="88" rx="36" ry="24" :fill="`url(#${uid}-dogFur)`" />
      <path d="M34 74c8 6 18 9 26 9s18-3 26-9" stroke="#0f8f86" stroke-width="5" fill="none" stroke-linecap="round" />
      <circle cx="78" cy="78" r="5" fill="#f0a04b" stroke="#fff" stroke-width="1.5" />
      <g class="paw-l">
        <ellipse cx="36" cy="106" rx="12" ry="8" fill="#e8bc88" />
        <ellipse cx="36" cy="108" rx="9" ry="5" fill="#f7e2c4" />
        <circle cx="30" cy="104" r="2.2" fill="#e0b080" />
        <circle cx="36" cy="103" r="2.2" fill="#e0b080" />
        <circle cx="42" cy="104" r="2.2" fill="#e0b080" />
      </g>
      <g class="paw-r">
        <ellipse cx="84" cy="106" rx="12" ry="8" fill="#e8bc88" />
        <ellipse cx="84" cy="108" rx="9" ry="5" fill="#f7e2c4" />
        <circle cx="78" cy="104" r="2.2" fill="#e0b080" />
        <circle cx="84" cy="103" r="2.2" fill="#e0b080" />
        <circle cx="90" cy="104" r="2.2" fill="#e0b080" />
      </g>
      <ellipse cx="50" cy="110" rx="8" ry="4" fill="#d4a56e" />
      <ellipse cx="70" cy="110" rx="8" ry="4" fill="#d4a56e" />
      <path d="M28 40c-8 4-12 18-6 28 8-2 14-12 12-24z" fill="#c9956a" />
      <path d="M92 40c8 4 12 18 6 28-8-2-14-12-12-24z" fill="#c9956a" />
      <circle cx="60" cy="48" r="30" :fill="`url(#${uid}-dogFur)`" />
      <ellipse cx="48" cy="46" rx="7" ry="9" fill="#fff" />
      <ellipse cx="72" cy="46" rx="7" ry="9" fill="#fff" />
      <ellipse cx="49" cy="47" rx="3.8" ry="5.2" fill="#3a2a1a" />
      <ellipse cx="73" cy="47" rx="3.8" ry="5.2" fill="#3a2a1a" />
      <circle cx="50.4" cy="45" r="1.3" fill="#fff" />
      <circle cx="74.4" cy="45" r="1.3" fill="#fff" />
      <ellipse cx="60" cy="62" rx="14" ry="11" fill="#f7e2c4" />
      <ellipse cx="60" cy="58" rx="5" ry="3.5" fill="#3a2a1a" />
      <path d="M60 61v6" stroke="#3a2a1a" stroke-width="1.5" />
      <path d="M54 68c3 3 9 3 12 0" stroke="#c07060" stroke-width="2" stroke-linecap="round" fill="none" />
      <ellipse cx="40" cy="56" rx="5" ry="2.5" fill="rgba(255,120,130,0.3)" />
      <ellipse cx="80" cy="56" rx="5" ry="2.5" fill="rgba(255,120,130,0.3)" />
      <defs>
        <linearGradient :id="`${uid}-dogFur`" x1="60" y1="18" x2="60" y2="112">
          <stop offset="0%" stop-color="#f0d0a8" />
          <stop offset="100%" stop-color="#d4a56e" />
        </linearGradient>
      </defs>
    </svg>

    <div v-if="showBadge" class="lv">Lv.{{ level }}</div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { PetKind } from '../../stores/pet'

const props = withDefaults(
  defineProps<{
    kind: PetKind
    name?: string
    level?: number
    size?: 'sm' | 'md' | 'lg'
    bounce?: boolean
    showBadge?: boolean
  }>(),
  { name: '', level: 1, size: 'md', bounce: false, showBadge: true },
)

const sizeClass = computed(() => `size-${props.size}`)
const isHuman = computed(() => props.kind === 'boy' || props.kind === 'girl')
const uid = `p${Math.random().toString(36).slice(2, 9)}`
const portraitSrc = computed(() =>
  props.kind === 'girl' ? '/pets/girl.png' : props.kind === 'boy' ? '/pets/boy.png' : '',
)
</script>

<style scoped>
.avatar {
  position: relative;
  width: 96px;
  height: 114px;
  user-select: none;
  pointer-events: none;
}
.avatar.idle {
  width: 88px;
  height: 148px;
}
.size-sm {
  width: 58px;
  height: 70px;
}
.avatar.idle.size-sm {
  width: 52px;
  height: 88px;
}
.size-lg {
  width: 120px;
  height: 142px;
}
.avatar.idle.size-lg {
  width: 112px;
  height: 188px;
}

.stage {
  position: relative;
  width: 100%;
  height: 100%;
}

.shadow {
  position: absolute;
  left: 50%;
  bottom: 2px;
  width: 48%;
  height: 10px;
  transform: translateX(-50%);
  border-radius: 50%;
  background: rgba(18, 32, 43, 0.18);
  filter: blur(1px);
  animation: shadow-breathe 2.4s ease-in-out infinite;
}

.actor {
  position: absolute;
  inset: 0 0 8px;
  transform-origin: 50% 88%;
  animation: idle-bob 2.4s ease-in-out infinite;
  will-change: transform;
}

.playing .actor {
  animation:
    play-hop 0.85s ease-in-out infinite,
    play-sway 1.7s ease-in-out infinite;
}

.art {
  width: 100%;
  height: 100%;
  display: block;
  overflow: visible;
}

.art.portrait {
  width: 100%;
  height: 100%;
  object-fit: contain;
  object-position: center bottom;
  border-radius: 0;
  background: transparent;
  /* soft ground shadow only — no photo frame */
  filter: drop-shadow(0 10px 8px rgba(18, 32, 43, 0.22));
}

.spark {
  position: absolute;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #3aaea6;
  opacity: 0;
  pointer-events: none;
}
.spark.s1 {
  left: 12%;
  top: 28%;
  animation: sparkle 1.4s ease-in-out infinite;
}
.spark.s2 {
  right: 10%;
  top: 18%;
  width: 5px;
  height: 5px;
  background: #e87d94;
  animation: sparkle 1.4s ease-in-out 0.35s infinite;
}
.spark.s3 {
  right: 22%;
  top: 42%;
  width: 4px;
  height: 4px;
  background: #c9852d;
  animation: sparkle 1.4s ease-in-out 0.7s infinite;
}

.bounce .art:not(.portrait) {
  animation: hop 1.1s ease-in-out infinite;
}
.bounce .paw-l,
.bounce .paw-r {
  animation: tap 0.9s ease-in-out infinite;
}
.bounce .tail {
  animation: wag 0.8s ease-in-out infinite;
  transform-origin: 88px 78px;
}

@keyframes idle-bob {
  0%,
  100% {
    transform: translateY(0) rotate(-1.2deg) scale(1, 1);
  }
  40% {
    transform: translateY(-5px) rotate(1.4deg) scale(1.01, 0.99);
  }
  70% {
    transform: translateY(-2px) rotate(-0.6deg) scale(0.995, 1.01);
  }
}

@keyframes play-hop {
  0%,
  100% {
    transform: translateY(0) scale(1, 1);
  }
  45% {
    transform: translateY(-12px) scale(0.98, 1.03);
  }
  70% {
    transform: translateY(-2px) scale(1.02, 0.97);
  }
}

@keyframes play-sway {
  0%,
  100% {
    rotate: -4deg;
  }
  50% {
    rotate: 4deg;
  }
}

@keyframes shadow-breathe {
  0%,
  100% {
    transform: translateX(-50%) scaleX(1);
    opacity: 0.55;
  }
  50% {
    transform: translateX(-50%) scaleX(0.72);
    opacity: 0.32;
  }
}

@keyframes sparkle {
  0%,
  100% {
    opacity: 0;
    transform: translateY(0) scale(0.6);
  }
  40% {
    opacity: 0.95;
    transform: translateY(-8px) scale(1);
  }
}

@keyframes hop {
  0%,
  100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-5px);
  }
}
@keyframes tap {
  0%,
  100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(2px);
  }
}
@keyframes wag {
  0%,
  100% {
    transform: rotate(-8deg);
  }
  50% {
    transform: rotate(14deg);
  }
}

.lv {
  position: absolute;
  right: -2px;
  bottom: 0;
  z-index: 4;
  font-size: 10px;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 999px;
  background: rgba(15, 143, 134, 0.92);
  color: #fff;
  font-family: var(--font-mono);
}
</style>
