(() => {
  const body = document.body;
  const desktop = window.matchMedia("(min-width: 1200px)");

  /* ------------------------------------------------------------------
     Toasts (same markup as Django messages in base.html)
     ------------------------------------------------------------------ */
  function showToast(text, kind = "success") {
    let box = document.querySelector(".toasts");
    if (!box) {
      box = document.createElement("div");
      box.className = "toasts";
      box.setAttribute("role", "status");
      body.append(box);
    }
    const toast = document.createElement("div");
    toast.className = `toast toast--${kind}`;
    toast.textContent = text;
    toast.addEventListener("animationend", () => toast.remove());
    box.append(toast);
  }

  /* ------------------------------------------------------------------
     Copy text returned by a URL: <button data-copy-url="..." data-copy-label="Invite link">
     ------------------------------------------------------------------ */
  async function copyFromUrl(button) {
    const label = button.dataset.copyLabel || "Link";
    let text;
    try {
      const response = await fetch(button.dataset.copyUrl);
      if (!response.ok) throw new Error(response.statusText);
      text = (await response.text()).trim();
    } catch {
      showToast(`Couldn't get the ${label.toLowerCase()}`, "error");
      return;
    }
    try {
      await navigator.clipboard.writeText(text);
      showToast(`${label} copied`);
    } catch {
      // Clipboard API needs HTTPS; let the user copy manually.
      window.prompt(`Copy the ${label.toLowerCase()}:`, text);
    }
  }

  /* ------------------------------------------------------------------
     Forms panel (layouts/workspace.html)
     ------------------------------------------------------------------ */
  const openPanel = () => body.classList.add("panel-open");
  const closePanel = () => body.classList.remove("panel-open");
  const clearActive = () => document.querySelectorAll(".is-active[data-panel-item]").forEach((el) => el.classList.remove("is-active"));

  document.addEventListener("click", (event) => {
    const target = event.target;

    if (target.closest("[data-panel-close]")) closePanel();

    const copyButton = target.closest("[data-copy-url]");
    if (copyButton) copyFromUrl(copyButton);

    // Quick-fill buttons, e.g. duration chips: <button data-fill="duration" data-value="45">
    const chip = target.closest("[data-fill]");
    if (chip) {
      const input = chip.form?.elements[chip.dataset.fill];
      if (input) {
        input.value = chip.dataset.value;
        input.dispatchEvent(new Event("input", { bubbles: true }));
      }
      chip.parentElement.querySelectorAll("[data-fill]").forEach((el) => el.classList.toggle("is-active", el === chip));
    }

    // Highlight the item currently opened in the panel
    const item = target.closest('[hx-target="#form-container"]')?.closest("[data-panel-item]");
    if (item) {
      clearActive();
      item.classList.add("is-active");
    }
  });

  /* ------------------------------------------------------------------
     Number stepper: <div data-stepper><button data-step="-1"> <input type=number> <button data-step="1"></div>
     ------------------------------------------------------------------ */
  document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-stepper] [data-step]");
    if (!button) return;
    const input = button.closest("[data-stepper]").querySelector("input");
    const min = input.min === "" ? -Infinity : Number(input.min);
    const max = input.max === "" ? Infinity : Number(input.max);
    const next = (Number(input.value) || 0) + Number(button.dataset.step);
    input.value = Math.min(max, Math.max(min, next));
    input.dispatchEvent(new Event("input", { bubbles: true }));
  });

  /* ------------------------------------------------------------------
     Live totals: <span data-total data-price="600.00" data-qty="lessons_amount">
     shows price × the named input of the same form.
     ------------------------------------------------------------------ */
  const money = new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 });

  function updateTotals(form) {
    form.querySelectorAll("[data-total]").forEach((el) => {
      const qty = Math.max(0, Number(form.elements[el.dataset.qty]?.value) || 0);
      el.textContent = money.format(Number(el.dataset.price) * qty);
    });
  }

  document.addEventListener("input", (event) => {
    const form = event.target.form;
    if (form?.querySelector("[data-total]")) updateTotals(form);
  });

  /* ------------------------------------------------------------------
     Plain (non-htmx) forms that must not be sent twice, e.g. payments:
     <form data-submit-once> <button data-loading-text="Redirecting…">
     ------------------------------------------------------------------ */
  document.addEventListener("submit", (event) => {
    const form = event.target;
    if (!form.matches("[data-submit-once]")) return;
    if (form.dataset.submitted) {
      event.preventDefault();
      return;
    }
    form.dataset.submitted = "true";
    form.querySelectorAll("button[type=submit]").forEach((button) => {
      button.dataset.originalHtml = button.innerHTML;
      if (button.dataset.loadingText) button.textContent = button.dataset.loadingText;
      button.classList.add("htmx-request");
    });
  });

  // Coming back from the payment page via "Back" restores the page from cache: unlock the form.
  window.addEventListener("pageshow", () => {
    document.querySelectorAll("form[data-submitted]").forEach((form) => {
      delete form.dataset.submitted;
      form.querySelectorAll("button[data-original-html]").forEach((button) => {
        button.innerHTML = button.dataset.originalHtml;
        button.classList.remove("htmx-request");
      });
    });
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closePanel();
  });

  body.addEventListener("htmx:afterSwap", (event) => {
    const { target, requestConfig } = event.detail;
    if (target.id !== "form-container") return;

    const trigger = requestConfig?.elt;
    // The container's own initial load and "cancel" buttons must not pop the panel open.
    if (trigger === target || trigger?.hasAttribute("data-panel-close")) {
      clearActive();
      return;
    }

    if (desktop.matches) {
      target.querySelector("input:not([type=hidden]), select")?.focus({ preventScroll: true });
    } else {
      openPanel();
    }
  });

  /* ------------------------------------------------------------------
     Client-side search + pagination for any list:
       <div data-list data-page-size="10">
         <input data-list-search>
         <span data-list-count></span>
         <article data-list-item data-search="text to match">…</article>
         <div data-list-no-results hidden></div>
         <nav data-list-pager></nav>
       </div>
     ------------------------------------------------------------------ */
  function pageNumbers(current, total) {
    if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1);
    const pages = new Set([1, total, current - 1, current, current + 1]);
    const sorted = [...pages].filter((n) => n >= 1 && n <= total).sort((a, b) => a - b);
    // insert gaps ("…") between non-consecutive numbers
    return sorted.flatMap((n, i) => (i && n - sorted[i - 1] > 1 ? ["…", n] : [n]));
  }

  function pagerButton(label, page, { current = false, disabled = false, aria } = {}) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "pager__btn";
    button.textContent = label;
    button.dataset.page = page;
    button.disabled = disabled;
    if (current) button.setAttribute("aria-current", "page");
    if (aria) button.setAttribute("aria-label", aria);
    return button;
  }

  function initList(root) {
    if (root.dataset.listReady) return;
    root.dataset.listReady = "true";

    const items = [...root.querySelectorAll("[data-list-item]")];
    const search = root.querySelector("[data-list-search]");
    const count = root.querySelector("[data-list-count]");
    const noResults = root.querySelector("[data-list-no-results]");
    const pager = root.querySelector("[data-list-pager]");
    const pageSize = Number(root.dataset.pageSize) || 10;
    const haystack = new Map(items.map((el) => [el, (el.dataset.search || el.textContent).toLocaleLowerCase()]));
    let page = 1;

    function render() {
      const query = (search?.value || "").trim().toLocaleLowerCase();
      const matches = query ? items.filter((el) => haystack.get(el).includes(query)) : items;
      const totalPages = Math.max(1, Math.ceil(matches.length / pageSize));
      page = Math.min(page, totalPages);

      const visible = new Set(matches.slice((page - 1) * pageSize, page * pageSize));
      items.forEach((el) => (el.hidden = !visible.has(el)));

      if (count) count.textContent = query ? `${matches.length} of ${items.length}` : items.length;
      if (noResults) noResults.hidden = !(query && matches.length === 0);

      if (pager) {
        pager.replaceChildren();
        pager.hidden = totalPages === 1;
        if (totalPages > 1) {
          pager.append(pagerButton("←", page - 1, { disabled: page === 1, aria: "Previous page" }));
          for (const n of pageNumbers(page, totalPages)) {
            if (n === "…") {
              const gap = document.createElement("span");
              gap.className = "pager__gap";
              gap.textContent = "…";
              pager.append(gap);
            } else {
              pager.append(pagerButton(n, n, { current: n === page, aria: `Page ${n}` }));
            }
          }
          pager.append(pagerButton("→", page + 1, { disabled: page === totalPages, aria: "Next page" }));
        }
      }
    }

    search?.addEventListener("input", () => {
      page = 1;
      render();
    });

    pager?.addEventListener("click", (event) => {
      const button = event.target.closest("[data-page]");
      if (!button || button.disabled) return;
      page = Number(button.dataset.page);
      render();
      if (root.getBoundingClientRect().top < 0) root.scrollIntoView({ behavior: "smooth", block: "start" });
    });

    render();
  }

  htmx.onLoad((element) => {
    element.querySelectorAll?.("form").forEach((form) => {
      if (form.querySelector("[data-total]")) updateTotals(form);
    });
    if (element.matches?.("[data-list]")) initList(element);
    element.querySelectorAll?.("[data-list]").forEach(initList);
  });

  // On phones the schedule is a long list of days: start at today.
  if (!window.matchMedia("(min-width: 901px)").matches) {
    document.querySelector(".day.is-today")?.scrollIntoView({ block: "start" });
  }
})();
