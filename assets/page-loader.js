(function () {
  "use strict";
  var loader = document.getElementById("pageLoader");
  if (!loader) return;

  function isInternalNavigableLink(a) {
    if (!a || !a.href) return false;
    if (a.target && a.target !== "" && a.target !== "_self") return false;
    if (a.hasAttribute("download")) return false;
    var href = a.getAttribute("href") || "";
    if (href.startsWith("#") || href.startsWith("javascript:") || href.startsWith("mailto:") || href.startsWith("tel:")) return false;
    try {
      var url = new URL(a.href, window.location.href);
      return url.origin === window.location.origin;
    } catch (e) {
      return false;
    }
  }

  document.addEventListener("click", function (e) {
    var a = e.target.closest ? e.target.closest("a") : null;
    if (!isInternalNavigableLink(a)) return;
    // Same-page anchors and links that only differ by hash: skip the loader
    if (a.href === window.location.href) return;

    e.preventDefault();
    loader.classList.add("show");
    setTimeout(function () {
      window.location.href = a.href;
    }, 380);
  });

  // Hide the loader once a new page has actually painted (covers back/forward
  // cache restores where no fresh "load" fires too).
  window.addEventListener("pageshow", function () {
    loader.classList.remove("show");
  });
})();
