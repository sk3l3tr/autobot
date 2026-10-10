
/**
███████████████████████████████████████████████████████████████████
  powered by

  ██████  ███████ ███    ███ ██ ██    ██ ██████   ██████  ███████ 
  ██   ██ ██      ████  ████ ██ ██    ██ ██   ██ ██       ██      
  ██   ██ █████   ██ ████ ██ ██ ██    ██ ██████  ██   ███ █████   
  ██   ██ ██      ██  ██  ██ ██ ██    ██ ██   ██ ██    ██ ██      
  ██████  ███████ ██      ██ ██  ██████  ██   ██  ██████  ███████

  PSEUDO-SPA ARCHITECTURE                                  v0.0.2                                  
███████████████████████████████████████████████████████████████████
*/

// ==== BEGIN src/core/layout.js ====
(function (global) {
  // Inserta un fragmento de HTML remoto dentro del selector indicado.
  async function injectPartial(selector, url) {
    const el = document.querySelector(selector);
    if (!el) return null;

    try {
      const res = await fetch(url, {
        headers: { "X-Requested-With": "LayoutPartial" },
      });
      if (!res.ok) {
        console.error(`No se pudo cargar ${url}:`, res.status);
        return null;
      }

      const html = await res.text();
      el.innerHTML = html;
      return el;
    } catch (err) {
      console.error(`Error al cargar ${url}:`, err);
      return null;
    }
  }

  // Normaliza rutas para compararlas (quita query/hash, colapsa index.html, quita slash final).
  function normalizePath(path) {
    if (!path) return "/";
    path = path.split("?")[0].split("#")[0];
    path = path.replace(/\/index\.html?$/i, "/");
    if (path.length > 1 && path.endsWith("/")) {
      path = path.slice(0, -1);
    }
    if (path === "") return "/";
    return path;
  }

  // Calcula qué link se parece más a la ruta actual (prefiere coincidencia exacta/prefijo).
  function matchScore(linkPath, currentPath) {
    // "/" solo aplica cuando la ruta actual es raíz
    if (linkPath === "/") return currentPath === "/" ? 0 : -1;

    if (currentPath === linkPath) return linkPath.length;

    // Coincidencia por prefijo con frontera de segmento (/blog/post -> /blog)
    if (currentPath.startsWith(linkPath)) {
      const boundary = currentPath.charAt(linkPath.length);
      if (!boundary || boundary === "/") {
        return linkPath.length;
      }
    }

    return -1;
  }

  // Añade la clase "accent" al link más cercano a la ruta actual; quita el resto.
  function markActiveNavLink(root, selector) {
    root = root || document;
    selector = selector || "#menu a[href]";

    const links = root.querySelectorAll(selector);
    const currentPath = normalizePath(window.location.pathname);

    let bestLink = null;
    let bestScore = -1;

    links.forEach((link) => {
      const href = link.getAttribute("href");
      if (!href) return;

      const url = new URL(href, window.location.origin);
      const linkPath = normalizePath(url.pathname);

      const score = matchScore(linkPath, currentPath);
      if (score > bestScore) {
        bestScore = score;
        bestLink = link;
      }
    });

    links.forEach((link) => {
      if (link === bestLink) {
        link.classList.add("accent");
      } else {
        link.classList.remove("accent");
      }
    });
  }

  global.Layout = {
    injectPartial,
    markActiveNavLink,
  };
})(window);

// ==== END src/core/layout.js ====

// ==== BEGIN src/core/pseudo-spa.js ====
(function (global) {
  // Determina si un click en un <a> debe ser manejado por el router (solo navegación interna).
  function defaultShouldHandleLink(link, event) {
    const href = link.getAttribute("href");
    if (!href) return false;

    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
      return false;
    }

    if (link.target && link.target !== "_self") return false;

    if (
      href.startsWith("#") ||
      href.startsWith("mailto:") ||
      href.startsWith("tel:")
    ) {
      return false;
    }

    const url = new URL(href, window.location.href);
    if (url.origin !== window.location.origin) return false;

    const currentWithoutHash = window.location.href.split("#")[0];
    if (url.href === currentWithoutHash) return false;

    return true;
  }

  // Router ligero que intercambia el contenido de <main> via fetch manteniendo history.pushState.
  class PseudoSPA {
    constructor(options = {}) {
      this.options = Object.assign(
        {
          contentSelector: "main",
          linkSelector: "a[href]",
          shouldHandleLink: defaultShouldHandleLink,
          getTitle: (doc) => {
            const t = doc.querySelector("title");
            return t ? t.textContent : document.title;
          },
          onBeforeNavigate: () => {},
          onAfterNavigate: () => {},
          transition: {
            enabled: true,
            duration: 180,
            leaveClass: "spa-leave",
            leaveActiveClass: "spa-leave-active",
            enterClass: "spa-enter",
            enterActiveClass: "spa-enter-active",
          },
        },
        options
      );

      this.isNavigating = false;
      this.currentUrl = window.location.href;
    }

    init() {
      // Suscribe los listeners de click y popstate para interceptar navegación interna.
      this.bindLinkClicks();
      this.bindPopState();
    }

    getContentEl() {
      return document.querySelector(this.options.contentSelector);
    }

    bindLinkClicks() {
      document.addEventListener("click", (event) => {
        const link = event.target.closest(this.options.linkSelector);
        if (!link) return;

        if (!this.options.shouldHandleLink(link, event)) return;

        event.preventDefault();
        const url = new URL(link.getAttribute("href"), window.location.href);
        this.navigate(url.href, { push: true });
      });
    }

    bindPopState() {
      window.addEventListener("popstate", () => {
        const url = window.location.href;
        this.navigate(url, { push: false });
      });
    }

    // Orquesta la navegación: dispara callbacks, aplica transición y cambia el <main>.
    navigate(url, { push } = { push: true }) {
      if (this.isNavigating) return;
      if (url === this.currentUrl) return;

      this.isNavigating = true;
      this.options.onBeforeNavigate(url);

      const doFetchAndSwap = () => {
        this.loadDocument(url)
          .then((doc) => {
            if (!doc) {
              window.location.href = url;
              return;
            }
            this.swapContent(doc, url, push);
          })
          .catch(() => {
            window.location.href = url;
          })
          .finally(() => {
            this.isNavigating = false;
          });
      };

      const t = this.options.transition;
      if (t && t.enabled) {
        const contentEl = this.getContentEl();
        if (!contentEl) {
          doFetchAndSwap();
          return;
        }

        let didStartSwap = false;
        const startSwap = () => {
          if (didStartSwap) return;
          didStartSwap = true;
          doFetchAndSwap();
        };

        contentEl.classList.add(t.leaveClass);
        contentEl.offsetHeight;
        contentEl.classList.add(t.leaveActiveClass);

        const onEnd = (e) => {
          if (e.target !== contentEl) return;
          contentEl.removeEventListener("transitionend", onEnd);
          startSwap();
        };

        contentEl.addEventListener("transitionend", onEnd);

        setTimeout(() => {
          contentEl.removeEventListener("transitionend", onEnd);
          if (this.isNavigating) startSwap();
        }, t.duration + 80);
      } else {
        doFetchAndSwap();
      }
    }

    // Descarga el documento destino; devuelve un Document listo para leer.
    loadDocument(url) {
      return fetch(url, {
        headers: { "X-Requested-With": "PseudoSPA" },
      })
        .then((res) => {
          if (!res.ok) return null;
          return res.text();
        })
        .then((html) => {
          if (!html) return null;
          const parser = new DOMParser();
          return parser.parseFromString(html, "text/html");
        });
    }

    // Reemplaza el contenido principal, actualiza el título y el historial, y aplica transiciones.
    swapContent(newDoc, url, push) {
      const newContent = newDoc.querySelector(this.options.contentSelector);
      const currentContent = this.getContentEl();

      if (!newContent || !currentContent) {
        window.location.href = url;
        return;
      }

      const importedNewContent = document.importNode(newContent, true);
      currentContent.replaceWith(importedNewContent);

      const newTitle = this.options.getTitle(newDoc);
      if (newTitle) document.title = newTitle;

      if (push) {
        history.pushState({ url }, "", url);
      }
      this.currentUrl = url;

      window.scrollTo({ top: 0, left: 0 });

      const t = this.options.transition;
      if (t && t.enabled) {
        importedNewContent.classList.add(t.enterClass);
        importedNewContent.offsetHeight;
        importedNewContent.classList.add(t.enterActiveClass);

        const cleanup = () => {
          importedNewContent.classList.remove(t.enterClass, t.enterActiveClass);
        };

        const onEnd = (e) => {
          if (e.target !== importedNewContent) return;
          importedNewContent.removeEventListener("transitionend", onEnd);
          cleanup();
        };

        importedNewContent.addEventListener("transitionend", onEnd);
        setTimeout(cleanup, t.duration + 80);
      }

      this.options.onAfterNavigate(url, newDoc);
    }
  }

  global.PseudoSPA = PseudoSPA;
})(window);

// ==== END src/core/pseudo-spa.js ====

// ==== BEGIN src/core/modal-service.js ====
(function () {
  // Servicio de modales accesible y reutilizable; conserva instancia por elemento raíz.
  class Modal {
    static instances = new Map();

    static getOrCreate(root) {
      if (!root) return null;
      if (!Modal.instances.has(root)) {
        Modal.instances.set(root, new Modal(root));
      }
      return Modal.instances.get(root);
    }

    constructor(root) {
      this.root = root;
      this.previouslyFocused = null;
      this._handleEsc = (e) => {
        if (e.key === "Escape") this.close();
      };
    }

    open() {
      if (this.isOpen()) return;

      this.previouslyFocused = document.activeElement;
      this.root.classList.add("is-open");
      this.root.setAttribute("aria-hidden", "false");

      const focusable = this.root.querySelector(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      );
      if (focusable) {
        focusable.focus();
      }

      document.addEventListener("keydown", this._handleEsc);
    }

    close() {
      if (!this.isOpen()) return;

      this.root.classList.remove("is-open");
      this.root.setAttribute("aria-hidden", "true");

      if (
        this.previouslyFocused &&
        typeof this.previouslyFocused.focus === "function"
      ) {
        this.previouslyFocused.focus();
      }
      document.removeEventListener("keydown", this._handleEsc);
    }

    toggle() {
      this.isOpen() ? this.close() : this.open();
    }

    isOpen() {
      return this.root.classList.contains("is-open");
    }
  }

  // Delegación de eventos para abrir/cerrar modales declarativos por data-attributes.
  function init() {
    // ABRIR
    document.addEventListener("click", (e) => {
      const path = e.composedPath ? e.composedPath() : [e.target];
      const openBtn = path.find(
        (node) =>
          node instanceof Element && node.hasAttribute("data-modal-open")
      );

      if (!openBtn) return;

      const targetSelector = openBtn.getAttribute("data-modal-open");
      if (!targetSelector) return;

      const modalEl = document.querySelector(targetSelector);
      const modal = Modal.getOrCreate(modalEl);

      if (modal) modal.open();
    });

    // CERRAR (esto probablemente ya te funciona bien)
    document.addEventListener("click", (e) => {
      const closeTrigger = e.target.closest("[data-modal-close]");
      if (!closeTrigger) return;

      const modalEl = closeTrigger.closest(".modal");
      const modal = Modal.getOrCreate(modalEl);
      if (modal) modal.close();
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  } else {
    init();
  }

  window.Modal = Modal;
})();

/*
<!-- Así se abre -->
<button
  data-modal-open="#system-pymes"
  class="btn secondary secondary-hover no-border fs-1"
>
  Ver detalles
</button>
*/

/* 
<!-- Esto es el modal -->
<section
  class="modal"
  aria-hidden="true"
  role="dialog"
  aria-modal="true"
  id="${id}"
>
  <div class="modal__backdrop" data-modal-close></div>
  <div class="modal__dialog" role="document"></div>
</section>; 
*/

// ==== END src/core/modal-service.js ====

// ==== BEGIN src/core/script-loader.js ====
(function (global) {
  // Carga scripts declarados en window.PageConfig y evita duplicados entre navegaciones pseudo-SPA.
  const loadedScripts = new Set();
  let currentPageScripts = new Set();
  let currentPageId = null;
  let currentInitCleanup = null;

  // Inserta un <script> en <head> y resuelve cuando termina de cargar (o si ya estaba cargado).
  function loadScript(src, { trackForCleanup = false } = {}) {
    return new Promise((resolve, reject) => {
      if (!src) return resolve();

      if (loadedScripts.has(src)) return resolve();

      const s = document.createElement("script");
      s.src = src;
      s.async = true;
      if (trackForCleanup) {
        s.dataset.pageScriptLoader = "true";
        s.dataset.pageScriptSrc = src;
      }

      s.onload = () => {
        loadedScripts.add(src);
        resolve();
      };
      s.onerror = () => {
        console.error("Error cargando script:", src);
        reject(new Error("Error cargando script: " + src));
      };

      document.head.appendChild(s);
    });
  }

  // Resuelve un string tipo "Namespace.fn" a una función global; devuelve null si no existe.
  function resolveFunction(path) {
    if (!path) return null;
    const parts = path.split(".");
    let ctx = global;

    for (const part of parts) {
      ctx = ctx?.[part];
      if (ctx == null) return null;
    }
    return typeof ctx === "function" ? ctx : null;
  }

  // Ejecuta teardown registrado (init que devolvió cleanup + PageConfig.pages[pageId].teardown).
  function runTeardown(config) {
    const pageCfg = config.pages && currentPageId && config.pages[currentPageId];

    if (typeof currentInitCleanup === "function") {
      try {
        currentInitCleanup();
      } catch (err) {
        console.error("Error en cleanup de init:", err);
      }
    }
    currentInitCleanup = null;

    if (pageCfg && pageCfg.teardown) {
      const teardownFn = resolveFunction(pageCfg.teardown);
      if (teardownFn) {
        try {
          teardownFn();
        } catch (err) {
          console.error("Error en teardown de la página:", err);
        }
      }
    }
  }

  // Elimina scripts exclusivos de la página anterior (se vuelven a cargar si se regresa a ella).
  function cleanupPageScripts() {
    if (!currentPageScripts.size) return;

    const nodes = document.querySelectorAll(
      'script[data-page-script-loader="true"]'
    );

    nodes.forEach((node) => {
      const src = node.dataset.pageScriptSrc;
      if (src && currentPageScripts.has(src)) {
        node.remove();
      }
    });

    currentPageScripts.forEach((src) => loadedScripts.delete(src));
    currentPageScripts = new Set();
  }

  // Carga scripts compartidos + específicos de la página y ejecuta opcionalmente su init.
  async function loadForPage(pageId) {
    const config = global.PageConfig;
    if (!config) return;

    // Teardown de la página anterior y limpieza de sus scripts.
    runTeardown(config);
    cleanupPageScripts();

    const tasks = [];

    // sharedScripts SIEMPRE (si existen)
    if (Array.isArray(config.sharedScripts)) {
      tasks.push(...config.sharedScripts.map(loadScript));
    }

    const pageCfg = config.pages && config.pages[pageId];
    const pageScripts =
      pageCfg && Array.isArray(pageCfg.scripts) ? pageCfg.scripts : [];

    // Cargar scripts exclusivos de la página y marcarlos para limpieza en la siguiente navegación.
    pageScripts.forEach((src) => currentPageScripts.add(src));
    tasks.push(
      ...pageScripts.map((src) => loadScript(src, { trackForCleanup: true }))
    );

    await Promise.all(tasks);

    if (pageCfg && pageCfg.init) {
      const initFn = resolveFunction(pageCfg.init);
      if (initFn) {
        const res = await initFn();
        // Permitir que init devuelva un cleanup para ejecutar al salir de la página.
        if (typeof res === "function") {
          currentInitCleanup = res;
        }
      }
    }

    currentPageId = pageId;
  }

  global.PageScriptLoader = {
    loadForPage,
    loadScript,
    resolveFunction,
  };
})(window);

// ==== END src/core/script-loader.js ====

// ==== BEGIN src/bootstrap.js ====
// Punto de entrada: monta parciales de layout, resalta el nav activo,
// carga scripts de la vista actual y habilita el router pseudo-SPA.
const ASCII = `
███████████████████████████████████████████████████████████████████
powered by

  ██████  ███████ ███    ███ ██ ██    ██ ██████   ██████  ███████ 
  ██   ██ ██      ████  ████ ██ ██    ██ ██   ██ ██       ██      
  ██   ██ █████   ██ ████ ██ ██ ██    ██ ██████  ██   ███ █████   
  ██   ██ ██      ██  ██  ██ ██ ██    ██ ██   ██ ██    ██ ██      
  ██████  ███████ ██      ██ ██  ██████  ██   ██  ██████  ███████

  PSEUDO-SPA ARCHITECTURE                                  v0.0.2                                  
███████████████████████████████████████████████████████████████████
`;

document.addEventListener("DOMContentLoaded", async function () {
  const config = window.PageConfig || {};
  const layoutCfg = config.layout || {};

  async function injectLayoutPart(partCfg) {
    if (!partCfg || !partCfg.selector || !partCfg.url) return;
    await Layout.injectPartial(partCfg.selector, partCfg.url);
  }

  // 1) Inyectar layout si hay config
  await Promise.all([
    injectLayoutPart(layoutCfg.header),
    injectLayoutPart(layoutCfg.footer),
  ]);

  // 2) Marcar nav activo si hay Layout y selector de menú
  if (typeof Layout?.markActiveNavLink === "function") {
    const navSelector = layoutCfg.navSelector || "#menu a[href]";
    Layout.markActiveNavLink(document, navSelector);
  }

  // 3) Ejecutar lógica de la página actual
  async function runCurrentPage() {
    const main = document.querySelector("main");
    if (!main) return;

    const pageId = main.getAttribute("data-page");
    if (!pageId) return;

    await PageScriptLoader.loadForPage(pageId);
  }

  await runCurrentPage();

  // 4) Router pseudo-SPA
  const router = new PseudoSPA({
    contentSelector: "main",
    onAfterNavigate: async function (url, newDoc) {
      if (typeof Layout?.markActiveNavLink === "function") {
        const navSelector = layoutCfg.navSelector || "#menu a[href]";
        Layout.markActiveNavLink(document, navSelector);
      }
      await runCurrentPage();
    },
  });

  router.init();
  console.log(ASCII);
});

// ==== END src/bootstrap.js ====
