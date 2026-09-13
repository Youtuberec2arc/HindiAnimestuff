(function () {
  "use strict";
  var STORAGE_KEY = "tgPopupLastShown";
  var COOLDOWN_MS = 24 * 60 * 60 * 1000; // 24 hours

  var backdrop = document.getElementById("tgPopupBackdrop");
  if (!backdrop) return;

  var joinLink = document.getElementById("tgPopupJoinBtn");
  var joinUrl = joinLink ? joinLink.getAttribute("href") : "";

  function markDismissed() {
    try { localStorage.setItem(STORAGE_KEY, String(Date.now())); } catch (e) {}
  }

  function hidePopup() {
    backdrop.classList.remove("open");
    markDismissed();
  }

  function shouldShow() {
    var last;
    try { last = parseInt(localStorage.getItem(STORAGE_KEY) || "0", 10); } catch (e) { last = 0; }
    return !last || (Date.now() - last) > COOLDOWN_MS;
  }

  function showPopup() {
    backdrop.classList.add("open");
  }

  if (shouldShow()) {
    setTimeout(showPopup, 1500);
  }

  var closeBtn = document.getElementById("tgPopupClose");
  var joinedBtn = document.getElementById("tgPopupJoinedBtn");
  var copyBtn = document.getElementById("tgPopupCopyBtn");

  if (closeBtn) closeBtn.addEventListener("click", hidePopup);
  if (joinedBtn) joinedBtn.addEventListener("click", hidePopup);
  if (joinLink) joinLink.addEventListener("click", markDismissed);

  backdrop.addEventListener("click", function (e) {
    if (e.target === backdrop) hidePopup();
  });

  if (copyBtn) {
    copyBtn.addEventListener("click", function () {
      navigator.clipboard.writeText("https://hindianimestuff.web.app/").then(function () {
        var original = copyBtn.innerHTML;
        copyBtn.classList.add("copied");
        setTimeout(function () { copyBtn.classList.remove("copied"); }, 1500);
      });
    });
  }
})();
