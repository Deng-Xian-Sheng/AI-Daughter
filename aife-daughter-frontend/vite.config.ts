import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 如果需要跨域代理（比如不同域名），可开启 server.proxy
export default defineConfig({
    plugins: [vue()],
})