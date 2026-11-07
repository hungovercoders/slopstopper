(() => {
    // Light or dark, the visitor's call. The page follows the OS until the
    // toggle is pressed; a press stores "light" or "dark" in localStorage
    // (the only thing this site keeps in the browser, see privacy.html)
    // and sets data-theme on <html>, which shared.css reads. Choosing the
    // theme the OS already prefers clears the stored value, so the page
    // follows the OS again. This script is the first in <head> and runs
    // before first paint, so there is no flash of the wrong theme.
    const KEY = "theme";
    const root = document.documentElement;
    const media = window.matchMedia("(prefers-color-scheme: dark)");

    const stored = () => {
        try {
            return localStorage.getItem(KEY);
        } catch {
            return null;
        }
    };
    const store = (value) => {
        try {
            if (value) localStorage.setItem(KEY, value);
            else localStorage.removeItem(KEY);
        } catch {
            // Storage blocked: the choice still applies to this page.
        }
    };
    const apply = (choice) => {
        if (choice === "light" || choice === "dark") root.dataset.theme = choice;
        else delete root.dataset.theme;
    };
    const resolved = () => root.dataset.theme || (media.matches ? "dark" : "light");

    root.classList.add("js");
    apply(stored());

    const sync = () => {
        const theme = resolved();
        const next = theme === "dark" ? "light" : "dark";
        document.querySelectorAll(".theme-toggle").forEach((button) => {
            button.setAttribute("aria-label", `Switch to ${next} theme`);
            button.title = `Switch to ${next} theme`;
        });
        // The browser chrome colour on a phone follows the page background.
        const bg = getComputedStyle(root).getPropertyValue("--cream").trim();
        if (bg) document.querySelectorAll('meta[name="theme-color"]').forEach((meta) => meta.setAttribute("content", bg));
        document.dispatchEvent(new CustomEvent("themechange", { detail: { theme } }));
    };

    // An element shown in one theme only (.only-light / .only-dark, the
    // hero's recording) is display: none in the other, so a lazy image
    // among them has not loaded; fetch it as the toggle is approached, so
    // the switch does not show an empty box while it arrives.
    const warm = () => {
        document.querySelectorAll("img.only-light, img.only-dark").forEach((img) => {
            if (!img.complete || img.naturalWidth === 0) new Image().src = img.currentSrc || img.src;
        });
    };

    document.addEventListener("DOMContentLoaded", () => {
        document.querySelectorAll(".theme-toggle").forEach((button) => {
            button.addEventListener("pointerenter", warm, { once: true });
            button.addEventListener("focus", warm, { once: true });
            button.addEventListener("click", () => {
                const next = resolved() === "dark" ? "light" : "dark";
                const system = media.matches ? "dark" : "light";
                apply(next);
                store(next === system ? null : next);
                sync();
            });
        });
        sync();
    });

    media.addEventListener("change", () => {
        if (!stored()) sync();
    });
})();
