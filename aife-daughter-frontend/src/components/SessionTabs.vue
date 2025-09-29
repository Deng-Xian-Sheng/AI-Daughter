<template>
  <div class="tabs-panel">
    <div
      v-for="s in sessions"
      :key="s.id"
      class="tab-item"
      :class="{active: s.id===currentId}"
      @click="switchTo(s.id)"
    >
      <span>{{ labelOf(s) }}</span>
      <span v-if="s.unread_count>0" class="tab-dot"></span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { storeToRefs } from 'pinia'
import { useSessionsStore } from '../stores/sessions'

const store = useSessionsStore()
const { sessions, currentId } = storeToRefs(store)

function switchTo(id: string){
  store.switchSession(id)
}

function labelOf(s: any) {
  if (s.title) return s.title
  // 简单标签：根据 participants
  if (Array.isArray(s.participants)) {
    if (s.participants.includes('player') && s.participants.includes('agent')) return '和琪琪'
  }
  return '会话'
}
</script>