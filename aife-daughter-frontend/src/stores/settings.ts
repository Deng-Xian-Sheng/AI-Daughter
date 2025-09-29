import { defineStore } from 'pinia'
import { api } from '../api'

export const useSettingsStore = defineStore('settings', {
    state: () => ({
        staticPrefix: '/static/images',
    }),
    actions: {
        async load() {
            try {
                const data = await api.getSettings()
                this.staticPrefix = data.image_transport?.static_path_prefix || '/static/images'
            } catch (e) {
                console.warn('settings load failed', e)
            }
        },
        imageUrl(kind: 'uploads' | 'generated', imageId: string) {
            const base = import.meta.env.VITE_API_BASE || ''
            const prefix = this.staticPrefix || '/static/images'
            return `${base}${prefix}/${kind}/${imageId}.png`
        }
    }
})