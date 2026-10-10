window.ScheduleDetailPage = (function () {
  const AppConfig = window.AutobotAppConfig;
  if (!AppConfig || typeof AppConfig.endpoint !== "function") {
    console.error("AutobotAppConfig missing");
    return { init() {} };
  }

  const ENDPOINTS = {
    schedule: AppConfig.endpoint(AppConfig.schedule),
    robot: AppConfig.endpoint(AppConfig.robot),
    action: AppConfig.endpoint(AppConfig.action),
  };

  const SELECTORS = {
    form: "schedule-detail-form",
    id: "detail-id",
    robot: "detail-robot",
    trigger: "detail-trigger",
    runDate: "detail-run-date",
    intervalFields: "detail-interval-fields",
    dateFields: "detail-date-fields",
    days: "detail-days",
    hours: "detail-hours",
    minutes: "detail-minutes",
    createRobot: "detail-create-robot",
    backBtn: "schedule-back-btn",
    title: "schedule-detail-title",
  };

  const state = {
    mode: "create",
    editingId: null,
    robots: [],
  };

  const elements = {};

  const api = {
    async listSchedules() {
      return safeJsonFetch(ENDPOINTS.schedule) || [];
    },
    async save(payload) {
      return safeJsonFetch(ENDPOINTS.schedule, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
    },
    async listRobots() {
      return safeJsonFetch(ENDPOINTS.robot) || [];
    },
    async createRobot(name) {
      const payload = {
        action: "open_robot_recorder",
        kwargs: { file_name: `${name}.yaml` },
      };
      const res = await fetch(ENDPOINTS.action, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error("Failed to create robot");
    },
  };

  async function init() {
    cacheElements();
    bindEvents();

    const params = new URLSearchParams(window.location.search);
    const id = params.get("id");
    state.editingId = id;
    state.mode = id ? "edit" : "create";
    setTitle();

    await loadRobots();
    if (state.mode === "edit") {
      await populateSchedule(id);
    }
  }

  function cacheElements() {
    Object.entries(SELECTORS).forEach(([key, id]) => {
      elements[key] = document.getElementById(id);
    });
  }

  function bindEvents() {
    if (elements.form) {
      elements.form.addEventListener("submit", onSubmit);
    }

    elements.trigger?.addEventListener("change", () => {
      toggleInterval(elements.trigger.value);
    });

    elements.createRobot?.addEventListener("click", handleCreateRobot);
    elements.backBtn?.addEventListener("click", () =>
      navigate("/schedules.html"),
    );
  }

  async function onSubmit(event) {
    event.preventDefault();
    const payload = collectFormData();
    if (!payload) {
      alert("Please complete the form correctly");
      return;
    }

    try {
      await api.save(payload);
      navigate("/schedules.html");
    } catch (error) {
      console.error("Save schedule error", error);
      alert("Failed to save schedule. Check console for details.");
    }
  }

  function collectFormData() {
    const payload = {
      id: elements.id?.value.trim(),
      name: elements.robot?.value.trim(),
      trigger: elements.trigger?.value,
    };

    if (!payload.id || !payload.name || !payload.trigger) {
      return null;
    }

    payload.run_date = elements.runDate?.value || "";
    if (!payload.run_date) return null;

    if (payload.trigger === "interval") {
      payload.days = clamp(elements.days?.value);
      payload.hours = clamp(elements.hours?.value);
      payload.minutes = clamp(elements.minutes?.value);
      if (!(payload.days + payload.hours + payload.minutes)) {
        return null;
      }
    }

    return payload;
  }

  function clamp(value) {
    const parsed = parseInt(value, 10);
    return Number.isNaN(parsed) || parsed < 0 ? 0 : parsed;
  }

  function toggleInterval(triggerValue) {
    const show = triggerValue === "interval";
    if (elements.intervalFields) {
      elements.intervalFields.hidden = !show;
    }
  }

  async function loadRobots() {
    try {
      state.robots = await api.listRobots();
    } catch (err) {
      console.error("load robots", err);
      state.robots = [];
    }
    renderRobotOptions();
  }

  function renderRobotOptions(selected) {
    const select = elements.robot;
    if (!select) return;
    select.innerHTML = "";
    const placeholder = document.createElement("option");
    placeholder.value = "";
    placeholder.textContent = state.robots.length
      ? "Select a robot"
      : "No robots";
    placeholder.disabled = true;
    placeholder.selected = !selected;
    select.appendChild(placeholder);

    state.robots.forEach((robot) => {
      const option = document.createElement("option");
      option.value = robot;
      option.textContent = robot;
      if (selected === robot) option.selected = true;
      select.appendChild(option);
    });
  }

  async function populateSchedule(id) {
    try {
      const schedules = await api.listSchedules();
      const schedule = schedules.find((s) => s.id === id);
      if (!schedule) {
        alert("Schedule not found");
        navigate("/schedules.html");
        return;
      }
      applyScheduleValues(schedule);
    } catch (error) {
      console.error("Load schedule", error);
      alert("Unable to load schedule");
      navigate("/schedules.html");
    }
  }

  function applyScheduleValues(schedule) {
    if (elements.id) {
      elements.id.value = schedule.id || "";
      elements.id.disabled = true;
    }
    const cleanName = sanitizeName(schedule.name || "");
    renderRobotOptions(cleanName);

    if (elements.trigger) elements.trigger.value = schedule.trigger || "date";
    if (elements.runDate)
      elements.runDate.value = toDateInput(schedule.run_date);
    if (elements.days) elements.days.value = schedule.days ?? 0;
    if (elements.hours) elements.hours.value = schedule.hours ?? 0;
    if (elements.minutes) elements.minutes.value = schedule.minutes ?? 0;
    toggleInterval(elements.trigger?.value);
    setTitle(schedule.id || "Schedule");
  }

  function sanitizeName(value) {
    return (value || "").replace(/\.yaml$/i, "");
  }

  function toDateInput(value) {
    if (!value) return "";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "";
    const pad = (n) => String(n).padStart(2, "0");
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
  }

  function setTitle(id) {
    if (!elements.title) return;
    elements.title.textContent =
      state.mode === "edit" ? `Edit ${id}` : "New Schedule";
  }

  async function handleCreateRobot() {
    const desired = prompt("Robot name?");
    if (!desired) return;
    const sanitized = sanitizeInput(desired);
    if (!sanitized) {
      alert("Invalid name");
      return;
    }
    try {
      await api.createRobot(sanitized);
      await loadRobots();
      elements.robot.value = sanitized;
    } catch (error) {
      console.error("create robot", error);
      alert("Failed to start robot recorder");
    }
  }

  function sanitizeInput(value) {
    return value.trim().replace(/[^\w-]/g, "_");
  }

  function navigate(url) {
    window.location.href = url;
  }

  async function safeJsonFetch(url, options) {
    const response = await fetch(url, options);
    if (!response.ok) {
      throw new Error(`Request failed: ${response.status}`);
    }
    return response.json();
  }

  return { init };
})();
