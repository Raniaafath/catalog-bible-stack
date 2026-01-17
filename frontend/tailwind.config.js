/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"] ,
  theme: {
    extend: {
      colors: {
        ink: {
          50: "#f5f6f7",
          100: "#e1e4e8",
          200: "#c3c9d1",
          300: "#9aa3ad",
          400: "#7a8591",
          500: "#5f6873",
          600: "#4a515a",
          700: "#363b42",
          800: "#25292e",
          900: "#171a1e"
        },
        clay: {
          50: "#f8f4f0",
          100: "#efe6db",
          200: "#e0cbb8",
          300: "#cfae92",
          400: "#b98f6c",
          500: "#a07857",
          600: "#7f6047",
          700: "#5f4838",
          800: "#3f3128",
          900: "#2a211b"
        }
      },
      fontFamily: {
        display: ["\"Space Grotesk\"", "sans-serif"],
        body: ["\"IBM Plex Sans\"", "sans-serif"]
      },
      boxShadow: {
        card: "0 10px 30px rgba(15, 23, 42, 0.12)",
        soft: "0 6px 18px rgba(15, 23, 42, 0.08)"
      }
    }
  },
  plugins: []
};
