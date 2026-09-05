// Self-check for static/drafts.js: the save/restore/reset cycle behind the
// editor's Reset button. Run: node test_drafts.js
const assert = require("node:assert");

const store = new Map();
global.localStorage = {
  getItem: (k) => (store.has(k) ? store.get(k) : null),
  setItem: (k, v) => store.set(k, v),
  removeItem: (k) => store.delete(k),
};

const { draftKey, loadDraft, saveDraft, clearDraft } = require("./static/drafts.js");

function test_no_draft_means_starter_code() {
  store.clear();
  assert.strictEqual(loadDraft("novice-1"), null);
}

function test_draft_survives_reopening() {
  store.clear();
  saveDraft("novice-1", "def f(): return 1");
  assert.strictEqual(loadDraft("novice-1"), "def f(): return 1");
}

function test_drafts_are_per_exercise() {
  store.clear();
  saveDraft("novice-1", "a");
  saveDraft("novice-2", "b");
  assert.strictEqual(loadDraft("novice-1"), "a");
  assert.strictEqual(loadDraft("novice-2"), "b");
}

function test_reset_discards_the_draft() {
  store.clear();
  saveDraft("novice-1", "half-finished");
  clearDraft("novice-1");
  // loadDraft falling back to null is what makes openExercise show
  // starter_code again -- i.e. Reset actually resets.
  assert.strictEqual(loadDraft("novice-1"), null);
}

function test_reset_leaves_other_exercises_alone() {
  store.clear();
  saveDraft("novice-1", "a");
  saveDraft("novice-2", "b");
  clearDraft("novice-1");
  assert.strictEqual(loadDraft("novice-2"), "b");
}

function test_keys_are_namespaced() {
  assert.strictEqual(draftKey("novice-1"), "wr-draft-novice-1");
}

const tests = [
  test_no_draft_means_starter_code,
  test_draft_survives_reopening,
  test_drafts_are_per_exercise,
  test_reset_discards_the_draft,
  test_reset_leaves_other_exercises_alone,
  test_keys_are_namespaced,
];
for (const t of tests) {
  t();
  console.log(`PASS ${t.name}`);
}
console.log("All checks passed.");
