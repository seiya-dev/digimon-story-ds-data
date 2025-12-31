expandAll = () => document.querySelectorAll(".root").forEach(r => r.classList.remove("collapsed"));
collapseAll = () => document.querySelectorAll(".root").forEach(r => r.classList.add("collapsed"));
toggleRoot = (id) => {
    const el = document.getElementById(id);
    if (el)
        el.classList.toggle("collapsed");
};

(() => {
    const q = document.getElementById("q");
    const lvlChecks = Array.from(document.querySelectorAll(".lvl-filter"));
    const sections = Array.from(document.querySelectorAll("#viewByLine .section"));
    const idContainer = document.getElementById("viewById");
    const lineContainer = document.getElementById("viewByLine");
    const toggle = document.getElementById("toggleView");
    const fileInput = document.getElementById("importFile");

    const load = () => {
        try {
            return JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}")
        } catch {
            return {}
        }
    };
    const save = (st) => localStorage.setItem(STORAGE_KEY, JSON.stringify(st));
    let state = load();

    const allCbs = () => Array.from(document.querySelectorAll("input.cb"));
    function uniqueKeys() {
        return Array.from(new Set(allCbs().map(cb => cb.dataset.key)));
    }
    function checkedUniqueKeys() {
        const checked = new Set();
        allCbs().forEach(cb => {
            if (cb.checked)
                checked.add(cb.dataset.key);
        });
        return Array.from(checked);
    }

    function setCheckedForKey(key, checked) {
        document.querySelectorAll(`input.cb[data-key="${CSS.escape(key)}"]`).forEach(cb => {
            cb.checked = checked;
        });
    }
    function applyState() {
        allCbs().forEach(cb => cb.checked = !!state[cb.dataset.key]);
    }

    function updateCounts() {
        const total = uniqueKeys().length;
        const checked = checkedUniqueKeys().length;
        document.getElementById("count").textContent = `${checked}/${total} checked`;
    }

    document.addEventListener("change", (e) => {
        const cb = e.target.closest("input.cb");
        if (!cb)
            return;
        const key = cb.dataset.key;
        const checked = cb.checked;
        state[key] = checked;
        save(state);
        setCheckedForKey(key, checked);
        updateCounts();
    });

    window.setAll = (val) => {
        uniqueKeys().forEach(k => {
            state[k] = val;
        });
        save(state);
        uniqueKeys().forEach(k => setCheckedForKey(k, val));
        updateCounts();
    };

    window.clearState = () => {
        localStorage.removeItem(STORAGE_KEY);
        state = {};
        applyState();
        updateCounts();
    };

    function activeLvls() {
        return new Set(lvlChecks.filter(x => x.checked).map(x => x.value));
    }
    function matches(el, term, lvls) {
        const t = (el.dataset.text || "");
        const lvl = (el.dataset.lvl || "");
        return (!term || t.includes(term)) && (!lvls.size || lvls.has(lvl));
    }

    function filterIdView() {
        const term = (q.value || "").toLowerCase().trim();
        const lvls = activeLvls();
        idContainer.querySelectorAll(".node").forEach(el => {
            el.classList.toggle("hidden", !matches(el, term, lvls));
        });
    }

    function filterLineView() {
        const term = (q.value || "").toLowerCase().trim();
        const lvls = activeLvls();
        const nodes = Array.from(lineContainer.querySelectorAll("li.node"));
        nodes.forEach(li => li.classList.toggle("hidden", !matches(li, term, lvls)));

        nodes.filter(li => !li.classList.contains("hidden")).forEach(li => {
            let p = li.parentElement;
            while (p) {
                const parentLi = p.closest("li.node");
                if (!parentLi)
                    break;
                parentLi.classList.remove("hidden");
                p = parentLi.parentElement;
            }
        });

        sections.forEach(sec => {
            const anyVisible = sec.querySelector("li.node:not(.hidden)");
            sec.classList.toggle("hidden", !anyVisible);
        });
    }

    function filter() {
        filterLineView();
        filterIdView();
    }

    function setViewMode(mode) {
        const byId = (mode === "id");
        toggle.checked = byId;
        idContainer.classList.toggle("hidden", !byId);
        lineContainer.classList.toggle("hidden", byId);
        document.getElementById("viewLabel").textContent = byId ? "View: by ID" : "View: by Lines";
        localStorage.setItem(VIEW_KEY, mode);
        applyState();
        updateCounts();
        filter();
    }

    // Make the pill clickable already via label, but keep behavior on input change
    toggle.addEventListener("change", () => setViewMode(toggle.checked ? "id" : "lines"));

    // Export / Import
    function exportState() {
        const payload = {
            version: 1,
            savedAt: new Date().toISOString(),
            checked: Object.entries(state).filter(([k, v]) => !!v).map(([k]) => k).sort()
        };
        const blob = new Blob([JSON.stringify(payload, null, 2)], {
            type: "application/json"
        });
        const a = document.createElement("a");
        const stamp = payload.savedAt.replace(/[:.]/g, "-");
        a.href = URL.createObjectURL(blob);
        a.download = `${SAVE_KEY}_${stamp}.json`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        setTimeout(() => URL.revokeObjectURL(a.href), 1000);
    }

    function importStateFile(file) {
        const reader = new FileReader();
        reader.onload = () => {
            try {
                const data = JSON.parse(reader.result);
                const checked = Array.isArray(data.checked) ? data.checked : [];
                state = {};
                checked.forEach(k => {
                    state[k] = true;
                });
                save(state);
                applyState();
                updateCounts();
                filter();
                alert(`Imported ${checked.length} checked Digimon.`);
            } catch (e) {
                alert("Invalid file. Please choose a JSON export from this checklist.");
            }
        };
        reader.readAsText(file);
    }

    document.getElementById("exportBtn").addEventListener("click", exportState);
    document.getElementById("importBtn").addEventListener("click", () => fileInput.click());
    fileInput.addEventListener("change", (e) => {
        const f = e.target.files && e.target.files[0];
        if (f)
            importStateFile(f);
        e.target.value = "";
    });

    q.addEventListener("input", filter);
    lvlChecks.forEach(c => c.addEventListener("change", filter));

    // init
    const savedMode = localStorage.getItem(VIEW_KEY) || "lines";
    setViewMode(savedMode);
})();
