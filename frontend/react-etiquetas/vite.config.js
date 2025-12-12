import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

<<<<<<< HEAD
export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      external: []  // No externalizar ningún módulo
    }
  }
})
=======
// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
})
>>>>>>> 3b04a0c025c3742bd0fbc5d967031b0d610c09f8
