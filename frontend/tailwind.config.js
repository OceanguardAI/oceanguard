module.exports = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Manrope', 'system-ui', 'sans-serif'],
        display: ['Sora', 'system-ui', 'sans-serif'],
      },
      colors: {
        ocean: {
          950: "#020617",
          900: "#0B1F3A",
          800: "#0F2A4A",
          700: "#1A3A5C",
          600: "#1E4976",
          500: "#255B8A",
        },
        teal: {
          300: "#40C0C3",
          400: "#25A5A8",
          500: "#1E8A8C",
          600: "#17737A",
        },
        risk: {
          low:      "#22c55e",
          medium:   "#fbbf24",
          high:     "#f97316",
          critical: "#dc2626",
        },
      },
      keyframes: {
        aurora: {
          '0%, 100%': { backgroundPosition: '0% 50%' },
          '50%':       { backgroundPosition: '100% 50%' },
        },
        'glow-pulse': {
          '0%, 100%': { boxShadow: '0 0 6px rgba(37,165,168,0.3)' },
          '50%':       { boxShadow: '0 0 20px rgba(37,165,168,0.6), 0 0 40px rgba(37,165,168,0.15)' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%':       { transform: 'translateY(-10px)' },
        },
        shimmer: {
          '0%':   { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition:  '200% 0' },
        },
      },
      animation: {
        aurora:       'aurora 10s ease infinite',
        'glow-pulse': 'glow-pulse 2.5s ease-in-out infinite',
        float:        'float 5s ease-in-out infinite',
        shimmer:      'shimmer 2s linear infinite',
      },
      backgroundSize: {
        '300%': '300%',
        '200%': '200%',
      },
    },
  },
  plugins: [],
};
