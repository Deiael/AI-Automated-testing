import { computed, ref, watch } from 'vue'
import { defineStore } from 'pinia'

export type PetKind = 'boy' | 'girl' | 'cat' | 'dog'

export type QuestId =
  | 'adopt_pet'
  | 'open_settings'
  | 'create_project'
  | 'create_pipeline'
  | 'upload_req'
  | 'gen_cases'
  | 'feed_once'

export interface PetState {
  adopted: boolean
  kind: PetKind | null
  name: string
  level: number
  exp: number
  hunger: number
  mood: number
  legs: number
  pos: { x: number; y: number }
  inPlayZone: boolean
  completedQuests: QuestId[]
  claimedQuests: QuestId[]
}

export interface QuestDef {
  id: QuestId
  reward: number
  autoComplete?: boolean
}

const STORAGE_KEY = 'ai-test-pet-v1'

const QUEST_DEFS: QuestDef[] = [
  { id: 'adopt_pet', reward: 3, autoComplete: true },
  { id: 'open_settings', reward: 2 },
  { id: 'create_project', reward: 3 },
  { id: 'create_pipeline', reward: 3 },
  { id: 'upload_req', reward: 4 },
  { id: 'gen_cases', reward: 5 },
  { id: 'feed_once', reward: 2 },
]

function defaultState(): PetState {
  return {
    adopted: false,
    kind: null,
    name: '',
    level: 1,
    exp: 0,
    hunger: 70,
    mood: 80,
    legs: 2,
    pos: { x: 24, y: 120 },
    inPlayZone: false,
    completedQuests: [],
    claimedQuests: [],
  }
}

function load(): PetState {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return defaultState()
    return { ...defaultState(), ...JSON.parse(raw) }
  } catch {
    return defaultState()
  }
}

function expToNext(level: number) {
  return 20 + level * 15
}

export const usePetStore = defineStore('pet', () => {
  const state = ref<PetState>(load())

  watch(
    state,
    (v) => {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(v))
    },
    { deep: true },
  )

  const quests = QUEST_DEFS
  const nextExp = computed(() => expToNext(state.value.level))
  const feedCost = computed(() => Math.max(1, Math.ceil(state.value.level * 0.8)))

  function adopt(kind: PetKind, name: string) {
    const switching = state.value.adopted
    state.value.adopted = true
    state.value.kind = kind
    state.value.name = name.trim() || defaultName(kind)
    // switching keeps level / legs / quests; only refresh vitals a bit
    if (!switching) {
      state.value.hunger = 75
      state.value.mood = 85
      completeQuest('adopt_pet')
    } else {
      state.value.mood = Math.min(100, state.value.mood + 10)
      state.value.hunger = Math.min(100, Math.max(state.value.hunger, 55))
    }
  }

  function rename(name: string) {
    const next = name.trim()
    if (!next || !state.value.adopted) return false
    state.value.name = next.slice(0, 12)
    return true
  }

  function defaultName(kind: PetKind) {
    const map: Record<PetKind, string> = {
      boy: '小昊',
      girl: '小念',
      cat: '喵球',
      dog: '旺仔',
    }
    return map[kind]
  }

  function setPos(x: number, y: number) {
    state.value.pos = { x, y }
  }

  function setInPlayZone(v: boolean) {
    state.value.inPlayZone = v
    if (v) {
      state.value.mood = Math.min(100, state.value.mood + 8)
      state.value.exp += 2
      maybeLevelUp()
    }
  }

  function completeQuest(id: QuestId) {
    if (!state.value.completedQuests.includes(id)) {
      state.value.completedQuests.push(id)
    }
  }

  function claimQuest(id: QuestId) {
    if (!state.value.completedQuests.includes(id)) return false
    if (state.value.claimedQuests.includes(id)) return false
    const def = QUEST_DEFS.find((q) => q.id === id)
    if (!def) return false
    state.value.claimedQuests.push(id)
    state.value.legs += def.reward
    return true
  }

  function claimAllReady() {
    let n = 0
    for (const q of QUEST_DEFS) {
      if (claimQuest(q.id)) n += q.reward
    }
    return n
  }

  function feed() {
    const cost = feedCost.value
    if (state.value.legs < cost) return { ok: false as const, reason: 'no_legs' as const }
    state.value.legs -= cost
    state.value.hunger = Math.min(100, state.value.hunger + 25)
    state.value.mood = Math.min(100, state.value.mood + 10)
    state.value.exp += 12 + state.value.level * 2
    completeQuest('feed_once')
    maybeLevelUp()
    return { ok: true as const }
  }

  function maybeLevelUp() {
    while (state.value.exp >= expToNext(state.value.level)) {
      state.value.exp -= expToNext(state.value.level)
      state.value.level += 1
      state.value.mood = Math.min(100, state.value.mood + 15)
    }
  }

  function tickDecay() {
    if (!state.value.adopted) return
    state.value.hunger = Math.max(0, state.value.hunger - 1)
    if (state.value.hunger < 30) {
      state.value.mood = Math.max(0, state.value.mood - 1)
    }
  }

  const pendingClaims = computed(() =>
    QUEST_DEFS.filter(
      (q) => state.value.completedQuests.includes(q.id) && !state.value.claimedQuests.includes(q.id),
    ),
  )

  const activeQuests = computed(() =>
    QUEST_DEFS.map((q) => ({
      ...q,
      done: state.value.completedQuests.includes(q.id),
      claimed: state.value.claimedQuests.includes(q.id),
    })),
  )

  return {
    state,
    quests,
    nextExp,
    feedCost,
    pendingClaims,
    activeQuests,
    adopt,
    rename,
    setPos,
    setInPlayZone,
    completeQuest,
    claimQuest,
    claimAllReady,
    feed,
    tickDecay,
    defaultName,
  }
})
