/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        navy: {
          900: '#172554', // Deep Navy Sidebar & Branding
          800: '#1e3a8a',
          700: '#1d4ed8',
        },
        primary: {
          DEFAULT: '#4F46E5', // Primary Indigo
          dark: '#3730A3', // Dark Indigo
          light: '#EEF2FF', // Secondary Background
        },
        teal: {
          accent: '#0D9488', // Teal Accent
        },
        surface: {
          bg: '#F5F7FB', // Main Application Background
          card: '#FFFFFF', // Card Background
          sidebar: '#172554', // Sidebar Background
          header: '#F8FAFC', // Table Header Background
        },
        text: {
          primary: '#1E293B',
          secondary: '#64748B',
          muted: '#94A3B8',
        },
        status: {
          success: '#16A34A',
          'success-bg': '#DCFCE7',
          warning: '#D97706',
          'warning-bg': '#FEF3C7',
          error: '#DC2626',
          'error-bg': '#FEE2E2',
          info: '#2563EB',
          'info-bg': '#DBEAFE',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
      },
      boxShadow: {
        subtle: '0 1px 3px 0 rgba(0, 0, 0, 0.05), 0 1px 2px -1px rgba(0, 0, 0, 0.05)',
        card: '0 1px 3px 0 rgba(0, 0, 0, 0.06), 0 1px 2px -1px rgba(0, 0, 0, 0.04)',
        hover: '0 4px 6px -1px rgba(0, 0, 0, 0.08), 0 2px 4px -2px rgba(0, 0, 0, 0.06)',
      },
      borderRadius: {
        card: '12px',
        control: '8px',
      }
    },
  },
  plugins: [],
}
