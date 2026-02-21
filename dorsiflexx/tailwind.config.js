/** @type {import('tailwindcss').Config} */
module.exports = {
  // NOTE: Update this to include the paths to all files that contain Nativewind classes.
  content: ["./app/**/*.{js,jsx,ts,tsx}", "./components/**/*.{js,jsx,ts,tsx}"],
  presets: [require("nativewind/preset")],
  theme: {
    extend: {
      colors: {
        brand: {
          "purple-dark": "#8d44bc",
          "purple-medium": "#dca5ff",
          "purple-light": "#faf3ff",
          orange: "#FF7A28",
          grey: "#bfbfbf",
        },
      },
    },
  },
  plugins: [],
};
