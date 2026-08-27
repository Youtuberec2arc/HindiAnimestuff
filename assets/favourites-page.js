// Renders the /favourites.html grid client-side from localStorage ids
// + the embedded SITE_ITEMS list (data.js). Runs only on that page.
(function () {
  "use strict";
  var ROOT = document.body.getAttribute("data-root") || "";
  var grid = document.getElementById("favGrid");
  var emptyMsg = document.getElementById("favEmptyMsg");
  if (!grid) return;

  var favs = (window.SITE_APP && window.SITE_APP.getFavs()) || [];
  var items = (window.SITE_ITEMS || []).filter(function (it) {
    return favs.indexOf(it.id) !== -1;
  });

  if (items.length === 0) {
    if (emptyMsg) emptyMsg.style.display = "block";
    return;
  }

  grid.innerHTML = items.map(function (it) {
    return '<div class="card" data-id="' + it.id + '">' +
      '<a class="card-link" href="' + ROOT + 'pages/' + it.id + '.html">' +
        '<div class="thumb-wrap">' +
          '<img src="' + (/^https?:\/\//.test(it.poster) ? it.poster : ROOT + it.poster) + '" alt="" loading="lazy">' +
          '<div class="thumb-scrim"></div>' +
          '<div class="rating-badge">★ ' + it.rating + '</div>' +
          (it.episode_tag ? '<div class="ep-badge">' + it.episode_tag + '</div>' : '') +
        '</div>' +
        '<div class="info"><div class="title">' + it.title + '</div>' +
        '<div class="meta">' + (it.type || "") + '</div></div>' +
      '</a>' +
      '<button class="fav-btn active" data-fav-id="' + it.id + '" aria-label="Remove favourite">' +
        '<svg viewBox="0 0 24 24"><path d="M12 21s-7-4.5-9.5-9C.7 8.2 2.4 4 6.5 4 9 4 11 5.6 12 7c1-1.4 3-3 5.5-3 4.1 0 5.8 4.2 4 8-2.5 4.5-9.5 9-9.5 9z" stroke="currentColor" stroke-width="2" fill="none" stroke-linejoin="round"/></svg>' +
      '</button>' +
    '</div>';
  }).join("");

  // re-run favourite button wiring for the freshly inserted buttons
  grid.querySelectorAll("[data-fav-id]").forEach(function (btn) {
    btn.addEventListener("click", function (e) {
      e.preventDefault();
      e.stopPropagation();
      var id = btn.getAttribute("data-fav-id");
      var current = (window.SITE_APP && window.SITE_APP.getFavs()) || [];
      var idx = current.indexOf(id);
      if (idx !== -1) current.splice(idx, 1);
      try { localStorage.setItem("fav_ids", JSON.stringify(current)); } catch (e2) {}
      btn.closest(".card").remove();
      if (grid.children.length === 0 && emptyMsg) emptyMsg.style.display = "block";
    });
  });
})();
