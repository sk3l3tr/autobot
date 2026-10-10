window.IndexPage = (function () {
  const AppConfig = window.AutobotAppConfig;
  if (!AppConfig || typeof AppConfig.endpoint !== "function") {
    console.error("AutobotAppConfig is missing. Frontend endpoints are undefined.");
    return { init() {} };
  }

  const ENDPOINTS = {
    action: AppConfig.endpoint(AppConfig.action),
    robot: AppConfig.endpoint(AppConfig.robot),
  };

  const SELECTORS = {
    robotListContainer: "robot-list-container",
    robotList: "robot-list",
  };

  const REFRESH_DELAY = 500;

  const state = {
    robots: [],
  };

  const templates = {
    loader:
      "<span class='i i-loader pixel-rotate-animation' style='font-size:1.5rem;'></span>",
    emptyState: "<h2>No robots found</h2>",
    listShell: () => `
      <div style='display:flex;align-items:center;justify-content:space-between;'>
        <div style='display:flex;align-items:center;gap:0.75rem;'>
          <span id="add-btn" class='primary i i-add_box' title='Add' style='font-size:1.5rem; cursor:pointer;'></span>
          <button id="stop-btn" type="button" class="robot-stop-btn">STOP</button>
        </div>
        <h2 class='primary text-end'>LIST</h2>
      </div>
      <div id='${SELECTORS.robotList}'></div>
    `,
    robotItem: (name) => `
      <div class="list-item">
        <h2>${name}</h2>
        <div class="list-item__actions">
          <button popovertarget="${name}_pop" class="popover-anchor">
            <span class="i i-script_text" title="Options"></span>
          </button>
        </div>
      </div>
      <div popover id="${name}_pop" class="popover-menu">
        <div style="display:flex; flex-direction: column;">
          <span id="${name}_pop_play" class="i i-chevron_right" title="Play"></span>
          <span id="${name}_pop_edit" class="i i-script_text" title="Edit"></span>
          <span id="${name}_pop_delete" class="i i-trash" title="Delete"></span>
        </div>
      </div>
    `,
  };

  const api = {
    async listRobots() {
      try {
        const response = await fetch(ENDPOINTS.robot, {
          headers: { "X-Requested-With": "PageModule" },
        });

        if (!response || !response.ok) {
          throw new Error("Robot list request failed");
        }

        return await response.json();
      } catch (error) {
        console.error("Get Robots Error:", error);
        return [];
      }
    },

    async deleteRobot(name) {
      try {
        const response = await fetch(`${ENDPOINTS.robot}/${name}`, {
          method: "DELETE",
          headers: { "Content-Type": "application/json" },
        });

        if (!response || !response.ok) {
          throw new Error("Delete Robot request failed");
        }

        return await response.json();
      } catch (error) {
        console.error("Delete Robot Error:", error);
        return [];
      }
    },

    async openRecorder(fileName = "autobot") {
      const payload = {
        action: "open_robot_recorder",
        kwargs: { file_name: `${fileName}.yaml` },
      };

      await fetch(ENDPOINTS.action, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      }).catch((err) => console.error("Recorder Robot Error:", err));
    },

    async runRobot(name) {
      const payload = {
        action: "run_robot",
        kwargs: { name },
      };

      await fetch(ENDPOINTS.action, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      }).catch((err) => console.error("Run Robot Error:", err));
    },

    async stopRobot() {
      const payload = {
        action: "stop_robot",
        kwargs: {},
      };

      await fetch(ENDPOINTS.action, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      }).catch((err) => console.error("Stop Robot Error:", err));
    },

    async renameRobot(oldName, newName) {
      try {
        const response = await fetch(ENDPOINTS.robot, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ oldName, newName }),
        });

        if (!response || !response.ok) {
          throw new Error("Rename Robot request failed");
        }

        return await response.json();
      } catch (error) {
        console.error("Rename Robot Error:", error);
        return [];
      }
    },
  };

  function getElements() {
    return {
      robotListContainer: document.getElementById(SELECTORS.robotListContainer),
    };
  }

  function renderLoader(container) {
    if (!container) return;
    container.innerHTML = templates.loader;
  }

  function renderRobotList(container, robots) {
    container.innerHTML = templates.listShell();
    const listEl = container.querySelector(`#${SELECTORS.robotList}`);
    if (!listEl) return;

    if (!robots.length) {
      listEl.innerHTML = templates.emptyState;
      return;
    }

    listEl.appendChild(buildRobotItems(robots));
  }

  function updateRobotListUI(container, robots) {
    renderRobotList(container, robots);
    bindAddButton(container);
    bindStopButton(container);
    bindRobotActionEvents(container);
  }

  function buildRobotItems(robots) {
    const fragment = document.createDocumentFragment();

    robots.forEach((name) => {
      const template = document.createElement("template");
      template.innerHTML = templates.robotItem(name);
      fragment.appendChild(template.content);
    });

    return fragment;
  }

  function bindAddButton(container) {
    const addButton = container.querySelector("#add-btn");
    if (!addButton) return;

    addButton.addEventListener("click", () => handleAddRobot(container));
  }

  function bindStopButton(container) {
    const stopButton = container.querySelector("#stop-btn");
    if (!stopButton) return;

    stopButton.addEventListener("click", () => {
      api.stopRobot();
    });
  }

  function bindRobotActionEvents(container) {
    const robotListEl = container.querySelector(`#${SELECTORS.robotList}`);
    if (!robotListEl) return;

    robotListEl.addEventListener("click", (event) => {
      if (handleTitleClick(event, container)) return;
      handleRobotActionClick(event, container);
    });
  }

  async function handleAddRobot(container) {
    renderLoader(container);
    await api.openRecorder();
    scheduleRefresh();
  }

  function handleTitleClick(event, container) {
    const titleEl = event.target.closest(".list-item h2");
    if (!titleEl) return false;

    makeTitleEditable(titleEl, container);
    return true;
  }

  function makeTitleEditable(titleEl, container) {
    if (titleEl.isContentEditable) return;

    const originalName = titleEl.textContent.trim();
    titleEl.dataset.originalName = originalName;

    titleEl.setAttribute("contenteditable", "true");
    titleEl.focus();

    selectElementText(titleEl);

    const finishEditing = async () => {
      titleEl.removeAttribute("contenteditable");
      titleEl.removeEventListener("blur", finishEditing);
      titleEl.removeEventListener("keydown", handleKeydown);

      await processTitleChange(titleEl, originalName, container);
    };

    const handleKeydown = (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        titleEl.blur();
      }
    };

    titleEl.addEventListener("blur", finishEditing);
    titleEl.addEventListener("keydown", handleKeydown);
  }

  function selectElementText(element) {
    const selection = window.getSelection();
    if (!selection) return;

    const range = document.createRange();
    range.selectNodeContents(element);
    selection.removeAllRanges();
    selection.addRange(range);
  }

  async function processTitleChange(titleEl, originalName, container) {
    const newName = titleEl.textContent.trim();
    delete titleEl.dataset.originalName;

    if (!newName || newName === originalName) {
      titleEl.textContent = originalName;
      return;
    }

    renderLoader(container);

    const robots = await api.renameRobot(originalName, newName);
    state.robots = robots;

    updateRobotListUI(container, state.robots);
  }

  async function handleRobotActionClick(event, container) {
    const actionEl = event.target.closest("span[id]");
    if (!actionEl) return;

    const { id } = actionEl;
    const robotName = extractRobotName(id);
    if (!robotName) return;

    if (id.endsWith("_pop_play")) {
      api.runRobot(robotName);
      return;
    }

    if (id.endsWith("_pop_edit")) {
      api.openRecorder(robotName);
      return;
    }

    if (id.endsWith("_pop_delete")) {
      renderLoader(container);
      const robots = await api.deleteRobot(robotName);
      state.robots = robots;
      updateRobotListUI(container, state.robots);
      return;
    }
  }

  function extractRobotName(identifier) {
    const suffixIndex = identifier.lastIndexOf("_pop_");
    return suffixIndex === -1 ? "" : identifier.slice(0, suffixIndex);
  }

  function scheduleRefresh(delay = REFRESH_DELAY) {
    setTimeout(() => init(), delay);
  }

  async function init() {
    const { robotListContainer } = getElements();
    if (!robotListContainer) return;

    renderLoader(robotListContainer);
    state.robots = await api.listRobots();

    updateRobotListUI(robotListContainer, state.robots);
  }

  return { init };
})();
