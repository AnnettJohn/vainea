/* Galerie-Wechsel auf der Produktseite (pdpGalleryIdx im Click-Dummy). */
(function () {
  "use strict";

  var thumbs = Array.prototype.slice.call(document.querySelectorAll("[data-pdp-thumb]"));
  var shots = Array.prototype.slice.call(document.querySelectorAll("[data-pdp-shot]"));
  if (thumbs.length < 2 || !shots.length) return;

  thumbs.forEach(function (thumb) {
    thumb.addEventListener("click", function () {
      var idx = thumb.dataset.pdpThumb;
      thumbs.forEach(function (other) {
        other.classList.toggle("is-active", other === thumb);
      });
      shots.forEach(function (shot) {
        shot.hidden = shot.dataset.pdpShot !== idx;
      });
    });
  });
})();
