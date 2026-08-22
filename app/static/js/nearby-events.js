(function () {
  "use strict";

  const button = document.querySelector("[data-location-button]");
  if (!button) return;

  const idleLabel = button.textContent.trim();
  const status = document.getElementById("location-status");

  function finish(message) {
    button.disabled = false;
    button.removeAttribute("aria-busy");
    button.textContent = idleLabel;
    status.textContent = message;
  }

  button.addEventListener("click", function () {
    if (!("geolocation" in navigator)) {
      finish("当前浏览器不支持定位。你仍可按城市筛选或浏览全部活动。");
      return;
    }

    const form = document.getElementById(button.dataset.formId);
    button.disabled = true;
    button.setAttribute("aria-busy", "true");
    button.textContent = "正在获取位置…";
    status.textContent = "等待浏览器定位授权；拒绝后仍可继续浏览全部活动。";

    navigator.geolocation.getCurrentPosition(
      function (position) {
        form.elements.lat.value = position.coords.latitude.toFixed(5);
        form.elements.lng.value = position.coords.longitude.toFixed(5);
        form.elements.city.value = "";
        form.elements.sort.value = "distance";
        form.elements.sort.querySelector('[value="distance"]').disabled = false;
        status.textContent = "位置已获取，正在由服务端匹配附近活动…";
        if (form.requestSubmit) form.requestSubmit();
        else form.submit();
      },
      function (error) {
        finish(
          error.code === error.PERMISSION_DENIED
            ? "未获得定位授权。已保留城市筛选和全部活动。"
            : "暂时无法获取位置。你仍可按城市筛选或浏览全部活动。"
        );
      },
      { enableHighAccuracy: false, timeout: 10000, maximumAge: 60000 }
    );
  });
})();
