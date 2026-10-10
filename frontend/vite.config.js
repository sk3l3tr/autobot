import { defineConfig } from "vite";
import { resolve } from "node:path";

export default defineConfig({
  appType: "mpa",
  build: {
    rollupOptions: {
      input: {
        index: resolve(__dirname, "index.html"),
        schedules: resolve(__dirname, "schedules.html"),
        scheduleDetail: resolve(__dirname, "schedule-detail.html"),
        settings: resolve(__dirname, "settings.html"),
        settingsDetail: resolve(__dirname, "settings-detail.html"),
      },
    },
  },
});
