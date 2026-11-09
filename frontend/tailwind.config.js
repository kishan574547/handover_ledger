/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: '#F8FAFC',
        navy: {
          DEFAULT: '#1F3864',
          hover: '#2A4B85',
          dark: '#142544',
          light: '#28477D',
        },
        teal: {
          DEFAULT: '#0F766E',
          hover: '#115E59',
          light: '#CCFBF1',
        },
        text: {
          main: '#0F172A',
          muted: '#64748B',
        },
        status: {
          verified: {
            text: '#15803D',
            bg: '#DCFCE7',
            border: '#86EFAC',
          },
          inferred: {
            text: '#B45309',
            bg: '#FEF3C7',
            border: '#FCD34D',
          },
          conflicting: {
            text: '#B91C1C',
            bg: '#FEE2E2',
            border: '#FCA5A5',
          },
          missing: {
            text: '#475569',
            bg: '#E2E8F0',
            border: '#CBD5E1',
          },
          leaver: {
            text: '#6D28D9',
            bg: '#EDE9FE',
            border: '#C4B5FD',
          },
        },
        clearance: {
          general: '#16A34A',
          technical: '#2563EB',
          confidential: '#DC2626',
        }
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      borderRadius: {
        card: '12px',
      },
      boxShadow: {
        soft: '0 1px 3px 0 rgba(0, 0, 0, 0.05), 0 1px 2px 0 rgba(0, 0, 0, 0.03)',
        card: '0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03)',
      }
    },
  },
  plugins: [],
}
