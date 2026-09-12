(function () {
  "use strict";

  var videoTriggers = document.querySelectorAll(".ekit-video-popup-btn");
  var videoModal;
  var modalVideo;
  var lastVideoTrigger;

  var closeVideo = function () {
    if (!videoModal || videoModal.hidden) return;
    modalVideo.pause();
    videoModal.classList.remove("is-visible");
    document.body.classList.remove("aus-video-open");
    window.setTimeout(function () {
      videoModal.hidden = true;
      modalVideo.removeAttribute("src");
      modalVideo.load();
      if (lastVideoTrigger) lastVideoTrigger.focus();
    }, 220);
  };

  if (videoTriggers.length) {
    videoModal = document.createElement("div");
    videoModal.className = "aus-video-modal";
    videoModal.hidden = true;
    videoModal.setAttribute("role", "dialog");
    videoModal.setAttribute("aria-modal", "true");
    videoModal.setAttribute("aria-label", "Africa Unification Summit video");
    videoModal.innerHTML =
      '<div class="aus-video-modal__dialog">' +
      '<div class="aus-video-modal__bar"><strong>Africa Unification Summit 2026</strong>' +
      '<button class="aus-video-modal__close" type="button" aria-label="Close video">\u00d7</button></div>' +
      '<video controls playsinline preload="metadata"></video>' +
      '<p class="aus-video-modal__hint">Use the video controls to play, pause, adjust volume, or enter full screen.</p>' +
      '</div>';
    document.body.appendChild(videoModal);
    modalVideo = videoModal.querySelector("video");

    videoModal.querySelector(".aus-video-modal__close").addEventListener("click", closeVideo);
    videoModal.addEventListener("click", function (event) {
      if (event.target === videoModal) closeVideo();
    });
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape") closeVideo();
    });

    videoTriggers.forEach(function (trigger) {
      trigger.addEventListener("click", function (event) {
        event.preventDefault();
        var selector = trigger.getAttribute("href");
        var sourceWrap = selector && selector.charAt(0) === "#" ? document.querySelector(selector) : null;
        var sourceNode = sourceWrap && sourceWrap.querySelector("video source");
        var sourceVideo = sourceWrap && sourceWrap.querySelector("video");
        var sourceUrl = sourceNode
          ? (sourceNode.src || sourceNode.getAttribute("src"))
          : sourceVideo && (sourceVideo.currentSrc || sourceVideo.src || sourceVideo.getAttribute("src"));
        if (!sourceUrl) return;

        lastVideoTrigger = trigger;
        modalVideo.src = sourceUrl;
        var hero = trigger.closest("section, .e-con, .elementor-section");
        var heroImage = hero && window.getComputedStyle(hero).backgroundImage;
        var posterMatch = heroImage && heroImage.match(/url\(["']?(.*?)["']?\)/);
        if (posterMatch && posterMatch[1]) modalVideo.poster = posterMatch[1];
        videoModal.hidden = false;
        document.body.classList.add("aus-video-open");
        window.requestAnimationFrame(function () { videoModal.classList.add("is-visible"); });
        modalVideo.play().catch(function () {
          /* Browser autoplay policies may require the visible native play control. */
        });
        videoModal.querySelector(".aus-video-modal__close").focus();
      });
    });
  }

  var menuLinks = document.querySelectorAll(".aus-site-menu nav a");
  var cleanPath = function (value) {
    return value.replace(/index\.html$/i, "").replace(/\/+$/, "") || "/";
  };
  var currentPath = cleanPath(window.location.pathname);

  menuLinks.forEach(function (link) {
    var linkPath = cleanPath(new URL(link.href, window.location.href).pathname);
    if (linkPath === currentPath) {
      link.classList.add("is-current");
      link.setAttribute("aria-current", "page");
    }

    link.addEventListener("click", function (event) {
      if (event.button > 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      event.preventDefault();
      menuLinks.forEach(function (item) { item.classList.remove("is-selected"); });
      link.classList.add("is-selected");
      window.setTimeout(function () { window.location.assign(link.href); }, 180);
    });
  });

  var applicationLinks = document.querySelectorAll('a[href*="forms.gle"]');
  if (!applicationLinks.length) return;

  var toast = document.createElement("div");
  toast.className = "aus-application-toast";
  toast.setAttribute("role", "status");
  toast.setAttribute("aria-live", "polite");
  toast.innerHTML =
    '<span class="aus-application-toast__check" aria-hidden="true">\u2713</span>' +
    '<span><strong>Great choice!</strong><span>You\u2019re taking a positive step toward Africa\u2019s shared future.</span></span>';
  document.body.appendChild(toast);

  var hideTimer;
  applicationLinks.forEach(function (link) {
    link.classList.add("aus-apply-action");

    link.addEventListener("click", function (event) {
      clearTimeout(hideTimer);
      link.classList.add("is-clicked");

      var rect = link.getBoundingClientRect();
      var ripple = document.createElement("span");
      ripple.className = "aus-apply-action__ripple";
      ripple.style.left = event.clientX ? event.clientX - rect.left + "px" : "50%";
      ripple.style.top = event.clientY ? event.clientY - rect.top + "px" : "50%";
      link.appendChild(ripple);

      toast.classList.add("is-visible");
      hideTimer = window.setTimeout(function () {
        toast.classList.remove("is-visible");
        link.classList.remove("is-clicked");
        ripple.remove();
      }, 4200);
    });
  });
})();
