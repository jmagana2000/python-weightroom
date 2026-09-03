const levelTabs = document.getElementById("level-tabs");
const levelProgress = document.getElementById("level-progress");
const dueBadge = document.getElementById("due-badge");
const exerciseList = document.getElementById("exercise-list");
const exerciseSearch = document.getElementById("exercise-search");
const workspace = document.getElementById("workspace");
const emptyState = document.getElementById("empty-state");
const exTitle = document.getElementById("ex-title");
const exTopics = document.getElementById("ex-topics");
const exPrompt = document.getElementById("ex-prompt");
const exExample = document.getElementById("ex-example");
const exHiddenCount = document.getElementById("ex-hidden-count");
const hintToggle = document.getElementById("hint-toggle");
const exHint = document.getElementById("ex-hint");
const runBtn = document.getElementById("run-btn");
const runBtnSpinner = document.getElementById("run-btn-spinner");
const runBtnLabel = document.getElementById("run-btn-label");
const resetBtn = document.getElementById("reset-btn");
const exResults = document.getElementById("ex-results");
const levelUpBanner = document.getElementById("level-up-banner");
const offlineBanner = document.getElementById("offline-banner");

let progress = null;
let currentExercise = null;
let exerciseCache = new Map();
let editor = null;

async function api(path, options) {
  let res;
  try {
    res = await fetch(path, options);
  } catch (networkErr) {
    offlineBanner.classList.remove("hidden");
    throw networkErr;
  }
  offlineBanner.classList.add("hidden");
  const contentType = res.headers.get("content-type") || "";
  if (!contentType.includes("application/json")) {
    const text = await res.text();
    throw new Error(
      `Server returned ${res.status} (not JSON) — ${text.slice(0, 200)}`
    );
  }
  const body = await res.json();
  if (!res.ok) throw new Error(body.error || `Request failed (${res.status})`);
  return body;
}

function getEditor() {
  if (typeof CodeMirror === "undefined") {
    throw new Error(
      "Code editor failed to load (CodeMirror script blocked or offline). Check your internet connection and reload."
    );
  }
  if (!editor) {
    editor = CodeMirror(document.getElementById("editor-host"), {
      mode: "python",
      theme: "eclipse",
      lineNumbers: true,
      indentUnit: 4,
      tabSize: 4,
      indentWithTabs: false,
      extraKeys: { Tab: (cm) => cm.replaceSelection("    ", "end") },
    });
  }
  return editor;
}

async function loadProgress() {
  progress = await api("/api/progress");
}

function renderLevelTabs() {
  levelTabs.querySelectorAll(".level-tab").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.level === progress.level);
  });
}

async function renderLevelProgress() {
  const exercises = await getExercisesForLevel(progress.level);
  const solvedCount = exercises.filter((e) => progress.solved.includes(e.id)).length;
  levelProgress.textContent = `${solvedCount} / ${exercises.length} solved`;
}

function renderDueBadge() {
  const count = (progress.due_for_review || []).length;
  dueBadge.classList.toggle("hidden", count === 0);
  dueBadge.textContent = `📌 ${count} due for review`;
}

async function getExercisesForLevel(level) {
  if (!exerciseCache.has(level)) {
    exerciseCache.set(level, await api(`/api/exercises?level=${level}`));
  }
  return exerciseCache.get(level);
}

function clusterOpenKey(level, cluster) {
  return `wr-open-${level}-${cluster}`;
}

function isClusterOpen(level, cluster, hasActiveExercise) {
  const stored = localStorage.getItem(clusterOpenKey(level, cluster));
  if (stored !== null) return stored === "1";
  return hasActiveExercise; // first time seeing this cluster: start collapsed unless it holds the open exercise
}

async function loadExercises(level) {
  const exercises = await getExercisesForLevel(level);
  const due = new Set(progress.due_for_review || []);

  const groups = new Map(); // cluster name -> exercises[]
  for (const ex of exercises) {
    const cluster = ex.cluster || "Other";
    if (!groups.has(cluster)) groups.set(cluster, []);
    groups.get(cluster).push(ex);
  }

  exerciseList.innerHTML = "";
  for (const [cluster, exList] of groups) {
    const solvedCount = exList.filter((e) => progress.solved.includes(e.id)).length;
    const hasActive = !!currentExercise && exList.some((e) => e.id === currentExercise.id);

    const section = document.createElement("details");
    section.className = "cluster-section";
    section.dataset.cluster = cluster;
    section.open = isClusterOpen(level, cluster, hasActive);
    section.addEventListener("toggle", () => {
      localStorage.setItem(clusterOpenKey(level, cluster), section.open ? "1" : "0");
    });

    const summary = document.createElement("summary");
    summary.className = "cluster-summary";
    summary.innerHTML = `
      <svg class="cluster-chevron" viewBox="0 0 16 16" width="10" height="10" aria-hidden="true">
        <path d="M5 2l6 6-6 6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
      <span class="cluster-name"></span>
      <span class="cluster-count${solvedCount === exList.length ? " complete" : ""}"></span>`;
    summary.querySelector(".cluster-name").textContent = cluster;
    summary.querySelector(".cluster-count").textContent = `${solvedCount}/${exList.length}`;
    section.appendChild(summary);

    const itemsHost = document.createElement("div");
    itemsHost.className = "cluster-items";
    for (const ex of exList) {
      const item = document.createElement("div");
      const solved = progress.solved.includes(ex.id);
      const isDue = due.has(ex.id);
      item.className = "exercise-item" + (solved ? " solved" : "");
      item.dataset.id = ex.id;
      item.dataset.search = `${ex.title} ${(ex.topics || []).join(" ")} ${cluster}`.toLowerCase();
      if (currentExercise && currentExercise.id === ex.id) item.classList.add("active");
      item.innerHTML = `
        <span class="exercise-check">${solved ? "✓" : ""}</span>
        <span class="exercise-item-body">
          <span class="exercise-title"></span>
          <span class="exercise-topics"></span>
        </span>
        ${isDue ? '<span class="due-dot" title="Due for review">📌</span>' : ""}`;
      item.querySelector(".exercise-title").textContent = ex.title;
      item.querySelector(".exercise-topics").textContent = (ex.topics || []).join(" · ");
      item.onclick = () => openExercise(ex.id);
      itemsHost.appendChild(item);
    }
    section.appendChild(itemsHost);
    exerciseList.appendChild(section);
  }

  filterExercises(exerciseSearch.value);
  await renderLevelProgress();
  renderDueBadge();
}

function filterExercises(rawQuery) {
  const query = rawQuery.trim().toLowerCase();
  const sections = exerciseList.querySelectorAll(".cluster-section");
  if (!query) {
    sections.forEach((section) => {
      section.classList.remove("hidden");
      section.querySelectorAll(".exercise-item").forEach((item) => item.classList.remove("hidden"));
    });
    return;
  }
  sections.forEach((section) => {
    let anyVisible = false;
    section.querySelectorAll(".exercise-item").forEach((item) => {
      const match = item.dataset.search.includes(query);
      item.classList.toggle("hidden", !match);
      if (match) anyVisible = true;
    });
    section.classList.toggle("hidden", !anyVisible);
    if (anyVisible) section.open = true;
  });
}

exerciseSearch.oninput = () => filterExercises(exerciseSearch.value);

function formatExampleValue(v) {
  return JSON.stringify(v);
}

async function openExercise(id) {
  try {
    const ex = await api(`/api/exercises/${id}`);
    currentExercise = ex;

    exerciseList.querySelectorAll(".exercise-item").forEach((el) => el.classList.remove("active"));
    const activeItem = exerciseList.querySelector(`.exercise-item[data-id="${CSS.escape(id)}"]`);
    if (activeItem) {
      activeItem.classList.add("active");
      const section = activeItem.closest(".cluster-section");
      if (section) section.open = true;
    }

    exTitle.textContent = ex.title;
    exTopics.innerHTML = (ex.topics || [])
      .map((t) => `<span class="chip">${escapeHtml(t)}</span>`)
      .join("");
    exPrompt.textContent = ex.prompt;

    const args = ex.example.args.map(formatExampleValue).join(", ");
    exExample.textContent =
      `${ex.func_name}(${args})\n-> ${formatExampleValue(ex.example.expected)}`;
    exHiddenCount.textContent =
      ex.hidden_test_count > 0
        ? `+ ${ex.hidden_test_count} more hidden test${ex.hidden_test_count === 1 ? "" : "s"} run on submit`
        : "";

    if (ex.hint) {
      hintToggle.classList.remove("hidden");
      hintToggle.textContent = "Show hint";
      exHint.textContent = ex.hint;
      exHint.classList.add("hidden");
    } else {
      hintToggle.classList.add("hidden");
      exHint.classList.add("hidden");
    }

    exResults.innerHTML = "";
    emptyState.classList.add("hidden");
    workspace.classList.remove("hidden");
    getEditor().setValue(ex.starter_code);
    getEditor().refresh();
  } catch (err) {
    emptyState.classList.add("hidden");
    workspace.classList.remove("hidden");
    showGlobalError(err);
  }
}

hintToggle.onclick = () => {
  const showing = !exHint.classList.contains("hidden");
  exHint.classList.toggle("hidden", showing);
  hintToggle.textContent = showing ? "Show hint" : "Hide hint";
};

resetBtn.onclick = () => {
  if (currentExercise) getEditor().setValue(currentExercise.starter_code);
};

async function runTests() {
  if (!currentExercise) return;
  runBtn.disabled = true;
  runBtnSpinner.classList.remove("hidden");
  runBtnLabel.textContent = "Running…";
  try {
    const res = await api(`/api/exercises/${currentExercise.id}/submit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code: getEditor().getValue() }),
    });
    renderResults(res);
    const wasAlreadySolved = progress.solved.includes(currentExercise.id);
    if (res.solved || wasAlreadySolved) {
      // Either newly solved (checkmark) or a review re-attempt (review
      // schedule changed either way) -- refresh progress from the server
      // rather than guessing the new review state client-side.
      progress = await api("/api/progress");
      exerciseCache.delete(progress.level);
      await loadExercises(progress.level);
    }
    if (res.level_up_available) {
      levelUpBanner.textContent = `Ready for ${res.level_up_available} — click to switch`;
      levelUpBanner.classList.remove("hidden");
      levelUpBanner.onclick = () => setLevel(res.level_up_available);
    }
  } catch (err) {
    exResults.innerHTML = `<div class="error-box">Couldn't run your code: ${escapeHtml(err.message)}</div>`;
  } finally {
    runBtn.disabled = false;
    runBtnSpinner.classList.add("hidden");
    runBtnLabel.textContent = "Run Tests";
  }
}

function renderResults(res) {
  const { outcome } = res;
  if (outcome.status === "timeout") {
    exResults.innerHTML = `<div class="error-box">Time limit exceeded — check for an infinite loop.</div>`;
    return;
  }
  if (outcome.status === "error") {
    exResults.innerHTML = `<div class="error-box">${escapeHtml(outcome.message || "Something went wrong running your code.")}</div>`;
    return;
  }
  const results = outcome.results;
  const passCount = results.filter((r) => r.passed).length;
  const allPass = passCount === results.length;
  const summary = `<div class="result-summary ${allPass ? "all-pass" : "some-fail"}">${
    allPass ? "✓ " : ""
  }${passCount} / ${results.length} tests passed</div>`;
  const rows = results
    .map((r, i) => {
      if (r.passed) {
        const detail = `got ${JSON.stringify(r.actual)}`;
        return `<div class="test-row pass"><span class="test-icon">✓</span><span>Test ${i + 1}<div class="test-detail">${escapeHtml(detail)}</div></span></div>`;
      }
      const detail = r.error
        ? r.error
        : `got ${JSON.stringify(r.actual)}, expected ${JSON.stringify(r.expected)}`;
      return `<div class="test-row fail"><span class="test-icon">✕</span><span>Test ${i + 1}<div class="test-detail">${escapeHtml(detail)}</div></span></div>`;
    })
    .join("");
  exResults.innerHTML = summary + rows;
}

function escapeHtml(s) {
  const div = document.createElement("div");
  div.textContent = String(s);
  return div.innerHTML;
}

function showGlobalError(err) {
  exResults.innerHTML = `<div class="error-box">${escapeHtml(err.message)}</div>`;
}

async function setLevel(level) {
  try {
    progress = await api("/api/progress", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ level }),
    });
  } catch (err) {
    showGlobalError(err);
    return;
  }
  currentExercise = null;
  renderLevelTabs();
  levelUpBanner.classList.add("hidden");
  workspace.classList.add("hidden");
  emptyState.classList.remove("hidden");
  await loadExercises(level);
}

levelTabs.querySelectorAll(".level-tab").forEach((btn) => {
  btn.onclick = () => setLevel(btn.dataset.level);
});
runBtn.onclick = runTests;

(async function init() {
  try {
    await loadProgress();
  } catch (err) {
    return; // offline banner already shown by api()
  }
  renderLevelTabs();
  await loadExercises(progress.level);
})();
