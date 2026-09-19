// Homepage-Interaktivität aus dem Click-Dummy (index.html) nachgebaut:
// Hero-State-Auswahl, Shop-the-Look-Hotspots, Quiz-Reveal, Newsletter-Demo.
// Bewusst reines Vanilla-JS ohne Server-Roundtrip - alle Zieldaten (States,
// Quiz-Ergebnisse) sind serverseitig bereits vollständig im DOM gerendert,
// hier wird nur zwischen ihnen umgeschaltet.
(function () {
  "use strict";

  function initHero() {
    var hero = document.querySelector("[data-hero]");
    if (!hero) return;

    var buttons = hero.querySelectorAll("[data-hero-select]");
    var slides = hero.querySelectorAll("[data-hero-slide]");
    var eyebrow = hero.querySelector("[data-hero-eyebrow]");
    var line = hero.querySelector("[data-hero-line]");
    var cta = hero.querySelector("[data-hero-cta]");
    var ctaLabel = hero.querySelector("[data-hero-cta-label]");

    buttons.forEach(function (btn) {
      btn.addEventListener("click", function () {
        var slug = btn.getAttribute("data-hero-select");

        buttons.forEach(function (b) {
          var isActive = b === btn;
          b.classList.toggle("is-active", isActive);
          b.setAttribute("aria-pressed", isActive ? "true" : "false");
        });
        slides.forEach(function (slide) {
          slide.classList.toggle("is-active", slide.getAttribute("data-hero-slide") === slug);
        });

        hero.style.setProperty("--accent", btn.getAttribute("data-hero-hex"));
        if (eyebrow) eyebrow.textContent = btn.getAttribute("data-hero-mood");
        if (line) line.textContent = btn.getAttribute("data-hero-line");
        if (ctaLabel) ctaLabel.textContent = "Shop " + btn.getAttribute("data-hero-num") + " " + btn.getAttribute("data-hero-name");
        if (cta) cta.setAttribute("href", "/states/" + slug);
      });
    });
  }

  function initShopTheLook() {
    var frame = document.querySelector("[data-look]");
    if (!frame) return;

    var toggles = frame.querySelectorAll("[data-look-toggle]");
    toggles.forEach(function (toggle) {
      toggle.addEventListener("click", function () {
        var pid = toggle.getAttribute("data-look-toggle");
        var card = frame.querySelector('[data-look-card="' + pid + '"]');
        var wasOpen = card && card.classList.contains("is-open");

        frame.querySelectorAll("[data-look-card]").forEach(function (c) {
          c.classList.remove("is-open");
        });
        toggles.forEach(function (t) {
          t.classList.remove("is-open");
        });

        if (card && !wasOpen) {
          card.classList.add("is-open");
          toggle.classList.add("is-open");
        }
      });
    });
  }

  function initQuiz() {
    var quiz = document.querySelector("[data-quiz]");
    if (!quiz) return;

    var moodButtons = quiz.querySelectorAll("[data-quiz-mood]");
    var results = quiz.querySelectorAll("[data-quiz-result]");

    moodButtons.forEach(function (btn) {
      btn.addEventListener("click", function () {
        var slug = btn.getAttribute("data-quiz-mood");

        moodButtons.forEach(function (b) {
          b.classList.toggle("is-selected", b === btn);
        });
        results.forEach(function (r) {
          r.hidden = r.getAttribute("data-quiz-result") !== slug;
        });
        quiz.style.setProperty("--accent", btn.style.getPropertyValue("--accent"));
      });
    });
  }

  function initNewsletter() {
    var form = document.querySelector("[data-newsletter-form]");
    if (!form) return;

    // Rein clientseitige Demo (wie im Click-Dummy) - es wird noch nichts
    // gespeichert oder verschickt; siehe README für den offenen Punkt
    // "echte Newsletter-Anbindung".
    form.addEventListener("submit", function (event) {
      event.preventDefault();
      var success = document.querySelector("[data-newsletter-success]");
      form.hidden = true;
      if (success) success.hidden = false;
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    initHero();
    initShopTheLook();
    initQuiz();
    initNewsletter();
  });
})();
