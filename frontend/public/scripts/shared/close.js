(function () {
  const AppConfig = window.AutobotAppConfig;
  if (!AppConfig || typeof AppConfig.endpoint !== "function") {
    console.error("AutobotAppConfig is missing. Close control disabled.");
    return;
  }

  const ENDPOINT = AppConfig.endpoint(AppConfig.action);
  const btnEl = document.getElementById("close_btn");
  const payload = {
    action: "kill",
    kwargs: {},
  };

  async function kill() {
    fetch(ENDPOINT, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    }).catch((err) => console.error("Kill Error:", err));
  }

  function init() {
    btnEl.addEventListener("click", kill);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  } else {
    init();
  }
})();
