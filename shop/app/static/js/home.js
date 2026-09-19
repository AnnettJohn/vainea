/* Homepage-Interaktionen aus dem Click-Dummy: Hero-State-Wechsel
   (updateHeroVisual inkl. Swipe), Shop-the-Look-Hotspots, Find-your-State-Quiz
   und das Newsletter-Formular. */
(function () {
  "use strict";

  /* ---------- Hero ---------- */
  var hero = document.getElementById("heroSection");
  if (hero) {
    var slides = Array.prototype.slice.call(hero.querySelectorAll(".hero-slide"));
    var stateBtns = Array.prototype.slice.call(hero.querySelectorAll(".hero-state-btn"));
    var indexBtns = Array.prototype.slice.call(hero.querySelectorAll(".hero-index-item"));
    var textWrap = document.getElementById("heroTextWrap");
    var eyebrowEl = document.getElementById("heroEyebrow");
    var lineEl = document.getElementById("heroStateLine");
    var ctaEl = document.getElementById("heroCta");
    var ctaLabelEl = document.getElementById("heroCtaLabel");
    var activeIdx = 0;

    function selectHero(idx) {
      var n = slides.length;
      if (!n) return;
      idx = ((idx % n) + n) % n;
      if (idx === activeIdx) return;
      activeIdx = idx;

      var source = stateBtns[idx] || indexBtns[idx];
      if (!source) return;
      var data = source.dataset;

      slides.forEach(function (node, i) {
        node.classList.toggle("is-active", i === idx);
      });
      stateBtns.forEach(function (node, i) {
        node.classList.toggle("is-active", i === idx);
        node.setAttribute("aria-pressed", i === idx ? "true" : "false");
      });
      indexBtns.forEach(function (node, i) {
        node.classList.toggle("is-active", i === idx);
      });
      hero.style.setProperty("--accent", data.heroHex);

      if (!textWrap) return;
      textWrap.classList.add("is-fading");
      setTimeout(function () {
        if (eyebrowEl) eyebrowEl.textContent = data.heroMood;
        if (lineEl) lineEl.textContent = data.heroLine;
        if (ctaLabelEl) ctaLabelEl.textContent = "Shop " + data.heroNum + " " + data.heroName;
        if (ctaEl) ctaEl.setAttribute("href", "/states/" + data.heroSelect);
        textWrap.classList.remove("is-fading");
      }, 160);
    }

    stateBtns.concat(indexBtns).forEach(function (btn) {
      btn.addEventListener("click", function () {
        var group = btn.classList.contains("hero-index-item") ? indexBtns : stateBtns;
        selectHero(group.indexOf(btn));
      });
    });

    var touchStartX = null;
    hero.addEventListener(
      "touchstart",
      function (e) {
        touchStartX = e.changedTouches[0].clientX;
      },
      { passive: true }
    );
    hero.addEventListener(
      "touchend",
      function (e) {
        if (touchStartX == null) return;
        var dx = e.changedTouches[0].clientX - touchStartX;
        touchStartX = null;
        if (Math.abs(dx) < 40) return;
        selectHero(activeIdx + (dx < 0 ? 1 : -1));
      },
      { passive: true }
    );
  }

  /* ---------- Shop the Look ---------- */
  var lookFrame = document.querySelector("[data-look]");
  if (lookFrame) {
    var hotspots = Array.prototype.slice.call(lookFrame.querySelectorAll("[data-look-toggle]"));
    var cards = Array.prototype.slice.call(lookFrame.querySelectorAll("[data-look-card]"));
    var openSpot = null;

    function renderLook() {
      hotspots.forEach(function (btn) {
        btn.classList.toggle("is-open", btn.dataset.lookToggle === openSpot);
      });
      cards.forEach(function (card) {
        card.hidden = card.dataset.lookCard !== openSpot;
      });
    }

    hotspots.forEach(function (btn) {
      btn.addEventListener("click", function () {
        openSpot = openSpot === btn.dataset.lookToggle ? null : btn.dataset.lookToggle;
        renderLook();
      });
    });
  }

  /* ---------- Find your State ---------- */
  var quiz = document.querySelector("[data-quiz]");
  if (quiz) {
    var moodBtns = Array.prototype.slice.call(quiz.querySelectorAll("[data-quiz-mood]"));
    var results = Array.prototype.slice.call(quiz.querySelectorAll("[data-quiz-result]"));

    moodBtns.forEach(function (btn) {
      btn.addEventListener("click", function () {
        var slug = btn.dataset.quizMood;
        moodBtns.forEach(function (other) {
          other.classList.toggle("is-selected", other === btn);
        });
        results.forEach(function (result) {
          result.hidden = result.dataset.quizResult !== slug;
        });
        quiz.style.setProperty("--accent", btn.dataset.quizHex);
      });
    });
  }

  /* ---------- Newsletter ---------- */
  var newsletterForm = document.querySelector("[data-newsletter-form]");
  if (newsletterForm) {
    newsletterForm.addEventListener("submit", function (e) {
      e.preventDefault();
      var success = document.querySelector("[data-newsletter-success]");
      newsletterForm.hidden = true;
      if (success) success.hidden = false;
    });
  }
})();
