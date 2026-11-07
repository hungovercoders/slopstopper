(() => {
    // Giscus loads only when the visitor asks for it. Until then nothing on
    // this page talks to giscus.app, so a passive reader's IP and browser
    // details stay with Cloudflare alone (see privacy.html). The attributes
    // below mirror the exception documented in docs/security/CSP_EXCEPTIONS.md;
    // the integrity hash pins the exact loader bundle and is refreshed there.
    const button = document.getElementById("load-comments");
    const container = document.querySelector(".giscus");
    if (!button || !container) return;

    // The widget takes the site's theme (theme.js sets data-theme when the
    // visitor has chosen one; the OS preference otherwise) and follows the
    // toggle through giscus's postMessage API once its frame is up.
    const theme = () =>
        document.documentElement.dataset.theme ||
        (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    document.addEventListener("themechange", () => {
        const frame = container.querySelector("iframe.giscus-frame");
        if (frame && frame.contentWindow) {
            frame.contentWindow.postMessage({ giscus: { setConfig: { theme: theme() } } }, "https://giscus.app");
        }
    });

    button.addEventListener("click", () => {
        button.disabled = true;
        button.textContent = "Loading comments…";

        const script = document.createElement("script");
        script.src = "https://giscus.app/client.js";
        const attrs = {
            "data-repo": "hungovercoders/slopstopper",
            "data-repo-id": "R_kgDOQ0Psbg",
            "data-category": "Feedback",
            "data-category-id": "DIC_kwDOQ0Psbs4C-oQh",
            "data-mapping": "pathname",
            "data-strict": "0",
            "data-reactions-enabled": "1",
            "data-emit-metadata": "0",
            "data-input-position": "bottom",
            "data-theme": theme(),
            "data-lang": "en",
            integrity: "sha384-UwLZGbJGvkTzz0719+xEzUm/idqwzs0yZN8aB9Se5vUXHbyRyDWw9yqZTIsOsJ7x",
            crossorigin: "anonymous",
        };
        for (const [name, value] of Object.entries(attrs)) script.setAttribute(name, value);
        script.async = true;
        script.addEventListener("load", () => button.closest(".comments-load").hidden = true);
        script.addEventListener("error", () => {
            button.disabled = false;
            button.textContent = "Comments didn't load. Try again";
        });
        container.parentNode.insertBefore(script, container.nextSibling);
    }, { once: false });
})();
