import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'

const app = createApp(App)
app.use(createPinia())
app.mount('#app')

// 背景几何形状生成（轻量、安全）
function spawnShapes() {
    const layer = document.querySelector('.bg-layer') as HTMLElement | null
    if (!layer) return
    if ((layer as any).dataset.spawned === '1') return  // 避免热更新重复插入
        ; (layer as any).dataset.spawned = '1'

    // 尊重“减少动效”偏好
    if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) return

    const colors = [
        'linear-gradient(135deg, rgba(255,210,126,.45), rgba(255,232,168,.45))',
        'linear-gradient(135deg, rgba(179,229,255,.45), rgba(207,217,255,.45))',
        'linear-gradient(135deg, rgba(226,183,255,.45), rgba(199,191,255,.45))',
        'linear-gradient(135deg, rgba(255,250,241,.45), rgba(255,232,204,.45))'
    ]
    const types = ['circle', 'square', 'diamond', 'triangle']
    const COUNT = 12  // 如需更轻，调小

    for (let i = 0; i < COUNT; i++) {
        const s = document.createElement('span')
        s.className = 'shape'
        const t = types[Math.floor(Math.random() * types.length)]
        s.dataset.t = t
        const size = Math.floor(80 + Math.random() * 140)
        const left = Math.random() * 100
        const top = Math.random() * 100

        s.style.setProperty('--s', size + 'px')
        s.style.width = size + 'px'
        s.style.height = size + 'px'
        s.style.left = `calc(${left}vw - ${size / 2}px)`
        s.style.top = `calc(${top}vh - ${size / 2}px)`
        s.style.background = colors[Math.floor(Math.random() * colors.length)]
        s.style.setProperty('--dur', (14 + Math.random() * 12) + 's')
        s.style.setProperty('--rot', (18 + Math.random() * 16) + 's')
        s.style.opacity = (0.12 + Math.random() * 0.14).toFixed(2)
        layer.appendChild(s)
    }
}

spawnShapes()