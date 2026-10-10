window.SchedulesPage = (function () {
  const AppConfig = window.AutobotAppConfig;
  if (!AppConfig || typeof AppConfig.endpoint !== "function") {
    console.error("AutobotAppConfig is missing. Schedule module disabled.");
    return { init() {} };
  }

  const ENDPOINTS = {
    schedule: AppConfig.endpoint(AppConfig.schedule),
  };

  const SELECTORS = {
    container: "schedules-list-container",
    list: "schedule-list",
  };

  const state = {
    schedules: [],
  };

  const templates = {
    loader:
      "<span class='i i-loader pixel-rotate-animation' style='font-size:1.5rem;'></span>",
    empty: "<h2>No schedules found</h2>",
    shell: () => `
        <div style='display:flex;align-items:center;justify-content:space-between;'>
          <span id="schedule-add-btn" class='primary i i-add_box' title='Add' style='font-size:1.5rem; cursor:pointer;'></span>
          <h2 class='primary text-end'>LIST</h2>
        </div>
        <div id='${SELECTORS.list}'></div>
      `,
    item: (schedule) => {
      const safeId = toDomId(schedule.id);
      const popoverId = `schedule_${safeId}_menu`;
      const summary = buildScheduleSummary(schedule);
      return `
        <div class="list-item" data-schedule-id="${escapeHtml(schedule.id)}">
          <div>
            <h2>${escapeHtml(schedule.id)}</h2>
            <p class="muted" style="margin:0;">${summary}</p>
          </div>
          <div class="list-item__actions">
            <button popovertarget="${popoverId}" class="popover-anchor" data-schedule-id="${escapeHtml(schedule.id)}">
              <span class="i i-script_text" title="Options"></span>
            </button>
          </div>
        </div>
        <div popover id="${popoverId}" class="popover-menu" data-schedule-id="${escapeHtml(schedule.id)}">
          <div style="display:flex; flex-direction: column;">
            <span class="i i-script_text" data-action="edit" data-schedule-id="${escapeHtml(schedule.id)}" title="Edit"></span>
            <span class="i i-trash" data-action="delete" data-schedule-id="${escapeHtml(schedule.id)}" title="Delete"></span>
          </div>
        </div>
      `;
    },
  };

  const elements = {
    container: null,
  };

  const api = {
    async list() {
      return safeFetch(ENDPOINTS.schedule) ?? [];
    },
    async remove(id) {
      return (
        safeFetch(`${ENDPOINTS.schedule}/${encodeURIComponent(id)}`, {
          method: "DELETE",
          headers: { "Content-Type": "application/json" },
        }) ?? []
      );
    },
  };

  async function init() {
    cacheElements();
    if (!elements.container) return;
    renderLoader();
    await loadSchedules();
  }

  function cacheElements() {
    elements.container = document.getElementById(SELECTORS.container);
  }

  async function loadSchedules() {
    try {
      state.schedules = await api.list();
      renderScheduleList();
    } catch (error) {
      console.error(error);
      elements.container.innerHTML = templates.empty;
    }
  }

  function renderLoader() {
    elements.container.innerHTML = templates.loader;
  }

  function renderScheduleList() {
    elements.container.innerHTML = templates.shell();
    const listEl = elements.container.querySelector(`#${SELECTORS.list}`);
    if (!listEl) return;

    if (!state.schedules.length) {
      listEl.innerHTML = templates.empty;
      bindAddButton();
      return;
    }

    const fragment = document.createDocumentFragment();
    state.schedules.forEach((schedule) => {
      const template = document.createElement("template");
      template.innerHTML = templates.item(schedule);
      fragment.appendChild(template.content);
    });

    listEl.appendChild(fragment);
    bindAddButton();
    bindListEvents(listEl);
  }

  function bindAddButton() {
    const addBtn = elements.container.querySelector("#schedule-add-btn");
    if (!addBtn) return;
    addBtn.addEventListener("click", () => navigateToDetail());
  }

  function bindListEvents(listEl) {
    listEl.addEventListener("click", async (event) => {
      const actionEl = event.target.closest("[data-action]");
      if (!actionEl) return;
      const scheduleId = actionEl.getAttribute("data-schedule-id");
      if (!scheduleId) return;

      const action = actionEl.getAttribute("data-action");
      if (action === "edit") {
        navigateToDetail(scheduleId);
      }

      if (action === "delete") {
        await handleDelete(scheduleId);
      }
    });
  }

  async function handleDelete(scheduleId) {
    if (!scheduleId) return;
    if (!window.confirm(`Delete schedule "${scheduleId}"?`)) return;

    try {
      renderLoader();
      state.schedules = await api.remove(scheduleId);
      renderScheduleList();
    } catch (error) {
      console.error("Delete schedule error", error);
      alert("Failed to delete schedule. Check the console for details.");
      renderScheduleList();
    }
  }

  function navigateToDetail(id) {
    const target = id
      ? `/schedule-detail.html?id=${encodeURIComponent(id)}`
      : "/schedule-detail.html";
    window.location.href = target;
  }

  function buildScheduleSummary(schedule) {
    const trigger = schedule.trigger || "unknown";
    if (trigger === "interval") {
      const parts = [];
      if (schedule.days) parts.push(`${schedule.days}d`);
      if (schedule.hours) parts.push(`${schedule.hours}h`);
      if (schedule.minutes) parts.push(`${schedule.minutes}m`);
      const interval = parts.length ? parts.join(" ") : "0m";
      return `Every ${interval} – robot: ${escapeHtml(schedule.name || "")}`;
    }

    const runDate = schedule.run_date
      ? formatDate(schedule.run_date)
      : "not set";
    return `On ${runDate} – robot: ${escapeHtml(schedule.name || "")}`;
  }

  function formatDate(value) {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return escapeHtml(value);
    return date.toLocaleString();
  }

  function toDomId(value) {
    return (value || "").replace(/[^a-zA-Z0-9_-]/g, "_");
  }

  function escapeHtml(value) {
    return (value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  async function safeFetch(url, options) {
    try {
      const response = await fetch(url, options);
      if (!response || !response.ok) {
        throw new Error(
          `Request failed (${response?.status || "no response"})`,
        );
      }
      return await response.json();
    } catch (error) {
      console.error("Schedule API error", error);
      throw error;
    }
  }

  return { init };
})();
