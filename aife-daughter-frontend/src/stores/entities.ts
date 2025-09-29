import { defineStore } from 'pinia'

export const useEntitiesStore = defineStore('entities', {
    state: () => ({
        names: {
            player: '爸爸',
            agent: '琪琪'
        } as Record<string, string>,
        titles: {
            'player->agent': '琪琪',
            'agent->player': '爸爸'
        } as Record<string, string>
    }),
    getters: {
        displayName: (s) => (id: string) => s.names[id] || id,
        titleTo: (s) => (subjectId: string, objectId: string) => {
            return s.titles[`${subjectId}->${objectId}`] || ''
        }
    }
})