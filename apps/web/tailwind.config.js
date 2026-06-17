/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: [
          "-apple-system",
          "BlinkMacSystemFont",
          "'PingFang SC'",
          "'Microsoft YaHei'",
          "system-ui",
          "sans-serif",
        ],
      },
    },
  },
  plugins: [],
};
