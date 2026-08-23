(() => {
  "use strict";

  const input = document.querySelector("[data-avatar-input]");
  const preview = document.querySelector("[data-avatar-preview]");
  const placeholder = document.querySelector("[data-avatar-placeholder]");
  const status = document.querySelector("[data-avatar-status]");
  const card = document.querySelector("[data-avatar-preview-card]");
  if (!input || !preview || !placeholder || !status || !card) return;

  const allowedTypes = new Set(["image/jpeg", "image/png", "image/webp"]);
  const maximumBytes = 400 * 1024;
  let previewUrl = "";

  const clearPreview = (message = "Mock 占位 · 未真实验证") => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    previewUrl = "";
    preview.hidden = true;
    preview.removeAttribute("src");
    placeholder.hidden = false;
    status.textContent = message;
    card.dataset.state = "empty";
  };

  input.addEventListener("change", () => {
    input.setCustomValidity("");
    const file = input.files?.[0];
    if (!file) {
      clearPreview();
      return;
    }
    if (!allowedTypes.has(file.type) || file.size > maximumBytes) {
      input.value = "";
      input.setCustomValidity("请选择小于 400 KiB 的 JPG、PNG 或 WebP 头像。");
      clearPreview("文件不符合要求，请重新选择");
      input.reportValidity();
      return;
    }
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    previewUrl = URL.createObjectURL(file);
    preview.src = previewUrl;
    preview.hidden = false;
    placeholder.hidden = true;
    status.textContent = "已选择 · Mock 人脸核验占位";
    card.dataset.state = "ready";
  });

  window.addEventListener("pagehide", () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
  });
})();
