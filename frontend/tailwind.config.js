/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        // Sampled directly from the store's own logo — not a generic
        // blue default. brand = the logo's sky-blue oval, gold = the
        // cart icon. Used sparingly (per spec section 46: no gradients/
        // glassmorphism, this stays professional business software).
        brand: {
          50: "#eaf6fb",
          100: "#d3ecf5",
          500: "#2e96c9",
          600: "#2483b3",
          700: "#1d6f99",
        },
        gold: {
          50: "#fdf6e3",
          400: "#f0c94d",
          500: "#e8bb00",
          600: "#c9a100",
        },
        success: "#15803d",
        danger: "#b91c1c",
        warning: "#b45309",
      },
    },
  },
  plugins: [],
};
