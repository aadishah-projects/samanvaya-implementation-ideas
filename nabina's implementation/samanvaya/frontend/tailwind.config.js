/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        panel: '#0b1220',
        panelSoft: '#111a2e',
        ink: '#e5eefb',
        muted: '#8fa3c4',
        green: '#2fd27b',
        yellow: '#f7c948',
        red: '#ef4d4d',
        accent: '#67b7ff',
      },
      boxShadow: {
        glow: '0 20px 60px rgba(3, 13, 33, 0.55)',
      },
      backgroundImage: {
        dashboard: 'radial-gradient(circle at top left, rgba(103,183,255,0.18), transparent 28%), radial-gradient(circle at top right, rgba(47,210,123,0.12), transparent 28%), linear-gradient(135deg, #08111f 0%, #0e1730 55%, #0a101b 100%)',
      },
    },
  },
  plugins: [],
};