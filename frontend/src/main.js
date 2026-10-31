import { bootstrapDemiurge } from "@sk3l3tr/demiurgejs";
import "@sk3l3tr/demiurgejs/style.css";

window.PageConfig = {
  layout: {
    header: {
      selector: "#app-header",
      url: "/partials/header.html",
    },
    footer: {
      selector: "#app-footer",
      url: "/partials/footer.html",
    },
    navSelector: "#menu a[href]",
  },
  sharedScripts: ["/scripts/shared/close.js"],
  pages: {
    index: { scripts: ["/scripts/pages/index.js"], init: "IndexPage.init" },
    schedules: {
      scripts: ["/scripts/pages/schedules.js"],
      init: "SchedulesPage.init",
    },
    "schedule-detail": {
      scripts: ["/scripts/pages/schedule-detail.js"],
      init: "ScheduleDetailPage.init",
    },
    settings: {
      scripts: ["/scripts/pages/settings.js"],
      init: "SettingsPage.init",
    },
    "settings-detail": {
      scripts: ["/scripts/pages/settings-detail.js"],
      init: "SettingsDetailPage.init",
    },
  },
};

bootstrapDemiurge();
