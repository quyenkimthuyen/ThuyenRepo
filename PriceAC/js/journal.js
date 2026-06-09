/* Journal module: stores emotion notes in LocalStorage and renders editable history. */
const JournalStore = (() => {
  const storageKey = "market-psychology-journal";

  const read = () => {
    try {
      return JSON.parse(localStorage.getItem(storageKey)) || [];
    } catch (error) {
      console.warn("Unable to read journal entries", error);
      return [];
    }
  };

  const write = (entries) => {
    localStorage.setItem(storageKey, JSON.stringify(entries));
  };

  const createId = () => {
    if (window.crypto && crypto.randomUUID) {
      return crypto.randomUUID();
    }
    return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  };

  const save = (entry) => {
    const entries = read();

    if (entry.id) {
      const nextEntries = entries.map((item) => item.id === entry.id ? entry : item);
      write(nextEntries);
      return nextEntries;
    }

    const nextEntry = {
      ...entry,
      id: createId()
    };
    const nextEntries = [nextEntry, ...entries];
    write(nextEntries);
    return nextEntries;
  };

  const remove = (id) => {
    const nextEntries = read().filter((entry) => entry.id !== id);
    write(nextEntries);
    return nextEntries;
  };

  const clear = () => {
    write([]);
    return [];
  };

  const search = (query) => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) {
      return read();
    }

    return read().filter((entry) => {
      const haystack = `${entry.date} ${entry.asset} ${entry.emotion} ${entry.note}`.toLowerCase();
      return haystack.includes(normalized);
    });
  };

  return {
    read,
    save,
    remove,
    clear,
    search
  };
})();

const JournalUI = (() => {
  let onChange = () => {};

  const elements = {};

  const cacheElements = () => {
    elements.form = document.querySelector("#journal-form");
    elements.id = document.querySelector("#entry-id");
    elements.date = document.querySelector("#entry-date");
    elements.asset = document.querySelector("#entry-asset");
    elements.emotion = document.querySelector("#entry-emotion");
    elements.note = document.querySelector("#entry-note");
    elements.search = document.querySelector("#journal-search");
    elements.list = document.querySelector("#journal-list");
  };

  const resetForm = () => {
    elements.id.value = "";
    elements.date.value = new Date().toISOString().slice(0, 10);
    elements.asset.value = "BTC";
    elements.emotion.value = "Fear";
    elements.note.value = "";
  };

  const escapeHtml = (value) => String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll("\"", "&quot;")
    .replaceAll("'", "&#039;");

  const renderList = (entries) => {
    if (!entries.length) {
      elements.list.innerHTML = "<div class=\"empty-state\">No journal entries yet. Save a reflection to begin.</div>";
      return;
    }

    elements.list.innerHTML = entries.map((entry) => `
      <article class="journal-item" data-id="${entry.id}">
        <div class="journal-meta">${escapeHtml(entry.date)} &middot; ${escapeHtml(entry.asset)} &middot; ${escapeHtml(entry.emotion)}</div>
        <h3>${escapeHtml(entry.emotion)}</h3>
        <p>${escapeHtml(entry.note)}</p>
        <div class="journal-actions">
          <button class="ghost-button" data-action="edit">Edit</button>
          <button class="ghost-button delete" data-action="delete">Delete</button>
        </div>
      </article>
    `).join("");
  };

  const refresh = () => {
    renderList(JournalStore.search(elements.search.value));
    onChange(JournalStore.read());
  };

  const bindEvents = () => {
    elements.form.addEventListener("submit", (event) => {
      event.preventDefault();
      JournalStore.save({
        id: elements.id.value,
        date: elements.date.value,
        asset: elements.asset.value,
        emotion: elements.emotion.value,
        note: elements.note.value.trim()
      });
      resetForm();
      refresh();
    });

    elements.search.addEventListener("input", refresh);

    elements.list.addEventListener("click", (event) => {
      const button = event.target.closest("button");
      const item = event.target.closest(".journal-item");
      if (!button || !item) {
        return;
      }

      const entry = JournalStore.read().find((current) => current.id === item.dataset.id);
      if (!entry) {
        return;
      }

      if (button.dataset.action === "delete") {
        JournalStore.remove(entry.id);
        refresh();
        return;
      }

      elements.id.value = entry.id;
      elements.date.value = entry.date;
      elements.asset.value = entry.asset;
      elements.emotion.value = entry.emotion;
      elements.note.value = entry.note;
      document.querySelector("[data-target='journal']").click();
    });
  };

  const init = (changeHandler) => {
    onChange = changeHandler;
    cacheElements();
    resetForm();
    bindEvents();
    refresh();
  };

  return {
    init,
    refresh
  };
})();
