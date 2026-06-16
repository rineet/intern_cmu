/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Space Grotesk"', 'ui-sans-serif', 'system-ui'],
      },
      boxShadow: {
        glow: '0 24px 80px rgba(2, 8, 23, 0.35)',
      },
      colors: {
        ink: {
          950: '#07111f',
        },
      },
    },
  },
  plugins: [],
}