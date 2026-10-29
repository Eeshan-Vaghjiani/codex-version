import react from '@vitejs/plugin-react'
import {
  defineConfig,
  loadEnv,
} from 'vite'

export default defineConfig(({ command, mode }) => {
  const env = loadEnv(mode, process.cwd(), '')

  // A production build must know where the backend is.
  // Without this check the built site would silently
  // call http://127.0.0.1:8000 on each visitor's own
  // computer.
  if (
    command === 'build' &&
    !env.VITE_API_BASE_URL
  ) {
    throw new Error(
      'VITE_API_BASE_URL is not set. Set it to the backend URL ' +
        'before running "npm run build", for example in a .env ' +
        'file: VITE_API_BASE_URL=https://your-backend.example.com',
    )
  }

  return {
    plugins: [react()],

    test: {
      environment: 'jsdom',
      setupFiles: './src/test/setup.js',
    },
  }
})
