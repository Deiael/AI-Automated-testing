import { usePetStore, type QuestId } from '../stores/pet'

/** Call from feature pages when a newbie milestone is reached. */
export function usePetQuests() {
  const pet = usePetStore()

  function mark(id: QuestId) {
    pet.completeQuest(id)
  }

  return { mark, pet }
}
