// Per-exercise editor drafts in localStorage, so an in-progress attempt
// survives switching exercises and reloading -- and so Reset has something
// to actually discard.
function draftKey(id) {
  return `wr-draft-${id}`;
}

function loadDraft(id) {
  return localStorage.getItem(draftKey(id));
}

function saveDraft(id, code) {
  localStorage.setItem(draftKey(id), code);
}

function clearDraft(id) {
  localStorage.removeItem(draftKey(id));
}

if (typeof module !== "undefined") {
  module.exports = { draftKey, loadDraft, saveDraft, clearDraft };
}
