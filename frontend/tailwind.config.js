/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        flood: {
          critical: '#dc2626',
          high: '#ea580c',
          moderate: '#eab308',
          low: '#22c55e',
          safe: '#3b82f6',
        },
        ufie: {
          dark: '#0f172a',
          panel: '#1e293b',
          border: '#334155',
          accent: '#38bdf8',
          text: '#e2e8f0',
          muted: '#94a3b8',
        },
      },
    },
  },
  plugins: [],
}
