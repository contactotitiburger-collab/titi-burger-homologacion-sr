/** @type {import('tailwindcss').Config} */
export default {
  content: ['./src/**/*.{astro,html,js,jsx,md,mdx,svelte,ts,tsx,vue}'],
  theme: {
    extend: {
      fontFamily: {
        sans: [
          '-apple-system',
          'BlinkMacSystemFont',
          '"Segoe UI"',
          'Roboto',
          'Inter',
          'system-ui',
          'sans-serif',
        ],
        display: [
          '-apple-system',
          'BlinkMacSystemFont',
          '"Segoe UI"',
          'Roboto',
          'Inter',
          'system-ui',
          'sans-serif',
        ],
      },
      colors: {
        bg: 'var(--color-bg)',
        fg: 'var(--color-fg)',
        muted: 'var(--color-muted)',
        subtle: 'var(--color-subtle)',
        border: 'var(--color-border)',
        brand: 'var(--color-brand)',
        'brand-secondary': 'var(--color-brand-secondary)',
      },
      borderRadius: {
        card: 'var(--radius-card)',
        button: 'var(--radius-button)',
      },
      transitionDuration: {
        motion: 'var(--motion-duration)',
      },
      transitionTimingFunction: {
        motion: 'var(--motion-easing)',
      },
    },
  },
  plugins: [],
};
