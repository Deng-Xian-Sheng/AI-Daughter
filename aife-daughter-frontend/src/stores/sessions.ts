import { defineStore } from 'pinia'
import { api, API_BASE } from '../api'

type Msg = {
    id: string
    session_id: string
    sender_id: string
    type: 'text' | 'image'
    text?: string
    image_id?: string
    url?: string
    created_at?: string
    meta?: any
    _ephemeral?: boolean
    _noAnim?: boolean
    _key?: string
    _blobURL?: string
}

type PendingItem = {
    key: string
    file: File
    blobURL: string
    status: 'ready' | 'uploading' | 'done' | 'error'
}

function uid() {
    return 'pv-' + Math.random().toString(36).slice(2, 10) + Date.now().toString(36)
}

export const useSessionsStore = defineStore('sessions', {
    state: () => ({
        sessions: [] as any[],
        currentId: '' as string,
        messages: {} as Record<string, Msg[]>,
        sse: null as EventSource | null,
        timelineSlice: null as any,
        staticPrefix: '/static/images',
        pending: {} as Record<string, PendingItem[]>,      // 每会话的缩略图托盘
        uploadQueue: {} as Record<string, string[]>,       // 正在上传的key队列（用于与SSE对齐）
        genLoaders: {} as Record<string, string[]> // 每会话的“生成中占位”key队列
    }),
    getters: {
        pendingOfCurrent(state): PendingItem[] {
            return state.pending[state.currentId] || []
        }
    },
    actions: {
        async bootstrap() {
            try {
                const set = await api.getSettings()
                this.staticPrefix = set.image_transport?.static_path_prefix || '/static/images'
            } catch { }
            const data = await api.listSessions()
            this.sessions = data.sessions || []
            if (this.sessions.length === 0) {
                const created = await api.createSession(['player', 'agent'], '')
                await this.refreshSessions()
                this.currentId = created.session_id
            } else {
                this.currentId = this.sessions[0].id
            }
            await this.loadMessages(this.currentId)
            // 初始时间线（刷新后也有）
            try { this.timelineSlice = await api.getTimelineSlice() } catch { }
            this.connectSSE(this.currentId)
        },
        async refreshSessions() {
            const data = await api.listSessions()
            this.sessions = data.sessions || []
        },
        async loadMessages(sid) {
            const data = await api.getMessages(sid)
            this.messages[sid] = data.messages || []
            this.pending[sid] = this.pending[sid] || []
            this.uploadQueue[sid] = this.uploadQueue[sid] || []
            this.genLoaders[sid] = this.genLoaders[sid] || []
        },
        switchSession(sid: string) {
            if (this.currentId === sid) return
            this.currentId = sid
            this.loadMessages(sid)
            this.connectSSE(sid)
        },
        connectSSE(sid: string) {
            if (this.sse) { this.sse.close(); this.sse = null }
            const es = new EventSource(`${API_BASE}/api/stream/${sid}`)
            es.onmessage = (ev) => {
                const data = JSON.parse(ev.data)
                const arr = this.messages[sid] ||= []
                this.pending[sid] ||= []
                this.uploadQueue[sid] ||= []
                this.genLoaders[sid] ||= []

                switch (data.type) {
                    case 'message_new': {
                        const m = data.message as any
                        // 生成完成：用真正图片替换最近的“生成中”占位
                        if (m.sender_id === 'agent' && m.type === 'image' && m.meta?.kind === 'generated') {
                            const key = this.genLoaders[sid].shift()
                            if (key) {
                                const idx = arr.findIndex(x => (x._key || x.id) === key)
                                if (idx >= 0) {
                                    const old = arr[idx]
                                    arr[idx] = {
                                        id: m.id, _key: key, session_id: sid, sender_id: 'agent',
                                        type: 'image', image_id: m.image_id, meta: { kind: 'generated' }, _noAnim: true
                                    }
                                    break
                                }
                            }
                        }
                        // 玩家上传图片：替换托盘的“上传中”项（你之前的逻辑保留）
                        if (m.sender_id === 'player' && m.type === 'image' && m.meta?.kind === 'uploads') {
                            const upKey = this.uploadQueue[sid].shift()
                            if (upKey) {
                                const pIdx = this.pending[sid].findIndex(p => p.key === upKey)
                                if (pIdx >= 0) {
                                    URL.revokeObjectURL(this.pending[sid][pIdx].blobURL)
                                    this.pending[sid].splice(pIdx, 1)
                                    arr.push(m)
                                    break
                                }
                            }
                        }
                        // 其他消息直接追加
                        arr.push(m)
                        break
                    }
                    case 'timeline_hint': {
                        this.timelineSlice = data.slice
                        break
                    }
                    case 'text_start': {
                        const mid = data.temp_id as string
                        arr.push({
                            id: mid, _key: mid,
                            session_id: sid, sender_id: 'agent',
                            type: 'text',
                            text: '正在输入…',     // 关键：先显示文案
                            _typing: true,         // 标记首段到来时要清空
                            _ephemeral: true, _noAnim: true
                        })
                        break
                    }
                    case 'text_delta': {
                        const mid = data.temp_id as string
                        const delta = data.delta as string
                        const m = arr.find(x => (x._key || x.id) === mid)
                        if (m) {
                            if ((m as any)._typing) {
                                m.text = ''          // 第一段到来先清掉“正在输入…”
                                    ; (m as any)._typing = false
                            }
                            m.text = (m.text || '') + delta
                        }
                        break
                    }
                    case 'text_done': {
                        const mid = data.temp_id as string
                        const finalId = data.final_id as string
                        const full = data.text as string
                        const m = arr.find(x => (x._key || x.id) === mid)
                        if (m) {
                            m.id = finalId
                            m.text = full
                            m._ephemeral = false
                            m._noAnim = true
                                ; (m as any)._typing = false
                        } else {
                            arr.push({
                                id: finalId, _key: mid,
                                session_id: sid, sender_id: 'agent',
                                type: 'text', text: full, _noAnim: true
                            })
                        }
                        break
                    }
                    case 'image_task_queued': {
                        // 插入“生成中”占位
                        const key = 'gen-' + Math.random().toString(36).slice(2, 8) + Date.now().toString(36)
                        arr.push({
                            id: key, _key: key, session_id: sid, sender_id: 'agent',
                            type: 'image', meta: { kind: 'loading' }, _ephemeral: true, _noAnim: true
                        })
                        this.genLoaders[sid].push(key)
                        break
                    }
                    case 'image_task_done': {
                        if (data.status === 'FAILED') {
                            const key = this.genLoaders[sid].shift()
                            if (key) {
                                const idx = arr.findIndex(x => (x._key || x.id) === key)
                                if (idx >= 0) {
                                    arr[idx].meta = { kind: 'gen_error' }
                                    arr[idx]._noAnim = true
                                }
                            }
                        }
                        break
                    }
                }
            }
            this.sse = es
        },
        imageUrl(kind: 'uploads' | 'generated', imageId: string) {
            const base = import.meta.env.VITE_API_BASE || ''
            return `${base}${this.staticPrefix}/${kind}/${imageId}.png`
        },

        // 选择文件：加入托盘，尚未上传
        addPendingFiles(files: File[]) {
            const sid = this.currentId
            this.pending[sid] = this.pending[sid] || []
            for (const f of files) {
                const key = uid()
                const blobURL = URL.createObjectURL(f)
                this.pending[sid].push({ key, file: f, blobURL, status: 'ready' })
            }
        },
        // 删除托盘项（仅允许 ready/ error）
        removePending(key: string) {
            const sid = this.currentId
            const idx = (this.pending[sid] || []).findIndex(p => p.key === key)
            if (idx >= 0) {
                const item = this.pending[sid][idx]
                if (item.status === 'uploading') return
                URL.revokeObjectURL(item.blobURL)
                this.pending[sid].splice(idx, 1)
            }
        },

        // 发送：把托盘中 ready 的文件上传；文本一起发
        async sendWithPending(text: string) {
            const sid = this.currentId
            const ready = (this.pending[sid] || []).filter(p => p.status === 'ready')
            const files = ready.map(p => p.file)

            // 标记上传中 + 构建队列（用于与SSE对齐，保证顺序一致）
            for (const p of ready) {
                p.status = 'uploading'
                this.uploadQueue[sid] = this.uploadQueue[sid] || []
                this.uploadQueue[sid].push(p.key)
            }

            try {
                await api.sendMessage(sid, 'player', text, files)
            } catch (e) {
                // 标记失败
                for (const p of ready) p.status = 'error'
                console.error('sendWithPending failed', e)
            }
        },

        async sendText(text: string) {
            await api.sendMessage(this.currentId, 'player', text, [])
        },
    }
})