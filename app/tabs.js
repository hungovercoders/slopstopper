(() => {
    // A tab set (Features: the five loops; Tools: the tool groups). The
    // markup is a tablist of in-page links over the panels, so a page
    // without script shows every panel and each link scrolls to one.
    // With script: one panel at a time, the arrow keys move between
    // tabs, the hash follows the open tab so a deep link
    // (features.html#hygiene, the home page's cards) opens the right
    // one, and a hash change (back/forward) does too.
    const list = document.querySelector(".tabs[role='tablist']");
    if (!list) return;
    const tabs = Array.from(list.querySelectorAll("[role='tab']"));
    const panels = tabs.map((tab) => document.getElementById(tab.getAttribute("aria-controls")));
    if (panels.some((panel) => !panel)) return;

    const indexOf = (id) => panels.findIndex((panel) => panel.id === id);

    const activate = (index, { focus = false, hash = true } = {}) => {
        tabs.forEach((tab, i) => {
            const on = i === index;
            tab.setAttribute("aria-selected", String(on));
            tab.tabIndex = on ? 0 : -1;
            panels[i].hidden = !on;
        });
        if (focus) tabs[index].focus();
        if (hash && location.hash !== `#${panels[index].id}`) {
            history.replaceState(null, "", `#${panels[index].id}`);
        }
    };

    tabs.forEach((tab, i) => {
        tab.addEventListener("click", (event) => {
            event.preventDefault();
            activate(i, { focus: true });
        });
    });

    list.addEventListener("keydown", (event) => {
        const current = tabs.indexOf(document.activeElement);
        if (current < 0) return;
        const last = tabs.length - 1;
        const next = { ArrowRight: current + 1, ArrowDown: current + 1, ArrowLeft: current - 1, ArrowUp: current - 1, Home: 0, End: last }[event.key];
        if (next === undefined) return;
        event.preventDefault();
        activate((next + tabs.length) % tabs.length, { focus: true });
    });

    window.addEventListener("hashchange", () => {
        const index = indexOf(location.hash.slice(1));
        if (index >= 0) activate(index, { hash: false });
    });

    const initial = indexOf(location.hash.slice(1));
    activate(initial >= 0 ? initial : 0, { hash: false });
    if (initial >= 0) {
        // The browser scrolls to the panel itself once the page has loaded,
        // which puts the tab row under the sticky header; after that, bring
        // the row (its scroll margin clears the header) into view instead.
        const reveal = () => requestAnimationFrame(() => list.scrollIntoView({ block: "start" }));
        if (document.readyState === "complete") reveal();
        else window.addEventListener("load", reveal, { once: true });
    }
})();
