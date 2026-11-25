import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const base = '/misecundaria7/'

export default defineConfig({
  plugins: [react()],
  root: '.',
  base,
  server: {
    port: 5173,
  },
  test: {
    environment: 'jsdom',
    globals: true,
  },
})
