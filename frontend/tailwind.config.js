/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: 'var(--color-bg)',
        surface: {
          DEFAULT: 'var(--color-surface)',
          hover: 'var(--color-surface-hover)',
        },
        border: 'var(--color-border)',
        navy: {
          DEFAULT: 'var(--color-primary)',
          hover: 'var(--color-primary-hover)',
          dark: 'var(--color-sidebar)',
          light: 'var(--color-primary-light)',
        },
        sidebar: 'var(--color-sidebar)',
        teal: {
          DEFAULT: 'var(--color-accent)',
          hover: 'var(--color-accent-hover)',
          light: 'var(--color-accent-light)',
        },
        text: {
          main: 'var(--color-text)',
          muted: 'var(--color-muted)',
        },
        status: {
          verified: {
            text: 'var(--status-verified-text)',
            bg: 'var(--status-verified-bg)',
            border: 'var(--status-verified-border)',
          },
          inferred: {
            text: 'var(--status-inferred-text)',
            bg: 'var(--status-inferred-bg)',
            border: 'var(--status-inferred-border)',
          },
          conflicting: {
            text: 'var(--status-conflicting-text)',
            bg: 'var(--status-conflicting-bg)',
            border: 'var(--status-conflicting-border)',
          },
          missing: {
            text: 'var(--status-missing-text)',
            bg: 'var(--status-missing-bg)',
            border: 'var(--status-missing-border)',
          },
          leaver: {
            text: 'var(--status-leaver-text)',
            bg: 'var(--status-leaver-bg)',
            border: 'var(--status-leaver-border)',
          },
        },
        clearance: {
          general: 'var(--clearance-general)',
          technical: 'var(--clearance-technical)',
          confidential: 'var(--clearance-confidential)',
        }
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      borderRadius: {
        card: '12px',
        btn: '10px',
      },
      zIndex: {
        'content': '1',
        'sticky-bar': '20',
        'floating': '30',
        'sidebar': '40',
        'drawer': '45',
        'modal': '50',
        'toast': '60',
      },
      boxShadow: {
        soft: 'var(--shadow-soft)',
        card: 'var(--shadow-card)',
      }
    },
  },
  plugins: [],
}
