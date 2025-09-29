<template>
  <div class="chat-window">
    <div class="messages" ref="scrollEl">
      <div v-if="!currMsgs.length" style="display:flex; align-items:center; justify-content:center; height: 100%; opacity:.6; font-size:14px;">
        和琪琪打个招呼吧～
      </div>
      <MessageBubble
        v-for="m in currMsgs"
        :key="m._key || m.id"
        :msg="m"
        @imageloaded="scrollToBottom"
      />
      <div v-if="aiTyping" class="msg-row left" style="opacity:.7">
        <img class="avatar" src="/avatar_qiqi.png" alt="琪琪" />
        <div class="bubble-wrap">
          <div class="nickname">琪琪</div>
        </div>
      </div>
    </div>

    <div class="composer">
      <!-- 缩略图托盘：选择即显示；发送时变“上传中…”；收到SSE后消失 -->
      <div class="attach-tray" v-if="pending.length">
        <div class="thumb" v-for="p in pending" :key="p.key">
          <img :src="p.blobURL" alt="预览" />
          <button class="x" v-if="p.status==='ready'" @click="remove(p.key)">×</button>
          <div class="overlay" v-if="p.status==='uploading'">上传中…</div>
          <div class="overlay error" v-if="p.status==='error'">上传失败</div>
        </div>
      </div>

      <textarea
        v-model="text"
        placeholder="对琪琪说点什么..."
        @keydown="onKeydown"
        @compositionstart="composing = true"
        @compositionend="composing = false"
      />
      <div class="actions">
        <input ref="fileEl" type="file" multiple accept="image/*" style="display:none" @change="onFiles"/>
        <button class="btn" @click="pickFiles" :disabled="isSending">图片</button>
        <button class="btn primary" @click="send" :disabled="isSending">发送</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick, computed } from 'vue'
import { storeToRefs } from 'pinia'
import { useSessionsStore } from '../stores/sessions'
import MessageBubble from './MessageBubble.vue'

const store = useSessionsStore()
const { currentId } = storeToRefs(store)

const text = ref('')
const fileEl = ref<HTMLInputElement|null>(null)
const scrollEl = ref<HTMLElement|null>(null)

const currMsgs = computed(() => store.messages[currentId.value] || [])
const pending = computed(() => store.pendingOfCurrent)

// 正在输入（仅文本才开）
const aiTyping = ref(false)
const isSending = ref(false)
const composing = ref(false)

watch(currMsgs, async () => {
  await nextTick(); scrollToBottom()
  const last = currMsgs.value[currMsgs.value.length - 1]
  if (last && last.sender_id === 'agent') aiTyping.value = false
}, { deep: true })

function scrollToBottom() {
  if (scrollEl.value) scrollEl.value.scrollTop = scrollEl.value.scrollHeight
}

function pickFiles(){ fileEl.value?.click() }
function onFiles(e: Event){
  const input = e.target as HTMLInputElement
  const list = input.files
  if (!list) return
  store.addPendingFiles(Array.from(list)) // 选择即加入托盘
  if (fileEl.value) fileEl.value.value = '' // 允许下次继续选择
}
function remove(key: string){ store.removePending(key) }

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey && !composing.value) { e.preventDefault(); send() }
}

async function send(){
  const t = text.value
  if (!t.trim() && pending.value.length === 0) return
  text.value = ''
  isSending.value = true
  // 文本才启动“正在输入…”，单图不显示
  if (t.trim()) aiTyping.value = true
  try {
    await store.sendWithPending(t)
  } finally {
    isSending.value = false
  }
}
</script>