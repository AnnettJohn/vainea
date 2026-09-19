/* Header-Verhalten aus dem Click-Dummy: Mega-Menüs und der transparente
   Header über dem Hero (updateHeaderTransparency). Auf jeder Seite geladen. */
(function () {
  "use strict";

  var header = document.getElementById("siteHeader");
  if (!header) return;

  var toggles = Array.prototype.slice.call(document.querySelectorAll("[data-menu-toggle]"));
  var panels = Array.prototype.slice.call(document.querySelectorAll("[data-menu-panel]"));
  var openMenu = null;

  function renderMenu() {
    toggles.forEach(function (btn) {
      btn.classList.toggle("is-open", btn.dataset.menuToggle === openMenu);
      btn.setAttribute("aria-expanded", btn.dataset.menuToggle === openMenu ? "true" : "false");
    });
    panels.forEach(function (panel) {
      panel.hidden = panel.dataset.menuPanel !== openMenu;
    });
    updateHeaderTransparency();
  }

  toggles.forEach(function (btn) {
    btn.setAttribute("aria-expanded", "false");
    btn.addEventListener("click", function () {
      openMenu = openMenu === btn.dataset.menuToggle ? null : btn.dataset.menuToggle;
      renderMenu();
    });
  });

  document.addEventListener("click", function (e) {
    if (openMenu && !e.target.closest(".site-header")) {
      openMenu = null;
      renderMenu();
    }
  });

  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && openMenu) {
      openMenu = null;
      renderMenu();
    }
  });

  function updateHeaderTransparency() {
    if (openMenu) {
      header.classList.remove("is-transparent");
      return;
    }
    var hero = document.getElementById("heroSection");
    if (!hero) {
      header.classList.remove("is-transparent");
      return;
    }
    var headerH = header.offsetHeight || 76;
    header.classList.toggle("is-transparent", hero.getBoundingClientRect().bottom > headerH);
  }

  window.addEventListener("scroll", updateHeaderTransparency, { passive: true });
  window.addEventListener("resize", updateHeaderTransparency);
  updateHeaderTransparency();

  /* Toast nach dem Add-to-Bag wieder ausblenden (showToast im Click-Dummy). */
  var toastTimer = null;
  document.body.addEventListener("htmx:afterSwap", function (e) {
    if (e.target.id !== "cart-toast") return;
    var quickadd = e.detail && e.detail.requestConfig && e.detail.requestConfig.elt;
    if (quickadd) {
      var details = quickadd.closest("details.quickadd");
      if (details) details.open = false;
    }
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () {
      e.target.innerHTML = "";
    }, 2400);
  });
})();
