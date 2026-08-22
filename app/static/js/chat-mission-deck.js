(() => {
  "use strict";

  const shell = document.querySelector(".mission-shell");
  if (!shell) return;

  const messageLog = shell.querySelector("[data-message-log]");
  if (messageLog) {
    requestAnimationFrame(() => {
      messageLog.scrollTop = messageLog.scrollHeight;
    });
  }

  const drawer = shell.querySelector("[data-tool-drawer]");
  const drawerLabel = shell.querySelector("[data-drawer-label]");
  const updateDrawerState = () => {
    if (!drawer || !drawerLabel) return;
    drawerLabel.textContent = drawer.open ? "收起" : "展开";
    drawer.dataset.drawerState = drawer.open ? "open" : "closed";
  };

  if (drawer) {
    updateDrawerState();
    drawer.addEventListener("toggle", updateDrawerState);
  }

  const composer = shell.querySelector("#content");
  const characterCount = shell.querySelector("[data-character-count]");
  const updateCharacterCount = () => {
    if (!composer || !characterCount) return;
    characterCount.textContent = `${composer.value.length} / ${composer.maxLength}`;
  };

  if (composer) {
    updateCharacterCount();
    composer.addEventListener("input", updateCharacterCount);
  }

  const dialogSupported =
    typeof window.HTMLDialogElement !== "undefined" &&
    typeof window.HTMLDialogElement.prototype.showModal === "function";
  if (!dialogSupported) return;

  const launchers = [...shell.querySelectorAll("[data-dialog-open]")];
  const dialogs = launchers
    .map((button) => document.getElementById(button.dataset.dialogOpen))
    .filter((dialog) => dialog instanceof window.HTMLDialogElement);

  if (!launchers.length || dialogs.length !== launchers.length) return;
  shell.dataset.chatEnhanced = "true";

  const setLauncherState = (button, isOpen) => {
    button.setAttribute("aria-expanded", String(isOpen));
  };

  let lastLauncher = null;
  launchers.forEach((button) => {
    setLauncherState(button, false);
    button.addEventListener("click", () => {
      const dialog = document.getElementById(button.dataset.dialogOpen);
      if (!(dialog instanceof window.HTMLDialogElement) || dialog.open) return;
      lastLauncher = button;
      dialog.hidden = false;
      try {
        dialog.showModal();
        setLauncherState(button, true);
      } catch (_) {
        dialog.hidden = true;
        setLauncherState(button, false);
        lastLauncher = null;
        delete shell.dataset.chatEnhanced;
        return;
      }
      const firstField = dialog.querySelector("textarea, input:not([type='hidden'])");
      if (firstField) firstField.focus();
    });
  });

  dialogs.forEach((dialog) => {
    dialog.querySelectorAll("[data-dialog-close]").forEach((button) => {
      button.addEventListener("click", () => dialog.close());
    });

    dialog.addEventListener("click", (event) => {
      if (event.target === dialog) dialog.close();
    });

    dialog.addEventListener("close", () => {
      const launcher = launchers.find((button) => button.dataset.dialogOpen === dialog.id);
      if (launcher) setLauncherState(launcher, false);
      if (lastLauncher && document.contains(lastLauncher)) lastLauncher.focus();
      lastLauncher = null;
      dialog.hidden = true;
    });
  });
})();
