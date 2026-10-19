(() => {
  const root = document.getElementById("viewer");
  let props = {};
  let page = 0;
  let selected = new Set();
  let waitingForPreview = false;

  function notifyHeight() {
    window.parent.postMessage(
      {
        isStreamlitMessage: true,
        type: "streamlit:setFrameHeight",
        height: document.documentElement.scrollHeight,
      },
      "*",
    );
  }

  function publish() {
    window.parent.postMessage(
      {
        isStreamlitMessage: true,
        type: "streamlit:setComponentValue",
        value: { page, selected: [...selected] },
        dataType: "json",
      },
      "*",
    );
  }

  function setPage(nextPage) {
    page = Math.max(0, Math.min(props.pageCount - 1, nextPage));
    waitingForPreview = false;
    publish();
  }

  function toggleFinding(finding) {
    if (!finding.enabled) return;
    if (selected.has(finding.id)) selected.delete(finding.id);
    else selected.add(finding.id);
    waitingForPreview = true;
    render();
    publish();
  }

  function render() {
    if (!props.image || !Number.isFinite(props.pageCount)) return;
    const toolbar = document.createElement("nav");
    toolbar.className = "viewer-toolbar";
    toolbar.setAttribute("aria-label", "PDF pages and correction preview");

    const pageControls = document.createElement("div");
    pageControls.className = "toolbar-group";
    pageControls.append(button("Previous page", "‹", page === 0, () => setPage(page - 1)));
    const pageLabel = document.createElement("span");
    pageLabel.className = "page-label";
    pageLabel.textContent = `Page ${page + 1} of ${props.pageCount}`;
    pageControls.append(pageLabel);
    pageControls.append(
      button("Next page", "›", page >= props.pageCount - 1, () => setPage(page + 1)),
    );

    const actions = document.createElement("div");
    actions.className = "toolbar-group";
    const count = document.createElement("span");
    count.className = "change-count";
    count.textContent = `${selected.size} change${selected.size === 1 ? "" : "s"} previewed`;
    actions.append(count);
    actions.append(
      button("Clear all changes", "Clear", selected.size === 0, () => {
        selected.clear();
        waitingForPreview = true;
        render();
        publish();
      }),
    );
    toolbar.append(pageControls, actions);

    const shell = document.createElement("div");
    shell.className = "page-shell";
    const image = document.createElement("img");
    image.className = "page-image";
    image.alt = `PDF page ${page + 1}`;
    image.src = `data:image/png;base64,${props.image}`;
    shell.append(image);

    for (const finding of props.findings || []) {
      const rect = finding.rect;
      const mark = document.createElement("button");
      mark.type = "button";
      mark.className = "finding-mark";
      mark.style.left = `${(rect[0] / props.pageWidth) * 100}%`;
      mark.style.top = `${(rect[1] / props.pageHeight) * 100}%`;
      mark.style.width = `${(rect[2] - rect[0]) / props.pageWidth * 100}%`;
      mark.style.height = `${(rect[3] - rect[1]) / props.pageHeight * 100}%`;
      mark.disabled = !finding.enabled;
      mark.setAttribute("aria-pressed", selected.has(finding.id) ? "true" : "false");
      mark.setAttribute(
        "aria-label",
        finding.enabled
          ? `${finding.original} to ${finding.correction}. Click to toggle.`
          : `${finding.original}: ${finding.reason || "Unavailable for direct replacement."}`,
      );
      mark.title = finding.enabled
        ? `${finding.original} → ${finding.correction}`
        : `${finding.original}: ${finding.reason || "Unavailable for direct replacement."}`;
      mark.addEventListener("click", () => toggleFinding(finding));
      shell.append(mark);
    }

    const note = document.createElement("p");
    note.className = `viewer-note${waitingForPreview ? " updating" : ""}`;
    note.textContent = waitingForPreview
      ? "Updating page preview…"
      : "Click a highlighted word to preview its correction. Click it again to restore the original.";
    root.replaceChildren(toolbar, shell, note);
    image.addEventListener("load", notifyHeight, { once: true });
    requestAnimationFrame(notifyHeight);
  }

  function button(label, text, disabled, action) {
    const control = document.createElement("button");
    control.type = "button";
    control.textContent = text;
    control.title = label;
    control.setAttribute("aria-label", label);
    control.disabled = disabled;
    control.addEventListener("click", action);
    return control;
  }

  window.addEventListener("message", (event) => {
    if (event.source !== window.parent) return;
    if (event.data.type !== "streamlit:render") return;
    props = event.data.args || {};
    const state = props.default || {};
    page = Number.isInteger(state.page) ? state.page : 0;
    selected = new Set(Array.isArray(state.selected) ? state.selected : []);
    waitingForPreview = false;
    render();
  });

  window.parent.postMessage(
    { isStreamlitMessage: true, type: "streamlit:componentReady", apiVersion: 1 },
    "*",
  );
})();