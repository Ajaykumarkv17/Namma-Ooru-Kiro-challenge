import type { Config } from 'tailwindcss';

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        maroon: '#6D1B2B',
        ochre: '#B95C17',
        gold: '#C88A18',
        teal: '#075F63',
        sand: '#F6F0E5',
        ink: '#1F1A17',
      },
      fontFamily: {
        display: ['Georgia', 'serif'],
      },
    },
  },
  plugins: [],
} satisfies Config;
