export const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000'

async function jfetch<T>(path: string, init?: RequestInit): Promise<T> {
    const r = await fetch(`${API_BASE}${path}`, init)
    if (!r.ok) throw new Error(`${r.status} ${r.statusText}`)
    return await r.json() as T
}

export const api = {
    // sessions
    listSessions: () => jfetch<{ sessions: any[] }>('/api/session.list'),
    createSession: (participants: string[], title = '') =>
        jfetch<{ session_id: string }>('/api/session.create', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ participants, title })
        }),
    getMessages: (sid: string) => jfetch<{ messages: any[] }>(`/api/session/${sid}/messages`),

    // settings (用于拿静态路径前缀)
    getSettings: () => jfetch<any>('/api/settings'),

    // send message (multipart/form-data)
    sendMessage: async (sid: string, sender: string, text: string, files: File[]) => {
        const fd = new FormData()
        fd.append('session_id', sid)
        fd.append('sender_id', sender)
        if (text.trim()) fd.append('text', text)
        for (const f of files) fd.append('files', f)
        const r = await fetch(`${API_BASE}/api/message.send`, { method: 'POST', body: fd })
        if (!r.ok) throw new Error(`${r.status} ${r.statusText}`)
        return await r.json()
    },

    getTimelineSlice: () => jfetch<any>('/api/timeline.slice'),
}