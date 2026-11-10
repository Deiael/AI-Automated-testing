/** Pipeline test-type catalog. Add a row here when introducing a new type. */
export type PipelineKindId = 'api' | 'version_regression' | 'smoke' | 'system'

export type PipelineKind = {
  id: PipelineKindId
  available: boolean
  ico: string
  titleKey: string
  descKey: string
}

export const PIPELINE_KINDS: PipelineKind[] = [
  {
    id: 'api',
    available: true,
    ico: '◎',
    titleKey: 'pipelineKinds.api.title',
    descKey: 'pipelineKinds.api.desc',
  },
  {
    id: 'version_regression',
    available: true,
    ico: '⇄',
    titleKey: 'pipelineKinds.version_regression.title',
    descKey: 'pipelineKinds.version_regression.desc',
  },
  {
    id: 'smoke',
    available: false,
    ico: '⌁',
    titleKey: 'pipelineKinds.smoke.title',
    descKey: 'pipelineKinds.smoke.desc',
  },
  {
    id: 'system',
    available: false,
    ico: '▣',
    titleKey: 'pipelineKinds.system.title',
    descKey: 'pipelineKinds.system.desc',
  },
]

export function pipelineKindOf(id: string | undefined | null): PipelineKind {
  return PIPELINE_KINDS.find((k) => k.id === id) || PIPELINE_KINDS[0]
}
