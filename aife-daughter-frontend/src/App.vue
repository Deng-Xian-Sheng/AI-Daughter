<template>
  <div class="page">
    <section class="chat-card" role="region" aria-label="聊天窗口">
      <HeaderBar />
      <div class="chat-body">
        <TimelineBar />
        <div class="main-area">
          <SessionTabs />
          <ChatWindow />
        </div>
      </div>
    </section>
  </div>
  <!-- 全局图片预览 -->
  <ImageLightbox />
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useSessionsStore } from './stores/sessions'
import HeaderBar from './components/HeaderBar.vue'
import TimelineBar from './components/TimelineBar.vue'
import SessionTabs from './components/SessionTabs.vue'
import ChatWindow from './components/ChatWindow.vue'
import ImageLightbox from './components/ImageLightbox.vue'

const sessions = useSessionsStore()
onMounted(() => {
  sessions.bootstrap()
})
</script>