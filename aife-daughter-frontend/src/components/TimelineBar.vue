<template>
  <div class="timeline-bar" v-if="slice">
    <div>
      <strong>时间线</strong> · 第{{ slice.now?.day }}天 {{ slice.now?.weekday }} {{ slice.now?.time_of_day }}
      ｜ {{ slice.environment?.city }} · {{ slice.environment?.weather }} · {{ slice.environment?.temp }}
      <span v-if="slice.beats?.length"> ｜ 事件：{{ slice.beats.map((b:any)=>b.id).join('、') }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { storeToRefs } from 'pinia'
import { useSessionsStore } from '../stores/sessions'
const store = useSessionsStore()
const { timelineSlice: slice } = storeToRefs(store)
</script>