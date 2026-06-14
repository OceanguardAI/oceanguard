module.exports = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ocean: {
          900: "#0B1F3A",
          800: "#0F2A4A",
          700: "#1A3A5C",
        },
        teal: {
          500: "#1E8A8C",
          400: "#25A5A8",
        },
        risk: {
          low:      "#22c55e",
          medium:   "#fbbf24",
          high:     "#f97316",
          critical: "#dc2626",
        },
      },
    },
  },
  plugins: [],
};
