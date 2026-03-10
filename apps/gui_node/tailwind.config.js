/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        lucid: {
          primary: '#3B82F6',
          secondary: '#1E40AF',
          accent: '#F59E0B',
          success: '#10B981',
          warning: '#F59E0B',
          error: '#EF4444',
          background: '#F8FAFC',
          surface: '#FFFFFF',
          text: '#1F2937',
          'text-secondary': '#6B7280',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
