import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // MINIMAL DESIGN SYSTEM - ONE PRIMARY ACCENT COLOR
        // Deep Blue - calm, focused, medical professionalism
        accent: {
          DEFAULT: '#4169E1', // Royal Blue - main accent
          light: '#5B7FE8',
          dark: '#2E4FA8',
        },
        // Semantic colors - only used when necessary
        success: '#10b981',
        error: '#ef4444',
        // Gray scale for hierarchy - CRITICAL for minimalism
        gray: {
          50: '#fafafa',
          100: '#f4f4f5',
          200: '#e4e4e7',
          300: '#d4d4d8',
          400: '#a1a1aa',
          500: '#71717a',
          600: '#52525b',
          700: '#3f3f46',
          800: '#27272a',
          900: '#18181b',
          950: '#09090b',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        serif: ['Cormorant', 'Georgia', 'serif'],
      },
      // STRICT SPACING SCALE - 8px base
      spacing: {
        '1': '0.25rem',  // 4px
        '2': '0.5rem',   // 8px
        '3': '0.75rem',  // 12px
        '4': '1rem',     // 16px
        '5': '1.25rem',  // 20px
        '6': '1.5rem',   // 24px
        '8': '2rem',     // 32px
        '10': '2.5rem',  // 40px
        '12': '3rem',    // 48px
        '16': '4rem',    // 64px
        '20': '5rem',    // 80px
        '24': '6rem',    // 96px
      },
      // TYPOGRAPHY SCALE - 4 sizes maximum
      fontSize: {
        'sm': ['0.875rem', { lineHeight: '1.5' }],     // 14px - small text
        'base': ['1rem', { lineHeight: '1.5' }],       // 16px - body
        'lg': ['1.125rem', { lineHeight: '1.5' }],     // 18px - emphasis
        'xl': ['1.5rem', { lineHeight: '1.3' }],       // 24px - headings
        '2xl': ['2rem', { lineHeight: '1.2' }],        // 32px - large headings
        '4xl': ['3rem', { lineHeight: '1.1' }],        // 48px - hero text
      },
      // MINIMAL BORDER RADIUS
      borderRadius: {
        'none': '0',
        'sm': '0.25rem',    // 4px
        'DEFAULT': '0.5rem', // 8px
        'lg': '0.75rem',    // 12px
        'full': '9999px',
      },
      // SUBTLE SHADOWS - minimal, not flashy
      boxShadow: {
        'sm': '0 1px 2px 0 rgba(0, 0, 0, 0.3)',
        'DEFAULT': '0 2px 4px 0 rgba(0, 0, 0, 0.4)',
        'lg': '0 4px 8px 0 rgba(0, 0, 0, 0.5)',
      },
      // SUBTLE ANIMATIONS - understated
      animation: {
        'fade-in': 'fadeIn 200ms ease-out',
        'slide-up': 'slideUp 200ms ease-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { transform: 'translateY(4px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
      },
      // REMOVE gradients - too flashy for minimal design
    },
  },
  plugins: [],
};

export default config;
