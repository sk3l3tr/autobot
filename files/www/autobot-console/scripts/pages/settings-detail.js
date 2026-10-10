window.SettingsDetailPage = (function () {
  const AppConfig = window.AutobotAppConfig;
  if (!AppConfig || typeof AppConfig.endpoint !== "function") {
    console.error("AutobotAppConfig is missing. Settings detail unavailable.");
    return { init() {} };
  }

  const ENDPOINTS = {
    config: AppConfig.endpoint(AppConfig.config),
  };

  const SELECTORS = {
    form: "settings-detail-form",
    title: "settings-detail-title",
    description: "settings-detail-description",
    fields: "settings-detail-fields",
    feedback: "settings-detail-feedback",
    saveButton: "settings-detail-save",
  };

  const state = {
    fullConfig: [],
    currentCategoryId: null,
    currentCategory: null,
    isSaving: false,
  };

  const elements = {};

  async function init() {
    cacheElements();
    setFeedback("Loading...", "muted");

    const params = new URLSearchParams(window.location.search);
    state.currentCategoryId = params.get("id");

    if (!state.currentCategoryId) {
      setFeedback("Missing category id.", "error");
      return;
    }

    try {
      state.fullConfig = await fetchConfig();
      state.currentCategory = findCategoryById(
        state.fullConfig,
        state.currentCategoryId,
      );
    } catch (error) {
      console.error("Load config error", error);
      setFeedback("Failed to load settings.", "error");
      return;
    }

    if (!state.currentCategory) {
      setFeedback("Category not found. Redirecting...", "error");
      setTimeout(() => navigate("/settings.html"), 1000);
      return;
    }

    renderCategory();
    setFeedback("", "muted");
  }

  function cacheElements() {
    Object.entries(SELECTORS).forEach(([key, id]) => {
      elements[key] = document.getElementById(id);
    });
  }

  async function onSubmit(event) {
    event.preventDefault();
    if (state.isSaving) return;

    clearFieldErrors();
    const fields = getSettingFields();
    if (!fields.length) {
      setFeedback("No editable fields found.", "error");
      return;
    }

    const updates = [];
    for (const field of fields) {
      const result = readFieldValue(field);
      if (!result.valid) {
        setFieldError(field, result.error || "Invalid value.");
        setFeedback("Please fix invalid fields before saving.", "error");
        return;
      }
      updates.push(result);
    }

    applyValueToConfig(updates);

    try {
      toggleSaving(true);
      await saveConfig(state.fullConfig);
      setFeedback("Settings saved successfully.", "success");
    } catch (error) {
      console.error("Save config error", error);
      setFeedback("Failed to save settings.", "error");
    } finally {
      toggleSaving(false);
    }
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

  function findCategoryById(config, categoryId) {
    return (
      (config || []).find((category) => category?.id === categoryId) || null
    );
  }

  function renderCategory() {
    if (!elements.title || !elements.description || !elements.fields) return;

    elements.title.textContent =
      state.currentCategory?.label || state.currentCategory?.id || "Settings";
    elements.description.textContent = state.currentCategory?.description || "";

    elements.fields.innerHTML = "";
    const blocks = Array.isArray(state.currentCategory?.blocks)
      ? state.currentCategory.blocks
      : [];

    if (!blocks.length) {
      const empty = document.createElement("p");
      empty.className = "muted";
      empty.textContent = "No options available for this category.";
      elements.fields.appendChild(empty);
      return;
    }

    const fragment = document.createDocumentFragment();
    blocks.forEach((block, blockIndex) => {
      fragment.appendChild(renderBlock(block, blockIndex));
    });

    elements.fields.appendChild(fragment);
  }

  function renderBlock(block, blockIndex) {
    const section = document.createElement("section");
    section.className = "settings-detail__block";

    if (block?.label) {
      const title = document.createElement("h3");
      title.className = "settings-detail__block-title";
      title.textContent = block.label;
      section.appendChild(title);
    }

    const options = Array.isArray(block?.options) ? block.options : [];
    const optionsContainer = document.createElement("div");
    optionsContainer.className = "pixel-form pixel-form--grid";

    options.forEach((option, optionIndex) => {
      optionsContainer.appendChild(
        renderOptionField(option, block, blockIndex, optionIndex),
      );
    });

    section.appendChild(optionsContainer);
    return section;
  }

  function renderOptionField(option, block, blockIndex, optionIndex) {
    const field = document.createElement("div");
    field.className = "pixel-field";

    const inputId = `setting_${blockIndex}_${optionIndex}`;
    const label = document.createElement("label");
    label.htmlFor = inputId;
    label.textContent =
      option?.label || option?.id || `Option ${optionIndex + 1}`;
    field.appendChild(label);

    const type = normalizeType(option?.type);
    const control =
      type === "boolean"
        ? buildBooleanInput(option, inputId)
        : buildInput(option, inputId);

    control.dataset.settingField = "true";
    control.dataset.categoryId = state.currentCategoryId || "";
    control.dataset.blockId = block?.id || "";
    control.dataset.blockIndex = String(blockIndex);
    control.dataset.optionId = option?.id || "";
    control.dataset.optionIndex = String(optionIndex);
    control.dataset.type = type;
    if (option?.min !== undefined && option?.min !== null) {
      control.dataset.min = String(option.min);
    }
    if (option?.max !== undefined && option?.max !== null) {
      control.dataset.max = String(option.max);
    }

    field.appendChild(
      type === "boolean" ? buildBooleanWrapper(control) : control,
    );

    if (option?.description) {
      const helper = document.createElement("span");
      helper.className = "pixel-helper";
      helper.textContent = option.description;
      field.appendChild(helper);
    }

    const error = document.createElement("span");
    error.className = "settings-field-error";
    error.hidden = true;
    field.appendChild(error);

    return field;
  }

  function buildInput(option, inputId) {
    const input = document.createElement("input");
    input.id = inputId;
    input.className = "pixel-input";
    const type = normalizeType(option?.type);

    if (type === "number") {
      input.type = "number";
      input.step = "any";
      if (option?.min !== undefined && option?.min !== null)
        input.min = option.min;
      if (option?.max !== undefined && option?.max !== null)
        input.max = option.max;
      input.value =
        option?.value === undefined || option?.value === null
          ? ""
          : String(option.value);
      return input;
    }

    input.type = "text";
    input.value =
      option?.value === undefined || option?.value === null
        ? ""
        : String(option.value);
    return input;
  }

  function buildBooleanInput(option, inputId) {
    const input = document.createElement("input");
    input.className = "settings-checkbox__input";
    input.id = inputId;
    input.type = "checkbox";
    input.checked = Boolean(option?.value);
    return input;
  }

  function buildBooleanWrapper(input) {
    const wrapper = document.createElement("label");
    wrapper.className = "settings-checkbox";
    wrapper.htmlFor = input.id;
    wrapper.appendChild(input);

    const text = document.createElement("span");
    text.textContent = input.checked ? "Enabled" : "Disabled";
    wrapper.appendChild(text);

    input.addEventListener("change", () => {
      text.textContent = input.checked ? "Enabled" : "Disabled";
    });

    return wrapper;
  }

  function getSettingFields() {
    if (!elements.fields) return [];
    return Array.from(
      elements.fields.querySelectorAll("[data-setting-field='true']"),
    );
  }

  function readFieldValue(field) {
    const type = normalizeType(field.dataset.type);
    const blockIndex = Number.parseInt(field.dataset.blockIndex || "-1", 10);
    const optionIndex = Number.parseInt(field.dataset.optionIndex || "-1", 10);
    const blockId = field.dataset.blockId || "";
    const optionId = field.dataset.optionId || "";

    if (type === "boolean") {
      return {
        valid: true,
        type,
        blockIndex,
        optionIndex,
        blockId,
        optionId,
        value: Boolean(field.checked),
      };
    }

    if (type === "number") {
      const raw = field.value;
      const value = Number(raw);
      if (raw === "" || !Number.isFinite(value)) {
        return { valid: false, error: "A valid number is required." };
      }

      if (field.dataset.min !== undefined) {
        const min = Number(field.dataset.min);
        if (Number.isFinite(min) && value < min) {
          return { valid: false, error: `Value must be >= ${min}.` };
        }
      }

      if (field.dataset.max !== undefined) {
        const max = Number(field.dataset.max);
        if (Number.isFinite(max) && value > max) {
          return { valid: false, error: `Value must be <= ${max}.` };
        }
      }

      return {
        valid: true,
        type,
        blockIndex,
        optionIndex,
        blockId,
        optionId,
        value,
      };
    }

    return {
      valid: true,
      type: "text",
      blockIndex,
      optionIndex,
      blockId,
      optionId,
      value: field.value,
    };
  }

  function applyValueToConfig(updates) {
    updates.forEach((update) => {
      const category = state.fullConfig.find(
        (item) => item?.id === state.currentCategoryId,
      );
      if (!category) return;

      const blocks = Array.isArray(category.blocks) ? category.blocks : [];
      const block = blocks[update.blockIndex];
      if (!block) return;

      const options = Array.isArray(block.options) ? block.options : [];
      const option = options[update.optionIndex];
      if (!option) return;

      if (update.blockId && block.id !== update.blockId) return;
      if (update.optionId && option.id !== update.optionId) return;

      option.value = update.value;
    });
  }

  async function saveConfig(payload) {
    const response = await fetch(ENDPOINTS.config, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error(`Request failed: ${response.status}`);
    }

    return response;
  }

  function clearFieldErrors() {
    if (!elements.fields) return;
    const errors = elements.fields.querySelectorAll(".settings-field-error");
    errors.forEach((errorEl) => {
      errorEl.hidden = true;
      errorEl.textContent = "";
    });
  }

  function setFieldError(field, message) {
    const wrapper = field.closest(".pixel-field");
    const errorEl = wrapper?.querySelector(".settings-field-error");
    if (!errorEl) return;
    errorEl.textContent = message;
    errorEl.hidden = false;
  }

  function setFeedback(message, kind) {
    if (!elements.feedback) return;
    elements.feedback.textContent = message || "";
    elements.feedback.classList.remove(
      "muted",
      "settings-detail__feedback--error",
      "settings-detail__feedback--success",
    );
    if (kind === "error") {
      elements.feedback.classList.add("settings-detail__feedback--error");
      return;
    }
    if (kind === "success") {
      elements.feedback.classList.add("settings-detail__feedback--success");
      return;
    }
    elements.feedback.classList.add("muted");
  }

  function toggleSaving(isSaving) {
    state.isSaving = isSaving;
    if (elements.saveButton) {
      elements.saveButton.disabled = isSaving;
      elements.saveButton.textContent = isSaving ? "Saving..." : "Save";
    }
  }

  function normalizeType(type) {
    if (type === "number" || type === "boolean" || type === "text") {
      return type;
    }
    return "text";
  }

  function navigate(url) {
    window.location.href = url;
  }

  return { init };
})();
