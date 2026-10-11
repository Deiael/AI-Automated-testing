import { createI18n } from 'vue-i18n'
import zhCN from './locales/zh-CN'
import enUS from './locales/en-US'

export type AppLocale = 'zh-CN' | 'en-US'

const saved = (localStorage.getItem('locale') as AppLocale | null) || 'zh-CN'

export const i18n = createI18n({
  legacy: false,
  globalInjection: true,
  locale: saved === 'en-US' ? 'en-US' : 'zh-CN',
  fallbackLocale: 'zh-CN',
  messages: {
    'zh-CN': zhCN,
    'en-US': enUS,
  },
})

export function setLocale(locale: AppLocale) {
  i18n.global.locale.value = locale
  localStorage.setItem('locale', locale)
  document.documentElement.lang = locale === 'en-US' ? 'en' : 'zh-CN'
}

document.documentElement.lang = saved === 'en-US' ? 'en' : 'zh-CN'
