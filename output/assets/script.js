// Runs on detail pages. Quality rows without a real link are already
// rendered as non-clickable "NOT AVAILABLE" (no href) — this just
// guards against someone re-enabling them via devtools and adds a
// small loading state on the real download buttons.
document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll(".dl-row.available").forEach(function (row) {
    row.addEventListener("click", function () {
      row.querySelector(".qlabel").textContent =
        row.querySelector(".qlabel").dataset.quality + " — starting...";
      setTimeout(function () {
        row.querySelector(".qlabel").textContent =
          row.querySelector(".qlabel").dataset.quality;
      }, 2500);
    });
  });

  document.querySelectorAll(".dl-row.unavailable").forEach(function (row) {
    row.addEventListener("click", function (e) {
      e.preventDefault();
    });
  });
});
