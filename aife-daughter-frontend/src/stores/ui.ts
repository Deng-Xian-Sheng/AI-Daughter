import { defineStore } from 'pinia'

export const useUIStore = defineStore('ui', {
    state: () => ({
        lightboxOpen: false,
        lightboxUrl: '' as string
    }),
    actions: {
        openImage(url: string) {
            if (!url) return
            this.lightboxUrl = url
            this.lightboxOpen = true
            document.body.style.overflow = 'hidden'
        },
        closeLightbox() {
            this.lightboxOpen = false
            this.lightboxUrl = ''
            document.body.style.overflow = ''
        }
    }
})