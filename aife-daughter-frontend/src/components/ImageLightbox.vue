<template>
  <transition name="lb" appear>
    <div v-if="open" class="lightbox" @click.self="close" title="点击空白处关闭">
      <div class="content">
        <img :src="url" alt="预览" @click.stop />
        <div class="toolbar">
          <button class="btn" :disabled="downloading" @click="download">
            {{ downloading ? '下载中…' : '下载' }}
          </button>
          <button class="btn" @click="close">关闭</button>
        </div>
      </div>
    </div>
  </transition>
</template>

<script setup lang="ts">
import { storeToRefs } from 'pinia'
import { ref } from 'vue'
import { useUIStore } from '../stores/ui'

const ui = useUIStore()
const { lightboxOpen: open, lightboxUrl: url } = storeToRefs(ui)
const close = () => ui.closeLightbox()

const downloading = ref(false)

function guessNameFromUrl(u: string) {
  try {
    const clean = u.split('?')[0].split('#')[0]
    const name = clean.split('/').pop() || 'image'
    return name.match(/\.(png|jpg|jpeg|webp|gif|bmp|tiff)$/i) ? name : name + '.png'
  } catch { return 'image.png' }
}

async function download() {
  if (!url.value || downloading.value) return
  downloading.value = true
  try {
    const res = await fetch(url.value, { mode: 'cors' })
    if (!res.ok) throw new Error(String(res.status))
    const blob = await res.blob()
    const ext = (blob.type || '').includes('png') ? 'png'
              : (blob.type || '').includes('jpeg') ? 'jpg'
              : (blob.type || '').includes('webp') ? 'webp'
              : (blob.type || '').includes('gif') ? 'gif'
              : 'png'
    const obj = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = obj
    const base = guessNameFromUrl(url.value).replace(/\.(png|jpg|jpeg|webp|gif|bmp|tiff)$/i, '')
    a.download = `${base}.${ext}`
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(obj)
  } catch (e) {
    // 退化：若 fetch 失败，尝试直接打开（少数跨域场景）
    const a = document.createElement('a')
    a.href = url.value
    a.target = '_blank'
    document.body.appendChild(a)
    a.click()
    a.remove()
  } finally {
    downloading.value = false
  }
}

window.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && ui.lightboxOpen) ui.closeLightbox()
})
</script>

<style scoped>
.lightbox {
  position: fixed; inset: 0; z-index: 999;
  background: rgba(10,10,14,.78);
  backdrop-filter: blur(2px);
  display: flex; align-items: center; justify-content: center;
  cursor: zoom-out; /* 提示可退出 */
}

/* 内容容器：用于过渡动画 */
.content {
  position: relative;
  display: flex; align-items: center; justify-content: center;
}

.lightbox img {
  max-width: 92vw; max-height: 92vh;
  border-radius: 12px;
  box-shadow: 0 16px 40px rgba(0,0,0,.35);
  cursor: default;
}

.toolbar {
  position: fixed; bottom: 24px; right: 24px;
  display: flex; gap: 10px;
}

.btn {
  padding: 9px 14px;
  border-radius: 10px;
  border: 1px solid rgba(255,255,255,.35);
  background: rgba(255,255,255,.10);
  color: #fff;
  cursor: pointer;
  backdrop-filter: blur(4px);
  font-size: 14px;           /* 两个按钮统一字号 */
  text-decoration: none;     /* 去掉下划线 */
}
.btn:disabled {
  opacity: .6; cursor: not-allowed;
}

/* 过渡：遮罩淡入，图片轻微上浮缩放 */
.lb-enter-active, .lb-leave-active {
  transition: opacity 220ms cubic-bezier(.22,.8,.22,1);
}
.lb-enter-from, .lb-leave-to { opacity: 0; }

/* 让内容本体也跟随过渡（缩放+上浮） */
.lb-enter-active .content, .lb-leave-active .content {
  transition: transform 220ms cubic-bezier(.22,.8,.22,1), opacity 220ms cubic-bezier(.22,.8,.22,1);
}
.lb-enter-from .content, .lb-leave-to .content {
  transform: translateY(8px) scale(.98);
  opacity: .92;
}
</style>