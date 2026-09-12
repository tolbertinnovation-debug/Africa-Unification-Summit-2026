(function () {
  "use strict";

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
