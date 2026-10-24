(() => {
    // Giscus loads only when the visitor asks for it. Until then nothing on
    // this page talks to giscus.app, so a passive reader's IP and browser
    // details stay with Cloudflare alone (see privacy.html). The attributes
    // below mirror the exception documented in docs/security/CSP_EXCEPTIONS.md;
    // the integrity hash pins the exact loader bundle and is refreshed there.
    const button = document.getElementById("load-comments");
    const container = document.querySelector(".giscus");
    if (!button || !container) return;

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
            "data-theme": "light",
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
