window.SettingsPage = (function () {
  const AppConfig = window.AutobotAppConfig;
  if (!AppConfig || typeof AppConfig.endpoint !== "function") {
    console.error(
      "AutobotAppConfig is missing. Settings endpoints unavailable.",
    );
    return { init() {} };
  }

  const ENDPOINTS = {
    config: AppConfig.endpoint(AppConfig.config),
  };

  const SELECTORS = {
    container: "settings-list-container",
  };

  const templates = {
    loader:
      "<span class='i i-loader pixel-rotate-animation' style='font-size:1.5rem;'></span>",
    empty: "<h2>No config found</h2>",
  };

  function getElements() {
    return {
      settingsListContainer: document.getElementById(SELECTORS.container),
    };
  }

  async function init() {
    const { settingsListContainer } = getElements();
    if (!settingsListContainer) return;

    settingsListContainer.innerHTML = templates.loader;

    let settings = [];
    try {
      settings = await fetchConfig();
    } catch (error) {
      console.error("Settings load error", error);
      settingsListContainer.innerHTML = templates.empty;
      return;
    }

    if (!Array.isArray(settings) || settings.length === 0) {
      settingsListContainer.innerHTML = templates.empty;
      return;
    }

    renderList(settingsListContainer, settings);
  }

  async function fetchConfig() {
    const response = await fetch(ENDPOINTS.config, {
      headers: { "X-Requested-With": "PageModule" },
    });
    if (!response.ok) {
      throw new Error(`Request failed: ${response.status}`);
    }
    return response.json();
  }

  function renderList(containerEl, categories) {
    containerEl.innerHTML = "";

    const fragment = document.createDocumentFragment();
    categories.forEach((category) => {
      const item = buildCategoryCard(category);
      fragment.appendChild(item);
    });

    containerEl.appendChild(fragment);
  }

  function buildCategoryCard(category) {
    const item = document.createElement("button");
    item.type = "button";
    item.className = "list-item settings-list-item";
    item.setAttribute(
      "aria-label",
      `Open ${category?.label || category?.id || "setting"}`,
    );
    item.addEventListener("click", () => navigateToDetail(category?.id));

    const content = document.createElement("div");
    content.className = "settings-list-item__content";

    const title = document.createElement("h2");
    title.textContent = category?.label || category?.id || "Unnamed setting";
    content.appendChild(title);

    const body = document.createElement("div");

    if (category?.description) {
      const desc = document.createElement("p");
      desc.className = "muted";
      desc.textContent = category.description;
      content.appendChild(desc);
    }

    const actions = document.createElement("div");
    actions.className = "list-item__actions";
    const icon = document.createElement("span");
    icon.className = "i i-chevron_right";
    icon.title = "Open";
    actions.appendChild(icon);

    item.appendChild(content);
    item.appendChild(actions);

    return item;
  }

  function navigateToDetail(categoryId) {
    if (!categoryId) return;
    window.location.href = `/settings-detail.html?id=${encodeURIComponent(categoryId)}`;
  }

  return { init };
})();
