import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import en from 'element-plus/es/locale/lang/en'
import 'element-plus/dist/index.css'
import './styles/theme.css'
import App from './App.vue'
import router from './router'
import { i18n } from './i18n'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.use(i18n)

const locale = localStorage.getItem('locale') === 'en-US' ? en : zhCn
app.use(ElementPlus, { locale })

app.mount('#app')

export function elementLocaleFor(lang: string) {
  return lang === 'en-US' ? en : zhCn
}
