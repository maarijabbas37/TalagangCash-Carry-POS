/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        // Neutral background + strong contrast + consistent primary,
        // per spec section 46. No gradients/glassmorphism.
        brand: {
          50: "#eff6ff",
          600: "#1d4ed8",
          700: "#1e40af",
        },
        success: "#15803d",
        danger: "#b91c1c",
        warning: "#b45309",
      },
    },
  },
  plugins: [],
};
