(() => {
    if (!navigator.clipboard || typeof navigator.clipboard.writeText !== "function") return;

    const blocks = document.querySelectorAll(".codeblock[data-copyable]");
    blocks.forEach((block) => {
        const code = block.querySelector("code");
        if (!code) return;

        const button = document.createElement("button");
        button.type = "button";
        button.className = "codeblock__copy";
        button.textContent = "Copy";
        const label = block.getAttribute("aria-label");
        button.setAttribute("aria-label", label ? `Copy: ${label}` : "Copy to clipboard");

        const status = document.createElement("span");
        status.className = "visually-hidden";
        status.setAttribute("aria-live", "polite");

        let timer;
        button.addEventListener("click", async () => {
            const text = code.textContent.trim();
            try {
                await navigator.clipboard.writeText(text);
                button.textContent = "Copied";
                status.textContent = "Copied to clipboard";
            } catch {
                button.textContent = "Copy failed";
                status.textContent = "Copy failed";
            }
            clearTimeout(timer);
            timer = setTimeout(() => {
                button.textContent = "Copy";
                status.textContent = "";
            }, 1500);
        });

        block.appendChild(button);
        block.appendChild(status);
    });
})();
