/**
 * Floating notification box — shows entries from window.SITE_NOTIFICATIONS
 * (generated at build time). History limited to last 7 days.
 * Red dot clears when the panel is opened (per device localStorage).
 */
(function () {
  var SEVEN_DAYS = 7 * 24 * 60 * 60 * 1000;
  var SEEN_KEY = "notify_last_seen";

  function now() { return Date.now(); }

  function getNotifications() {
    var list = window.SITE_NOTIFICATIONS || [];
    var cutoff = now() - SEVEN_DAYS;
    return list.filter(function (n) {
      var t = n.ts ? Date.parse(n.ts) : 0;
      return t >= cutoff;
    });
  }

  function render() {
    var listEl = document.getElementById("notifyList");
    var fab = document.getElementById("notifyFab");
    if (!listEl || !fab) return;

    var items = getNotifications();
    if (!items.length) {
      listEl.innerHTML = '<div class="notify-empty">No recent updates</div>';
      fab.classList.remove("has-new");
      return;
    }

    listEl.innerHTML = items.map(function (n) {
      return (
        '<div class="notify-item">' +
          '<div class="n-type">' + escapeHtml(n.type || "Update") + "</div>" +
          '<div class="n-title">' + escapeHtml(n.title || "") + "</div>" +
          (n.date ? '<div class="n-date">' + escapeHtml(n.date) + "</div>" : "") +
        "</div>"
      );
    }).join("");

    var lastSeen = parseInt(localStorage.getItem(SEEN_KEY) || "0", 10);
    var newest = Math.max.apply(null, items.map(function (n) {
      return n.ts ? Date.parse(n.ts) : 0;
    }));
    if (newest > lastSeen) fab.classList.add("has-new");
    else fab.classList.remove("has-new");
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  document.addEventListener("DOMContentLoaded", function () {
    var fab = document.getElementById("notifyFab");
    var panel = document.getElementById("notifyPanel");
    if (!fab || !panel) return;

    render();

    fab.addEventListener("click", function (e) {
      e.stopPropagation();
      var open = panel.classList.toggle("open");
      if (open) {
        localStorage.setItem(SEEN_KEY, String(now()));
        fab.classList.remove("has-new");
      }
    });

    document.addEventListener("click", function (e) {
      if (!panel.contains(e.target) && e.target !== fab) {
        panel.classList.remove("open");
      }
    });
  });
})();
