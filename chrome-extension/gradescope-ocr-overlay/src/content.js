(function () {
  const GRADE_URL_PATTERN = /^\/courses\/(?<courseId>\d+)\/questions\/(?<questionId>\d+)\/submissions\/(?<submissionId>\d+)\/grade\/?$/;
  const GROUP_URL_PATTERN = /^\/courses\/(?<courseId>\d+)\/questions\/(?<questionId>\d+)\/answer_groups(?:\/(?<answerGroupId>\d+))?\/?$/;
  const GROUPS_INDEX_URL_PATTERN = /^\/courses\/\d+\/questions\/\d+\/answer_groups\/?$/;
  const UNGROUPED_URL_PATTERN = /^\/courses\/\d+\/questions\/\d+\/answer_groups\/ungrouped\/?$/;
  const STORAGE_KEY = "gradescopeOcrOverlayPrefs";
  const HOST_ID = "gradescope-ocr-overlay-root";

  if (document.getElementById(HOST_ID)) {
    return;
  }

  const initialPage = parsePage();
  if (!initialPage && !isExcludedAnswerGroupPage()) {
    return;
  }

  const state = {
    page: initialPage,
    index: null,
    entry: null,
    groupEntries: [],
    groupOptions: [],
    selectedSubmissionId: initialPage ? initialPage.submissionId : null,
    inlineStats: null,
    inlineRenderTimer: null,
    inlineRetryTimer: null,
    inlineRetryUntil: 0,
    inlineComplete: false,
    lazyObserver: null,
    lazyObserverTimer: null,
    lazyRenderSignalTimer: null,
    lazyLoadHandler: null,
    moveControlActive: false,
    moveSelections: new Map(),
    prefs: {
      collapsed: false,
      top: 96,
      right: 24,
      width: 460
    }
  };

  const host = document.createElement("div");
  host.id = HOST_ID;
  const shadow = host.attachShadow({ mode: "open" });
  document.documentElement.appendChild(host);

  shadow.innerHTML = `
    <style>
      :host {
        all: initial;
        color-scheme: light;
        font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      }

      .panel {
        position: fixed;
        top: 96px;
        right: 24px;
        width: min(460px, calc(100vw - 32px));
        max-height: min(720px, calc(100vh - 32px));
        z-index: 2147483647;
        display: flex;
        flex-direction: column;
        overflow: hidden;
        border: 1px solid rgba(20, 24, 35, 0.18);
        border-radius: 8px;
        background: #fff;
        box-shadow: 0 18px 50px rgba(20, 24, 35, 0.22);
      }

      .panel.collapsed {
        width: auto;
        min-width: 186px;
      }

      .panel.hidden {
        display: none;
      }

      .header {
        display: flex;
        align-items: center;
        gap: 8px;
        min-height: 38px;
        padding: 7px 8px 7px 10px;
        border-bottom: 1px solid rgba(20, 24, 35, 0.12);
        background: #f8fafc;
        cursor: move;
        user-select: none;
      }

      .title {
        flex: 1;
        min-width: 0;
        font-size: 13px;
        font-weight: 650;
        color: #111827;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }

      .badge {
        flex: 0 0 auto;
        padding: 2px 6px;
        border-radius: 999px;
        background: #eef2ff;
        color: #3730a3;
        font-size: 11px;
        font-weight: 650;
      }

      .icon-button {
        flex: 0 0 auto;
        width: 28px;
        height: 28px;
        border: 1px solid rgba(20, 24, 35, 0.14);
        border-radius: 6px;
        background: #fff;
        color: #111827;
        font-size: 13px;
        line-height: 1;
        cursor: pointer;
      }

      .icon-button:hover {
        background: #f3f4f6;
      }

      .body {
        display: flex;
        flex-direction: column;
        min-height: 0;
      }

      .panel.collapsed .body,
      .panel.collapsed .footer {
        display: none;
      }

      .meta {
        display: grid;
        grid-template-columns: auto 1fr;
        gap: 3px 8px;
        padding: 9px 12px;
        border-bottom: 1px solid rgba(20, 24, 35, 0.10);
        background: #fff;
        color: #374151;
        font-size: 12px;
      }

      .meta-label {
        color: #6b7280;
      }

      .chooser {
        display: grid;
        grid-template-columns: 1fr auto;
        gap: 8px;
        padding: 9px 12px;
        border-bottom: 1px solid rgba(20, 24, 35, 0.10);
        background: #f8fafc;
      }

      .select {
        min-width: 0;
        border: 1px solid rgba(20, 24, 35, 0.18);
        border-radius: 6px;
        background: #fff;
        color: #111827;
        font-size: 12px;
        padding: 6px 8px;
      }

      .counter {
        align-self: center;
        color: #6b7280;
        font-size: 11px;
        white-space: nowrap;
      }

      .text {
        box-sizing: border-box;
        width: 100%;
        min-height: 180px;
        max-height: min(460px, calc(100vh - 240px));
        padding: 12px;
        overflow: auto;
        background: #fff;
        color: #111827;
        font-size: 13px;
        line-height: 1.5;
        white-space: pre-wrap;
      }

      .gradescope-ocr-move {
        display: grid;
        grid-template-columns: auto minmax(0, 1fr);
        gap: 6px;
        align-items: center;
        padding: 8px 12px;
        border-top: 1px solid rgba(20, 24, 35, 0.10);
        background: #f8fafc;
      }

      .gradescope-ocr-move-label,
      .gradescope-ocr-move-status {
        color: #6b7280;
        font-size: 11px;
        white-space: nowrap;
      }

      .gradescope-ocr-move-select {
        min-width: 0;
        border: 1px solid rgba(20, 24, 35, 0.18);
        border-radius: 6px;
        background: #fff;
        color: #111827;
        font-size: 12px;
        padding: 6px 8px;
      }

      .gradescope-ocr-move-status {
        grid-column: 2 / 3;
        overflow: hidden;
        text-overflow: ellipsis;
      }

      .math {
        font-family: "Times New Roman", Cambria, Georgia, serif;
        font-size: 1.08em;
      }

      .math-inline {
        display: inline;
        padding: 0 2px;
      }

      .math-display {
        display: block;
        margin: 8px 0;
        padding: 8px 10px;
        overflow-x: auto;
        border-radius: 6px;
        background: #f8fafc;
        text-align: center;
      }

      .math-frac {
        display: inline-flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        vertical-align: middle;
        margin: 0 2px;
      }

      .math-frac > .num {
        padding: 0 3px 1px;
        border-bottom: 1px solid currentColor;
        line-height: 1.1;
      }

      .math-frac > .den {
        padding: 1px 3px 0;
        line-height: 1.1;
      }

      .math-hat {
        text-decoration: overline;
        text-decoration-thickness: 1px;
      }

      .empty {
        padding: 14px 12px;
        color: #4b5563;
        font-size: 13px;
        line-height: 1.4;
      }

      .footer {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 8px;
        padding: 8px;
        border-top: 1px solid rgba(20, 24, 35, 0.10);
        background: #f8fafc;
      }

      .button-row {
        display: flex;
        gap: 6px;
      }

      .button {
        border: 1px solid rgba(20, 24, 35, 0.15);
        border-radius: 6px;
        background: #fff;
        color: #111827;
        font-size: 12px;
        font-weight: 600;
        line-height: 1;
        padding: 7px 9px;
        cursor: pointer;
      }

      .button:hover {
        background: #f3f4f6;
      }

      .status {
        min-width: 0;
        color: #6b7280;
        font-size: 11px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
    </style>

    <section class="panel hidden" part="panel">
      <header class="header" title="Drag to move">
        <span class="title">OCR Text</span>
        <span class="badge">loading</span>
        <button class="icon-button collapse" title="Collapse or expand" type="button">−</button>
        <button class="icon-button close" title="Hide overlay" type="button">×</button>
      </header>
      <div class="body"></div>
      <footer class="footer">
        <div class="button-row">
          <button class="button copy" type="button">Copy</button>
          <button class="button reload" type="button">Reload</button>
        </div>
        <div class="status">loading</div>
      </footer>
    </section>
  `;

  const panel = shadow.querySelector(".panel");
  const header = shadow.querySelector(".header");
  const title = shadow.querySelector(".title");
  const badge = shadow.querySelector(".badge");
  const body = shadow.querySelector(".body");
  const status = shadow.querySelector(".status");
  const collapseButton = shadow.querySelector(".collapse");
  const closeButton = shadow.querySelector(".close");
  const copyButton = shadow.querySelector(".copy");
  const reloadButton = shadow.querySelector(".reload");

  initialize();

  async function initialize() {
    state.prefs = { ...state.prefs, ...(await loadPrefs()) };
    applyPrefs();
    wireEvents();
    await loadAndRender();
  }

  async function loadAndRender() {
    clearInlineRenderTimer();
    stopLazyRenderObserver();

    if (!state.page || isExcludedAnswerGroupPage()) {
      removeInlineGroupOcr();
      panel.classList.add("hidden");
      body.innerHTML = "";
      badge.textContent = "off";
      status.textContent = "disabled on this page";
      return;
    }

    panel.classList.toggle("hidden", state.page.mode === "group");
    badge.textContent = "loading";
    title.textContent = state.page.mode === "group" ? "OCR Text: Answer Group" : "OCR Text";
    status.textContent = state.page.submissionId ? `submission ${state.page.submissionId}` : "answer group";
    try {
      if (!state.index) {
        state.index = await loadIndex();
      }
      if (state.page.mode === "group") {
        loadGroupEntries();
        renderGroup();
      } else {
        removeInlineGroupOcr();
        state.entry = lookupEntry(state.index, state.page.submissionId, state.page);
        renderSingleEntry();
      }
    } catch (error) {
      badge.textContent = "error";
      body.innerHTML = `<div class="empty">Could not load OCR data.<br>${escapeHtml(String(error.message || error))}</div>`;
    }
  }

  async function loadIndex() {
    const url = chrome.runtime.getURL("data/ocr-index.json");
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status} while loading OCR index`);
    }
    return response.json();
  }

  function loadGroupEntries() {
    const submissions = filterSubmissionsForCurrentGroup(extractSubmissionsFromPage());
    const seen = new Set();
    state.groupEntries = [];
    state.groupOptions = extractGroupsFromPage();
    state.inlineStats = null;
    state.inlineComplete = false;
    state.moveControlActive = false;
    state.moveSelections.clear();

    for (const submission of submissions) {
      const submissionId = String(submission.id || submission.submission_id || "");
      if (!submissionId || seen.has(submissionId)) {
        continue;
      }
      seen.add(submissionId);
      state.groupEntries.push({
        submissionId,
        graded: submission.graded,
        confirmedGroupId: submission.confirmed_group_id,
        unconfirmedGroupId: submission.unconfirmed_group_id,
        cropUrl: submission.masked_crop && submission.masked_crop.url ? String(submission.masked_crop.url) : "",
        cropPath: submission.masked_crop && submission.masked_crop.url ? urlPath(submission.masked_crop.url) : "",
        entry: lookupEntry(state.index, submissionId, state.page)
      });
    }

    if (!state.selectedSubmissionId || !seen.has(String(state.selectedSubmissionId))) {
      state.selectedSubmissionId = state.groupEntries[0] ? state.groupEntries[0].submissionId : null;
    }
    state.entry = selectedGroupEntry() ? selectedGroupEntry().entry : null;
  }

  function filterSubmissionsForCurrentGroup(submissions) {
    if (!state.page.answerGroupId) {
      return submissions;
    }

    const targetGroupId = String(state.page.answerGroupId);
    const matches = submissions.filter((submission) => {
      return [
        submission.confirmed_group_id,
        submission.unconfirmed_group_id,
        submission.answer_group_id,
        submission.group_id
      ].some((value) => value !== null && value !== undefined && String(value) === targetGroupId);
    });

    return matches.length ? matches : submissions;
  }

  function extractSubmissionsFromPage() {
    const reactProps = extractReactProps();
    for (const props of reactProps) {
      if (Array.isArray(props.submissions)) {
        return props.submissions;
      }
    }

    const ids = new Set();
    for (const link of document.querySelectorAll('a[href*="/submissions/"]')) {
      const match = link.href.match(/\/submissions\/(\d+)\//);
      if (match) ids.add(match[1]);
    }
    for (const element of document.querySelectorAll("[data-submission-id], [data-question-submission-id]")) {
      const id = element.getAttribute("data-submission-id") || element.getAttribute("data-question-submission-id");
      if (id) ids.add(id);
    }
    return Array.from(ids).map((id) => ({ id }));
  }

  function extractGroupsFromPage() {
    const reactProps = extractReactProps();
    for (const props of reactProps) {
      if (!Array.isArray(props.groups)) {
        continue;
      }
      return props.groups
        .filter((group) => group && group.id !== null && group.id !== undefined && group.hidden !== true)
        .map((group) => ({
          id: String(group.id),
          title: String(group.title || group.internal_title || `Group ${group.id}`)
        }));
    }
    return [];
  }

  function extractReactProps() {
    const props = [];
    for (const element of document.querySelectorAll("[data-react-props]")) {
      const raw = element.getAttribute("data-react-props");
      if (!raw) continue;
      try {
        props.push(JSON.parse(raw.replace(/&qquot;/g, "\"")));
      } catch (_error) {
        // Ignore unrelated React components with nonmatching data.
      }
    }
    return props;
  }

  function lookupEntry(index, submissionId, currentPage) {
    if (!submissionId) {
      return null;
    }
    const exactKey = `${currentPage.courseId}:${currentPage.questionId}:${submissionId}`;
    if (index.entriesByPage && index.entriesByPage[exactKey]) {
      return index.entriesByPage[exactKey];
    }
    if (index.entriesBySubmissionId && index.entriesBySubmissionId[submissionId]) {
      return index.entriesBySubmissionId[submissionId];
    }
    return null;
  }

  function selectedGroupEntry() {
    return state.groupEntries.find((item) => item.submissionId === String(state.selectedSubmissionId)) || null;
  }

  function renderSingleEntry() {
    if (!state.entry) {
      badge.textContent = "missing";
      body.innerHTML = `
        <div class="empty">
          No OCR text found for submission ${escapeHtml(state.page.submissionId)} on question ${escapeHtml(state.page.questionId)}.
        </div>
      `;
      return;
    }
    badge.textContent = (state.entry.text || "").trim() ? "found" : "blank";
    body.innerHTML = renderEntryHtml(state.entry);
    updateStatus();
  }

  function renderGroup() {
    const total = state.groupEntries.length;
    const found = state.groupEntries.filter((item) => item.entry).length;
    const selected = selectedGroupEntry();
    state.entry = selected ? selected.entry : null;
    badge.textContent = total ? `${found}/${total}` : "missing";

    if (!total) {
      body.innerHTML = `
        <div class="empty">
          Could not find any submissions on this answer-group page.
        </div>
      `;
      status.textContent = "0 submissions";
      return;
    }

    const options = state.groupEntries.map((item, index) => {
      const suffix = item.entry ? "" : " · no OCR";
      const selectedAttr = item.submissionId === String(state.selectedSubmissionId) ? " selected" : "";
      return `<option value="${escapeHtml(item.submissionId)}"${selectedAttr}>${index + 1}. ${escapeHtml(item.submissionId)}${suffix}</option>`;
    }).join("");

    body.innerHTML = `
      <div class="chooser">
        <select class="select" aria-label="Submission">${options}</select>
        <span class="counter">${found}/${total} found</span>
      </div>
      ${state.entry ? `${renderEntryHtml(state.entry)}${renderMoveControlHtml(selected)}` : `<div class="empty">No OCR text found for selected submission ${escapeHtml(state.selectedSubmissionId || "")}.</div>`}
    `;

    const select = body.querySelector(".select");
    if (select) {
      select.addEventListener("change", () => {
        state.selectedSubmissionId = select.value;
        renderGroup();
      });
    }
    if (selected) {
      wireMoveControls(body, selected);
    }
    startLazyRenderObserver();
    startInlineSyncWindow();
    scheduleInlineGroupOcr(120);
    updateStatus();
  }

  function renderEntryHtml(entry) {
    const text = entry.text || "";
    return `
      <div class="meta">
        <span class="meta-label">Submission</span><span>${escapeHtml(entry.submission_id || state.selectedSubmissionId || state.page.submissionId || "")}</span>
        <span class="meta-label">Question</span><span>${escapeHtml(entry.question || state.page.questionId)}</span>
        <span class="meta-label">Version</span><span>${escapeHtml(entry.version || "unknown")}</span>
        <span class="meta-label">Source</span><span title="${escapeHtml(entry.source_file || "")}">${escapeHtml(entry.source_file || "bundled OCR index")}</span>
      </div>
      <div class="text">${renderOcrText(text)}</div>
    `;
  }

  function renderMoveControlHtml(item) {
    if (!item || !state.groupOptions.length) {
      return "";
    }
    const currentGroupId = currentGroupIdForItem(item);
    const savedTargetId = state.moveSelections.get(item.submissionId) || "";
    const options = state.groupOptions.map((group) => {
      const isCurrent = currentGroupId && group.id === String(currentGroupId);
      const label = isCurrent ? `${group.title} (current)` : group.title;
      const selected = savedTargetId === group.id ? " selected" : "";
      return `<option value="${escapeHtml(group.id)}"${selected}>${escapeHtml(label)}</option>`;
    }).join("");
    const emptySelected = savedTargetId ? "" : " selected";

    return `
      <div class="gradescope-ocr-move" data-submission-id="${escapeHtml(item.submissionId)}">
        <span class="gradescope-ocr-move-label">Move to</span>
        <select class="gradescope-ocr-move-select" aria-label="Move submission to group">
          <option value=""${emptySelected}>Choose group...</option>
          ${options}
        </select>
        <span class="gradescope-ocr-move-status"></span>
      </div>
    `;
  }

  function wireMoveControls(root, item) {
    const control = root.querySelector(".gradescope-ocr-move");
    if (!control) {
      return;
    }
    const select = control.querySelector(".gradescope-ocr-move-select");
    const moveStatus = control.querySelector(".gradescope-ocr-move-status");
    if (!select || !moveStatus) {
      return;
    }

    const beginMoveInteraction = () => {
      state.moveControlActive = true;
      clearInlineRenderTimer();
      stopLazyRenderObserver();
    };

    for (const eventName of ["click", "mousedown", "pointerdown"]) {
      control.addEventListener(eventName, (event) => {
        beginMoveInteraction();
        event.stopPropagation();
      });
    }
    control.addEventListener("focusin", beginMoveInteraction);

    let moving = false;

    select.addEventListener("change", async (event) => {
      event.stopPropagation();
      beginMoveInteraction();
      if (moving) {
        return;
      }
      const currentGroupId = currentGroupIdForItem(item);
      const selectedIsCurrent = currentGroupId && select.value === String(currentGroupId);
      const targetGroupId = select.value;
      if (!targetGroupId) {
        state.moveSelections.delete(item.submissionId);
        moveStatus.textContent = "";
        return;
      }
      state.moveSelections.set(item.submissionId, targetGroupId);
      if (selectedIsCurrent) {
        moveStatus.textContent = "already in current group";
        return;
      }

      const targetGroup = state.groupOptions.find((group) => group.id === targetGroupId);
      moving = true;
      select.disabled = true;
      moveStatus.textContent = "moving...";
      try {
        await moveSubmissionToGroup(item.submissionId, targetGroupId);
        item.confirmedGroupId = targetGroupId;
        item.unconfirmedGroupId = null;
        state.moveSelections.delete(item.submissionId);
        refreshMoveSelectOptions(select, item, targetGroupId);
        moveStatus.textContent = targetGroup ? `moved to ${targetGroup.title}` : "moved";
        root.classList && root.classList.add("gradescope-ocr-moved");
        status.textContent = `moved ${item.submissionId}${targetGroup ? ` to ${targetGroup.title}` : ""}`;
      } catch (error) {
        state.moveSelections.delete(item.submissionId);
        select.value = "";
        moveStatus.textContent = `move failed: ${error.message || error}`;
      } finally {
        moving = false;
        select.disabled = false;
      }
    });
  }

  function refreshMoveSelectOptions(select, item, selectedValue = "") {
    const currentGroupId = currentGroupIdForItem(item);
    for (const option of select.options) {
      if (!option.value) {
        option.textContent = "Choose group...";
        continue;
      }
      const group = state.groupOptions.find((entry) => entry.id === option.value);
      if (!group) {
        continue;
      }
      const isCurrent = currentGroupId && group.id === String(currentGroupId);
      option.textContent = isCurrent ? `${group.title} (current)` : group.title;
    }
    select.value = selectedValue;
  }

  async function moveSubmissionToGroup(submissionId, answerGroupId) {
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;
    if (!csrfToken) {
      throw new Error("missing CSRF token");
    }

    const parsedGroupId = Number(answerGroupId);
    if (!Number.isFinite(parsedGroupId)) {
      throw new Error("invalid group id");
    }

    const parsedSubmissionId = Number(submissionId);
    if (!Number.isFinite(parsedSubmissionId)) {
      throw new Error("invalid submission id");
    }

    const response = await fetch(
      `/courses/${state.page.courseId}/questions/${state.page.questionId}/answer_group_memberships/many`,
      {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          "Accept": "application/json",
          "X-CSRF-Token": csrfToken,
          "X-Requested-With": "XMLHttpRequest"
        },
        body: JSON.stringify({
          answer_group_id: parsedGroupId,
          submission_ids: [parsedSubmissionId]
        })
      }
    );

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
  }

  function currentGroupIdForItem(item) {
    return item.confirmedGroupId ?? item.unconfirmedGroupId ?? state.page.answerGroupId ?? "";
  }

  function wireEvents() {
    collapseButton.addEventListener("click", async () => {
      state.prefs.collapsed = !state.prefs.collapsed;
      applyPrefs();
      await savePrefs();
    });

    closeButton.addEventListener("click", () => {
      host.remove();
    });

    copyButton.addEventListener("click", async () => {
      const text = state.entry ? state.entry.text || "" : "";
      if (!text) {
        status.textContent = "nothing to copy";
        return;
      }
      await navigator.clipboard.writeText(text);
      status.textContent = "copied";
      setTimeout(updateStatus, 1200);
    });

    reloadButton.addEventListener("click", async () => {
      state.index = null;
      await loadAndRender();
    });

    makeDraggable();
    watchViewportChanges();
    watchNavigation();
  }

  function watchViewportChanges() {
    const schedule = () => {
      if (!state.page || state.page.mode !== "group" || state.moveControlActive || state.inlineComplete) {
        return;
      }
      startInlineSyncWindow(5000);
      scheduleInlineGroupOcr(180);
    };
    document.addEventListener("scroll", schedule, { passive: true, capture: true });
    window.addEventListener("resize", schedule, { passive: true });
  }

  function scheduleInlineGroupOcr(delay = 100) {
    if (!state.page || state.page.mode !== "group" || state.moveControlActive) {
      return;
    }
    window.clearTimeout(state.inlineRenderTimer);
    state.inlineRenderTimer = window.setTimeout(syncInlineGroupOcr, delay);
  }

  function clearInlineRenderTimer() {
    window.clearTimeout(state.inlineRenderTimer);
    state.inlineRenderTimer = null;
    window.clearTimeout(state.inlineRetryTimer);
    state.inlineRetryTimer = null;
    state.inlineRetryUntil = 0;
  }

  function startInlineSyncWindow(duration = 15000) {
    state.inlineRetryUntil = Math.max(state.inlineRetryUntil || 0, Date.now() + duration);
  }

  function scheduleInlineRetry(delay = 400) {
    if (!state.page || state.page.mode !== "group" || state.moveControlActive) {
      return;
    }
    if (!state.inlineRetryUntil || Date.now() > state.inlineRetryUntil) {
      return;
    }
    window.clearTimeout(state.inlineRetryTimer);
    state.inlineRetryTimer = window.setTimeout(() => {
      state.inlineRetryTimer = null;
      scheduleInlineGroupOcr(0);
    }, delay);
  }

  function startLazyRenderObserver() {
    if (!state.page || state.page.mode !== "group" || state.moveControlActive || state.lazyObserver) {
      return;
    }

    const observer = new MutationObserver((mutations) => {
      if (state.moveControlActive) {
        return;
      }
      const hasAnswerChange = mutations.some((mutation) => {
        if (mutation.type === "childList") {
          return Array.from(mutation.addedNodes).some(nodeMayContainAnswerTarget);
        }
        return nodeMayContainAnswerTarget(mutation.target, false);
      });
      if (hasAnswerChange) {
        scheduleLazyRenderFromSignal();
      }
    });

    observer.observe(document.body || document.documentElement, {
      childList: true,
      subtree: true,
      attributes: true,
      attributeFilter: ["class", "style", "src", "href", "data-src", "data-original", "data-url", "data-background-image"]
    });

    state.lazyLoadHandler = (event) => {
      if (nodeMayContainAnswerTarget(event.target, false)) {
        scheduleLazyRenderFromSignal();
      }
    };
    document.addEventListener("load", state.lazyLoadHandler, true);

    state.lazyObserver = observer;
  }

  function stopLazyRenderObserver() {
    if (state.lazyObserver) {
      state.lazyObserver.disconnect();
      state.lazyObserver = null;
    }
    if (state.lazyLoadHandler) {
      document.removeEventListener("load", state.lazyLoadHandler, true);
      state.lazyLoadHandler = null;
    }
    window.clearTimeout(state.lazyObserverTimer);
    state.lazyObserverTimer = null;
    window.clearTimeout(state.lazyRenderSignalTimer);
    state.lazyRenderSignalTimer = null;
  }

  function scheduleLazyRenderFromSignal() {
    if (!state.page || state.page.mode !== "group" || state.moveControlActive) {
      return;
    }
    state.inlineComplete = false;
    startInlineSyncWindow(8000);
    window.clearTimeout(state.lazyRenderSignalTimer);
    state.lazyRenderSignalTimer = window.setTimeout(() => {
      state.lazyRenderSignalTimer = null;
      scheduleInlineGroupOcr(0);
    }, 180);
  }

  function nodeMayContainAnswerTarget(node, includeDescendants = true) {
    if (!node || node.nodeType !== Node.ELEMENT_NODE) {
      return false;
    }
    const element = node;
    if (
      element.id === HOST_ID ||
      element.id === "gradescope-ocr-inline-style" ||
      (element.closest && element.closest(`#${HOST_ID}, .gradescope-ocr-inline`))
    ) {
      return false;
    }
    if (element.matches && element.matches("img, canvas, image, svg image")) {
      return true;
    }
    if (hasAnswerishClass(element) || elementUrlAttributes(element).length) {
      return true;
    }
    if (extractCssUrls(element.style && element.style.backgroundImage).length) {
      return true;
    }
    if (!includeDescendants) {
      return false;
    }
    if (element.querySelector && element.querySelector("img, canvas, image, svg image")) {
      return true;
    }
    if (!element.querySelectorAll) {
      return false;
    }
    return Array.from(element.querySelectorAll("[class], [data-submission-id], [data-question-submission-id]"))
      .some((child) => hasAnswerishClass(child) || elementUrlAttributes(child).length);
  }

  function syncInlineGroupOcr() {
    if (state.moveControlActive) {
      return;
    }
    ensureInlineStyles();

    const totalWithOcr = state.groupEntries.filter((item) => item.entry).length;
    const gridRoots = findAnswerGridRoots();
    if (totalWithOcr > 0 && !gridRoots.length) {
      removeInlineGroupOcrOutsideRoots(gridRoots);
      state.inlineComplete = false;
      state.inlineStats = {
        inserted: 0,
        candidates: 0,
        total: totalWithOcr,
        waiting: true
      };
      scheduleInlineRetry(500);
      updateStatus();
      return;
    }

    removeInlineGroupOcrOutsideRoots(gridRoots);

    const attachment = selectAttachmentCandidates(findVisibleAnswerTargets(gridRoots), gridRoots.length > 0);
    const candidates = attachment.candidates;
    const usedTargets = new Set();
    const unmatchedItems = [];
    const placements = [];
    let inserted = 0;
    let usedFallback = false;

    for (const item of state.groupEntries) {
      if (!item.entry) {
        continue;
      }
      const target = findAnswerTarget(item, candidates, usedTargets, attachment.gridMode);
      if (!target) {
        unmatchedItems.push(item);
        continue;
      }
      usedTargets.add(target);
      placements.push({ item, target, matchMode: "exact" });
    }

    const remainingTargets = candidates
      .map((candidate) => candidate.target)
      .filter((target, index, targets) => !usedTargets.has(target) && targets.indexOf(target) === index);
    for (let i = 0; i < Math.min(unmatchedItems.length, remainingTargets.length); i += 1) {
      const item = unmatchedItems[i];
      const target = remainingTargets[i];
      usedTargets.add(target);
      placements.push({ item, target, matchMode: "visible-order" });
    }

    const placedIds = new Set();
    for (const placement of placements) {
      const card = placeInlineCard(placement.item, placement.target);
      card.dataset.matchMode = placement.matchMode;
      placedIds.add(placement.item.submissionId);
      inserted += 1;
    }
    removeUnplacedInlineCards(placedIds, gridRoots);

    if (!inserted && !attachment.gridMode && state.groupEntries.some((item) => item.entry)) {
      insertInlineFallbackList();
      inserted = state.groupEntries.filter((item) => item.entry).length;
      usedFallback = true;
    }

    const complete = !usedFallback && totalWithOcr > 0 && inserted >= totalWithOcr;
    state.inlineComplete = complete;
    state.inlineStats = {
      inserted,
      candidates: candidates.length,
      total: totalWithOcr
    };
    if (complete) {
      window.clearTimeout(state.inlineRetryTimer);
      state.inlineRetryTimer = null;
    } else {
      scheduleInlineRetry(700);
    }
    updateStatus();
  }

  function placeInlineCard(item, target) {
    const selector = `.gradescope-ocr-inline[data-submission-id="${CSS.escape(item.submissionId)}"]`;
    const existingCards = Array.from(document.querySelectorAll(selector));
    const card = existingCards.shift() || createInlineCard(item);
    for (const duplicate of existingCards) {
      duplicate.remove();
    }
    if (card.previousElementSibling !== target) {
      target.insertAdjacentElement("afterend", card);
    }
    return card;
  }

  function removeInlineGroupOcrOutsideRoots(gridRoots) {
    document.querySelectorAll(".gradescope-ocr-inline-fallback").forEach((node) => node.remove());
    const roots = gridRoots || [];
    if (!roots.length) {
      document.querySelectorAll(".gradescope-ocr-inline").forEach((node) => node.remove());
      return;
    }
    document.querySelectorAll(".gradescope-ocr-inline").forEach((node) => {
      if (!roots.some((root) => root.contains(node))) {
        node.remove();
      }
    });
  }

  function removeUnplacedInlineCards(placedIds, gridRoots) {
    const roots = gridRoots || [];
    document.querySelectorAll(".gradescope-ocr-inline:not(.gradescope-ocr-inline-fallback)").forEach((node) => {
      const submissionId = node.dataset.submissionId || "";
      const inCurrentGrid = !roots.length || roots.some((root) => root.contains(node));
      if (inCurrentGrid && !placedIds.has(submissionId)) {
        node.remove();
      }
    });
  }

  function removeInlineGroupOcr() {
    document.querySelectorAll(".gradescope-ocr-inline").forEach((node) => node.remove());
  }

  function findAnswerTarget(item, candidates, usedTargets, gridMode) {
    const itemPaths = new Set([item.cropPath, urlPath(item.cropUrl)].filter(Boolean));
    const exact = candidates.find((candidate) => {
      return !usedTargets.has(candidate.target) && [...candidate.paths].some((path) => itemPaths.has(path));
    });
    if (exact) {
      return exact.target;
    }

    if (gridMode) {
      return null;
    }

    const link = document.querySelector(`a[href*="/submissions/${CSS.escape(item.submissionId)}/"]`);
    if (link) {
      return placementTargetFromElement(link);
    }
    return null;
  }

  function findVisibleAnswerTargets(gridRoots = []) {
    const candidates = [];
    const seen = new Set();
    const roots = gridRoots.length ? gridRoots : [document.body];

    for (const root of roots) {
      for (const image of root.querySelectorAll("img")) {
        addCandidate(image, elementUrlAttributes(image), "image");
      }

      for (const image of root.querySelectorAll("svg image, image")) {
        addCandidate(image, elementUrlAttributes(image), "svg-image");
      }

      for (const element of root.querySelectorAll("*")) {
        if (element.closest(`#${HOST_ID}, .gradescope-ocr-inline`)) {
          continue;
        }
        const inlineUrls = extractCssUrls(element.style && element.style.backgroundImage);
        const computedUrls = extractCssUrls(window.getComputedStyle(element).backgroundImage);
        const attrUrls = elementUrlAttributes(element);
        const urls = [...inlineUrls, ...computedUrls, ...attrUrls];
        if (urls.length) {
          addCandidate(element, urls, "element-url");
        }
        if (element.tagName.toLowerCase() === "canvas") {
          addCandidate(element, [], "canvas", true);
        } else if (isSemanticAnswerTarget(element)) {
          addCandidate(element, [], "semantic", true);
        }
      }
    }

    return candidates;

    function addCandidate(element, urls, source, allowWithoutUrl = false) {
      if (!isVisibleAnswerElement(element)) {
        return;
      }
      if (allowWithoutUrl && !isPlausibleFallbackElement(element, source)) {
        return;
      }
      const paths = new Set(urls.map(urlPath).filter(Boolean));
      if (!paths.size && !allowWithoutUrl) {
        return;
      }
      const target = placementTargetFromElement(element);
      if (!target || seen.has(target)) {
        return;
      }
      seen.add(target);
      candidates.push({ element, target, paths, source, rect: target.getBoundingClientRect() });
    }
  }

  function findAnswerGridRoots() {
    const roots = [];
    for (const element of document.querySelectorAll(".answerGroupCard--submissions.js-answersContainer, .answerGroupCard--submissions")) {
      if (element.closest(`#${HOST_ID}, .gradescope-ocr-inline`)) {
        continue;
      }
      const rect = element.getBoundingClientRect();
      const styles = window.getComputedStyle(element);
      const hasAnswerTiles = Boolean(element.querySelector(".answerRegion, .answerRegion--image, img, canvas, image, svg image"));
      if (
        hasAnswerTiles &&
        rect.width > 0 &&
        styles.display !== "none" &&
        styles.visibility !== "hidden" &&
        !roots.includes(element)
      ) {
        roots.push(element);
      }
    }
    return roots;
  }

  function selectAttachmentCandidates(candidates, hasGridRoot = false) {
    const sorted = [...candidates].sort((a, b) => a.rect.top - b.rect.top || a.rect.left - b.rect.left);
    if (hasGridRoot) {
      return { candidates: sorted, gridMode: true };
    }

    const gridStartY = findAnswerGridStartY() ?? inferAnswerGridStartY(sorted);
    if (gridStartY !== null) {
      const gridCandidates = sorted.filter((candidate) => candidate.rect.top >= gridStartY - 8);
      return { candidates: gridCandidates, gridMode: true };
    }

    const totalWithOcr = state.groupEntries.filter((item) => item.entry).length;
    if (totalWithOcr > 0) {
      return { candidates: [], gridMode: true };
    }

    return { candidates: sorted, gridMode: false };
  }

  function inferAnswerGridStartY(candidates) {
    const rows = [];
    for (const candidate of candidates) {
      if (!isGridSizedCandidate(candidate)) {
        continue;
      }
      let row = rows.find((existing) => Math.abs(existing.top - candidate.rect.top) <= 48);
      if (!row) {
        row = { top: candidate.rect.top, candidates: [] };
        rows.push(row);
      }
      row.candidates.push(candidate);
      row.top = Math.min(row.top, candidate.rect.top);
    }

    rows.sort((a, b) => a.top - b.top);
    for (const row of rows) {
      const columns = uniqueColumns(row.candidates);
      if (columns.length >= 2) {
        return row.top;
      }
    }
    return null;
  }

  function isGridSizedCandidate(candidate) {
    const rect = candidate.rect;
    return (
      rect.width >= 240 &&
      rect.height >= 140 &&
      rect.width <= Math.max(1100, window.innerWidth * 0.65) &&
      rect.height <= 900
    );
  }

  function uniqueColumns(candidates) {
    const columns = [];
    for (const candidate of candidates) {
      if (!columns.some((left) => Math.abs(left - candidate.rect.left) <= 80)) {
        columns.push(candidate.rect.left);
      }
    }
    return columns;
  }

  function findAnswerGridStartY() {
    let bottom = null;
    for (const element of document.querySelectorAll("body *")) {
      if (element.closest(`#${HOST_ID}, .gradescope-ocr-inline`)) {
        continue;
      }
      const text = String(element.textContent || "").replace(/\s+/g, " ").trim();
      if (!/(^|\s)Confirmed\s+\d+($|\s)/.test(text)) {
        continue;
      }
      const rect = element.getBoundingClientRect();
      const styles = window.getComputedStyle(element);
      if (
        rect.width > 0 &&
        rect.height > 0 &&
        rect.width <= 520 &&
        rect.height <= 120 &&
        styles.display !== "none" &&
        styles.visibility !== "hidden"
      ) {
        bottom = Math.max(bottom ?? rect.bottom, rect.bottom);
      }
    }
    return bottom;
  }

  function elementUrlAttributes(element) {
    const urls = [];
    for (const attr of ["currentSrc", "src", "href"]) {
      if (element[attr]) {
        urls.push(String(element[attr]));
      }
    }
    for (const attr of ["src", "href", "xlink:href", "data-src", "data-original", "data-url", "data-background-image"]) {
      const value = element.getAttribute && element.getAttribute(attr);
      if (value) {
        urls.push(value);
      }
    }
    return urls;
  }

  function hasAnswerishClass(element) {
    const className = typeof element.className === "string"
      ? element.className
      : String(element.getAttribute("class") || "");
    return /(answer|submission|crop|question-submission|react-grid-item)/i.test(className);
  }

  function isSemanticAnswerTarget(element) {
    const className = typeof element.className === "string"
      ? element.className
      : String(element.getAttribute("class") || "");
    return /(^|\s)(answerRegion|answerRegion--image)(\s|$)|question-submission|react-grid-item|(^|\s)(crop|masked-crop)(\s|$)/i.test(className);
  }

  function isVisibleAnswerElement(element) {
    if (!element || element.closest(`#${HOST_ID}, .gradescope-ocr-inline`)) {
      return false;
    }
    const rect = element.getBoundingClientRect();
    const styles = window.getComputedStyle(element);
    return (
      rect.width >= 80 &&
      rect.height >= 45 &&
      rect.right >= 0 &&
      styles.display !== "none" &&
      styles.visibility !== "hidden" &&
      Number(styles.opacity || 1) !== 0
    );
  }

  function isPlausibleFallbackElement(element, source) {
    if (source === "canvas") {
      return true;
    }
    const rect = element.getBoundingClientRect();
    const maxWidth = Math.max(900, window.innerWidth * 0.55);
    return rect.width <= maxWidth && rect.height <= 900;
  }

  function placementTargetFromElement(element) {
    let target = element;
    let current = element;
    const base = element.getBoundingClientRect();

    for (let depth = 0; depth < 6 && current.parentElement; depth += 1) {
      const parent = current.parentElement;
      if (parent === document.body || parent.id === "main-content") {
        break;
      }
      const rect = parent.getBoundingClientRect();
      if (
        rect.width >= base.width &&
        rect.height >= base.height &&
        rect.width <= Math.max(900, window.innerWidth * 0.55) &&
        rect.height <= 900
      ) {
        target = parent;
        current = parent;
        continue;
      }
      break;
    }

    return target;
  }

  function extractCssUrls(value) {
    const urls = [];
    const source = String(value || "");
    const pattern = /url\((?:"([^"]+)"|'([^']+)'|([^)]*))\)/g;
    let match;
    while ((match = pattern.exec(source)) !== null) {
      urls.push(match[1] || match[2] || match[3] || "");
    }
    return urls;
  }

  function createInlineCard(item) {
    const card = document.createElement("aside");
    card.className = "gradescope-ocr-inline";
    card.dataset.submissionId = item.submissionId;
    const text = item.entry.text || "";
    card.innerHTML = `
      <div class="gradescope-ocr-inline-header">
        <strong>OCR ${escapeHtml(item.submissionId)}</strong>
        <button type="button">Copy</button>
      </div>
      <div class="gradescope-ocr-rendered">${renderOcrText(text)}</div>
      ${renderMoveControlHtml(item)}
    `;
    for (const eventName of ["click", "mousedown", "pointerdown"]) {
      card.addEventListener(eventName, (event) => {
        event.stopPropagation();
      });
    }
    card.querySelector("button").addEventListener("click", async () => {
      await navigator.clipboard.writeText(text);
      const button = card.querySelector("button");
      button.textContent = "Copied";
      window.setTimeout(() => {
        button.textContent = "Copy";
      }, 1000);
    });
    wireMoveControls(card, item);
    return card;
  }

  function insertInlineFallbackList() {
    const anchor = document.querySelector("#main-content") || document.body;
    const wrapper = document.createElement("section");
    wrapper.className = "gradescope-ocr-inline gradescope-ocr-inline-fallback";
    const cards = state.groupEntries
      .filter((item) => item.entry)
      .map((item) => `
        <details>
          <summary>OCR ${escapeHtml(item.submissionId)}</summary>
          <div class="gradescope-ocr-rendered">${renderOcrText(item.entry.text || "")}</div>
        </details>
      `)
      .join("");
    wrapper.innerHTML = `
      <div class="gradescope-ocr-inline-header">
        <strong>OCR transcriptions</strong>
      </div>
      ${cards}
    `;
    anchor.insertAdjacentElement("afterbegin", wrapper);
  }

  function ensureInlineStyles() {
    if (document.getElementById("gradescope-ocr-inline-style")) {
      return;
    }
    const style = document.createElement("style");
    style.id = "gradescope-ocr-inline-style";
    style.textContent = `
      .gradescope-ocr-inline {
        box-sizing: border-box;
        width: min(100%, 760px);
        margin: 10px 0 18px;
        border: 1px solid rgba(20, 24, 35, 0.16);
        border-radius: 8px;
        background: #fffdf6;
        box-shadow: 0 8px 24px rgba(20, 24, 35, 0.12);
        color: #111827;
        font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      }

      .gradescope-ocr-moved {
        opacity: 0.72;
      }

      .gradescope-ocr-inline-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 10px;
        padding: 8px 10px;
        border-bottom: 1px solid rgba(20, 24, 35, 0.10);
        background: #fff7d6;
        font-size: 12px;
      }

      .gradescope-ocr-inline-header button {
        border: 1px solid rgba(20, 24, 35, 0.18);
        border-radius: 6px;
        background: #fff;
        color: #111827;
        font-size: 12px;
        font-weight: 600;
        padding: 5px 8px;
        cursor: pointer;
      }

      .gradescope-ocr-move {
        display: grid;
        grid-template-columns: auto minmax(140px, 1fr);
        gap: 6px;
        align-items: center;
        padding: 8px 10px;
        border-top: 1px solid rgba(20, 24, 35, 0.10);
        background: #fffaf0;
      }

      .gradescope-ocr-move-label,
      .gradescope-ocr-move-status {
        color: #6b7280;
        font-size: 11px;
        white-space: nowrap;
      }

      .gradescope-ocr-move-select {
        min-width: 0;
        border: 1px solid rgba(20, 24, 35, 0.18);
        border-radius: 6px;
        background: #fff;
        color: #111827;
        font-size: 12px;
        padding: 6px 8px;
      }

      .gradescope-ocr-move-status {
        grid-column: 2 / 3;
        overflow: hidden;
        text-overflow: ellipsis;
      }

      .gradescope-ocr-rendered {
        box-sizing: border-box;
        max-height: 220px;
        padding: 10px;
        overflow: auto;
        white-space: pre-wrap;
        color: #111827;
        font-size: 12px;
        line-height: 1.45;
      }

      .gradescope-ocr-rendered .math {
        font-family: "Times New Roman", Cambria, Georgia, serif;
        font-size: 1.08em;
      }

      .gradescope-ocr-rendered .math-inline {
        display: inline;
        padding: 0 2px;
      }

      .gradescope-ocr-rendered .math-display {
        display: block;
        margin: 8px 0;
        padding: 8px 10px;
        overflow-x: auto;
        border-radius: 6px;
        background: #fff;
        text-align: center;
      }

      .gradescope-ocr-rendered .math-frac {
        display: inline-flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        vertical-align: middle;
        margin: 0 2px;
      }

      .gradescope-ocr-rendered .math-frac > .num {
        padding: 0 3px 1px;
        border-bottom: 1px solid currentColor;
        line-height: 1.1;
      }

      .gradescope-ocr-rendered .math-frac > .den {
        padding: 1px 3px 0;
        line-height: 1.1;
      }

      .gradescope-ocr-rendered .math-hat {
        text-decoration: overline;
        text-decoration-thickness: 1px;
      }

      .gradescope-ocr-inline-fallback {
        margin: 16px;
      }

      .gradescope-ocr-inline-fallback details {
        border-top: 1px solid rgba(20, 24, 35, 0.10);
      }

      .gradescope-ocr-inline-fallback summary {
        cursor: pointer;
        padding: 8px 10px;
        font-size: 12px;
        font-weight: 650;
      }
    `;
    document.head.appendChild(style);
  }

  function makeDraggable() {
    let start = null;

    header.addEventListener("pointerdown", (event) => {
      if (event.target.closest("button")) return;
      const rect = panel.getBoundingClientRect();
      start = {
        pointerId: event.pointerId,
        x: event.clientX,
        y: event.clientY,
        top: rect.top,
        left: rect.left
      };
      header.setPointerCapture(event.pointerId);
    });

    header.addEventListener("pointermove", (event) => {
      if (!start || event.pointerId !== start.pointerId) return;
      const nextTop = clamp(start.top + event.clientY - start.y, 8, window.innerHeight - 48);
      const nextLeft = clamp(start.left + event.clientX - start.x, 8, window.innerWidth - 96);
      panel.style.top = `${nextTop}px`;
      panel.style.left = `${nextLeft}px`;
      panel.style.right = "auto";
      state.prefs.top = Math.round(nextTop);
      state.prefs.left = Math.round(nextLeft);
      delete state.prefs.right;
    });

    header.addEventListener("pointerup", async (event) => {
      if (!start || event.pointerId !== start.pointerId) return;
      start = null;
      await savePrefs();
    });
  }

  function watchNavigation() {
    let lastPathname = window.location.pathname;
    window.setInterval(async () => {
      if (window.location.pathname === lastPathname) {
        return;
      }
      lastPathname = window.location.pathname;
      const nextPage = parsePage();
      state.page = nextPage;
      state.selectedSubmissionId = nextPage ? nextPage.submissionId : null;
      await loadAndRender();
    }, 750);
  }

  function updateStatus() {
    if (!state.entry) {
      status.textContent = state.page.mode === "group" ? `${state.groupEntries.length} submissions` : "missing";
      return;
    }
    const text = state.entry.text || "";
    const submissionId = state.entry.submission_id || state.selectedSubmissionId || state.page.submissionId;
    const inlineSuffix = state.page.mode === "group" && state.inlineStats
      ? ` · ${state.inlineStats.inserted}/${state.inlineStats.total} cards`
      : "";
    status.textContent = `${submissionId} · ${text.length.toLocaleString()} chars${inlineSuffix}`;
  }

  function applyPrefs() {
    panel.classList.toggle("collapsed", Boolean(state.prefs.collapsed));
    collapseButton.textContent = state.prefs.collapsed ? "+" : "−";
    if (typeof state.prefs.top === "number") {
      panel.style.top = `${state.prefs.top}px`;
    }
    if (typeof state.prefs.left === "number") {
      panel.style.left = `${state.prefs.left}px`;
      panel.style.right = "auto";
    } else if (typeof state.prefs.right === "number") {
      panel.style.right = `${state.prefs.right}px`;
      panel.style.left = "auto";
    }
    if (typeof state.prefs.width === "number") {
      panel.style.width = `min(${state.prefs.width}px, calc(100vw - 32px))`;
    }
  }

  async function loadPrefs() {
    try {
      const result = await chrome.storage.local.get(STORAGE_KEY);
      return result[STORAGE_KEY] || {};
    } catch (_error) {
      return {};
    }
  }

  async function savePrefs() {
    try {
      await chrome.storage.local.set({ [STORAGE_KEY]: state.prefs });
    } catch (_error) {
      // Preferences are nice to have; the overlay still works without them.
    }
  }

  function parsePage() {
    const gradeMatch = window.location.pathname.match(GRADE_URL_PATTERN);
    if (gradeMatch && gradeMatch.groups) {
      return {
        mode: "grade",
        courseId: gradeMatch.groups.courseId,
        questionId: gradeMatch.groups.questionId,
        submissionId: gradeMatch.groups.submissionId,
        answerGroupId: null
      };
    }

    const groupMatch = window.location.pathname.match(GROUP_URL_PATTERN);
    if (groupMatch && groupMatch.groups) {
      return {
        mode: "group",
        courseId: groupMatch.groups.courseId,
        questionId: groupMatch.groups.questionId,
        submissionId: null,
        answerGroupId: groupMatch.groups.answerGroupId || null
      };
    }

    return null;
  }

  function isExcludedAnswerGroupPage() {
    return (
      GROUPS_INDEX_URL_PATTERN.test(window.location.pathname) ||
      UNGROUPED_URL_PATTERN.test(window.location.pathname)
    );
  }

  function clamp(value, min, max) {
    return Math.max(min, Math.min(max, value));
  }

  function urlPath(value) {
    try {
      return new URL(value, window.location.href).pathname;
    } catch (_error) {
      return "";
    }
  }

  function renderOcrText(text) {
    const source = String(text || "").replace(/\r\n?/g, "\n");
    let html = "";
    let cursor = 0;
    const mathPattern = /\\\[((?:.|\n)*?)\\\]|\$\$((?:.|\n)*?)\$\$|\\\(((?:.|\n)*?)\\\)/g;
    let match;

    while ((match = mathPattern.exec(source)) !== null) {
      html += renderPlainText(source.slice(cursor, match.index));
      const display = match[1] !== undefined || match[2] !== undefined;
      const expression = match[1] ?? match[2] ?? match[3] ?? "";
      html += display
        ? `<span class="math math-display">${renderMathExpression(expression)}</span>`
        : `<span class="math math-inline">${renderMathExpression(expression)}</span>`;
      cursor = mathPattern.lastIndex;
    }

    html += renderPlainText(source.slice(cursor));
    return html;
  }

  function renderPlainText(text) {
    return String(text || "")
      .split("\n")
      .map((line) => {
        return looksLikeLatexLine(line)
          ? `<span class="math math-display">${renderMathExpression(line)}</span>`
          : escapeHtml(line);
      })
      .join("<br>");
  }

  function looksLikeLatexLine(line) {
    const trimmed = String(line || "").trim();
    if (!trimmed || trimmed.length > 180) {
      return false;
    }
    return /\\(frac|hat|bar|beta|alpha|gamma|delta|theta|lambda|mu|rho|sigma|phi|omega|text|operatorname|leq|geq|neq|approx|cdot|times)|[_^]\{/.test(trimmed);
  }

  function renderMathExpression(source) {
    const text = String(source || "")
      .replace(/\n+/g, " ")
      .replace(/\\left/g, "")
      .replace(/\\right/g, "")
      .trim();

    let html = "";
    let cursor = 0;

    while (cursor < text.length) {
      const fracIndex = text.indexOf("\\frac", cursor);
      if (fracIndex === -1) {
        html += renderMathChunk(text.slice(cursor));
        break;
      }

      html += renderMathChunk(text.slice(cursor, fracIndex));
      const numerator = readLatexGroup(text, fracIndex + "\\frac".length);
      if (!numerator) {
        html += renderMathChunk("\\frac");
        cursor = fracIndex + "\\frac".length;
        continue;
      }
      const denominator = readLatexGroup(text, numerator.end);
      if (!denominator) {
        html += renderMathChunk(text.slice(fracIndex, numerator.end));
        cursor = numerator.end;
        continue;
      }

      html += `<span class="math-frac"><span class="num">${renderMathExpression(numerator.body)}</span><span class="den">${renderMathExpression(denominator.body)}</span></span>`;
      cursor = denominator.end;
    }

    return html;
  }

  function renderMathChunk(source) {
    let html = escapeHtml(source || "");

    html = html
      .replace(/\\text\{([^{}]*)\}/g, "$1")
      .replace(/\\operatorname\{([^{}]*)\}/g, "$1")
      .replace(/\\hat\{([^{}]+)\}/g, '<span class="math-hat">$1</span>')
      .replace(/\\bar\{([^{}]+)\}/g, '<span class="math-hat">$1</span>')
      .replace(/\\quad|\\qquad|\\,/g, " ")
      .replace(/\\cdot/g, "·")
      .replace(/\\times/g, "×")
      .replace(/\\pm/g, "±")
      .replace(/\\leq?/g, "≤")
      .replace(/\\geq?/g, "≥")
      .replace(/\\neq/g, "≠")
      .replace(/\\approx/g, "≈")
      .replace(/\\infty/g, "∞")
      .replace(/\\rightarrow|\\to/g, "→")
      .replace(/\\leftarrow/g, "←")
      .replace(/\\alpha/g, "α")
      .replace(/\\beta/g, "β")
      .replace(/\\gamma/g, "γ")
      .replace(/\\delta/g, "δ")
      .replace(/\\epsilon|\\varepsilon/g, "ε")
      .replace(/\\theta/g, "θ")
      .replace(/\\lambda/g, "λ")
      .replace(/\\mu/g, "μ")
      .replace(/\\rho/g, "ρ")
      .replace(/\\sigma/g, "σ")
      .replace(/\\tau/g, "τ")
      .replace(/\\phi|\\varphi/g, "φ")
      .replace(/\\omega/g, "ω");

    html = html
      .replace(/([A-Za-z0-9α-ωΑ-Ωβθμρσφω]+)_\{([^{}]+)\}/g, "$1<sub>$2</sub>")
      .replace(/([A-Za-z0-9α-ωΑ-Ωβθμρσφω]+)\^\{([^{}]+)\}/g, "$1<sup>$2</sup>")
      .replace(/([A-Za-z0-9α-ωΑ-Ωβθμρσφω]+)_([A-Za-z0-9]+)/g, "$1<sub>$2</sub>")
      .replace(/([A-Za-z0-9α-ωΑ-Ωβθμρσφω]+)\^([A-Za-z0-9+\-]+)/g, "$1<sup>$2</sup>")
      .replace(/[{}]/g, "")
      .replace(/\\([A-Za-z]+)/g, "$1");

    return html;
  }

  function readLatexGroup(text, start) {
    let index = start;
    while (index < text.length && /\s/.test(text[index])) {
      index += 1;
    }
    if (text[index] !== "{") {
      return null;
    }

    let depth = 0;
    for (let i = index; i < text.length; i += 1) {
      if (text[i] === "{") depth += 1;
      if (text[i] === "}") depth -= 1;
      if (depth === 0) {
        return {
          body: text.slice(index + 1, i),
          end: i + 1
        };
      }
    }

    return null;
  }

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }
})();
