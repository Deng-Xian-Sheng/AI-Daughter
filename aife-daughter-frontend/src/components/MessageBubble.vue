<template>
  <div class="msg-row" :class="[side, rowTypeClass]">
    <img class="avatar" :src="avatarUrl" :alt="senderName" />
    <div class="bubble-wrap" :style="side==='right' ? 'order:-1' : ''">
      <div class="nickname" :class="{right: side==='right'}">
        {{ senderName }} <span v-if="title">（你称呼TA：{{ title }}）</span>
      </div>
      <div class="bubble" :class="[msg.type, {'no-anim': msg._noAnim}]">
        <template v-if="msg.type==='text'">
          {{ msg.text }}
        </template>
        <template v-else>
          <!-- 生成中 -->
          <div v-if="isGenLoading" class="img-gen-skeleton" role="status" aria-live="polite" aria-label="正在生成图片">
            <div class="loader">
              <!-- 图标：可换成其他，如 mdi:loading、line-md:loading-twotone-loop 等 -->
              <Icon icon="material-symbols:autorenew-rounded" width="44" height="44" class="loader-icon spin" />
            </div>
          </div>
          <!-- 生成失败 -->
          <div v-else-if="isGenError" style="width:240px;height:160px;border-radius:12px;display:flex;align-items:center;justify-content:center;background:#fff0f0;color:#b00020;">
            生成失败
          </div>
          <!-- 正常图片 -->
          <img
            v-else
            :src="imgUrl"
            @load="onImgLoad"
            @click="onPreview"
          />
        </template>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useEntitiesStore } from '../stores/entities'
import { useSessionsStore } from '../stores/sessions'
import { useUIStore } from '../stores/ui'
import { Icon } from '@iconify/vue'

const emit = defineEmits<{ (e: 'imageloaded'): void }>()
const props = defineProps<{ msg: any }>()
const entities = useEntitiesStore()
const sessions = useSessionsStore()
const ui = useUIStore()

const side = computed(() => props.msg.sender_id === 'player' ? 'right' : 'left')
const senderName = computed(() => entities.displayName(props.msg.sender_id))
const title = computed(() => entities.titleTo('player', props.msg.sender_id))

const isGenLoading = computed(() => props.msg?.meta?.kind === 'loading')
const isGenError   = computed(() => props.msg?.meta?.kind === 'gen_error')

const avatarUrl = computed(() => {
  if (props.msg.sender_id === 'agent') return '/avatar_qiqi.png'
  if (props.msg.sender_id === 'player') return '/avatar_dad.png'
  return '/avatar_npc.png'
})

const imgUrl = computed(() => {
  if (props.msg.url) return props.msg.url
  const kind = props.msg?.meta?.kind === 'generated' ? 'generated' : 'uploads'
  if (props.msg.image_id) return sessions.imageUrl(kind, props.msg.image_id)
  return ''
})

const rowTypeClass = computed(() => {
  if (props.msg.type === 'image') return 'image'         // 正常图片
  if (props.msg?.meta?.kind === 'loading') return 'image' // 生成中占位也按 image 处理
  if (props.msg?.meta?.kind === 'gen_error') return 'image'
  return 'text'
})

const isClickable = computed(() => props.msg.type === 'image' && !isGenLoading.value && !isGenError.value && !!imgUrl.value)

function onImgLoad() { emit('imageloaded') }

function onPreview() {
  if (isClickable.value) ui.openImage(imgUrl.value)
}
</script>

<style scoped>
/* 覆盖在占位动画之上的“加载中”层 */
.img-gen-skeleton .loader {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 3;              /* 高于 ::before/::after 色块云 */
  pointer-events: none;    /* 不阻止点击事件（如将来允许点击取消） */
}
.loader-icon {
  color: rgba(60, 62, 90, 0.70);
  filter: drop-shadow(0 1px 2px rgba(0,0,0,.18));
}
/* 旋转 */
.spin { animation: spin360 1.05s linear infinite; }
@keyframes spin360 { to { transform: rotate(1turn); } }
</style>