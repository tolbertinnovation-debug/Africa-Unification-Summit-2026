/* Partnership enquiry form.
 *
 * The site is a static mirror on GitHub Pages, so there is no server of our
 * own to receive submissions. Set ENDPOINT below to a form backend that
 * accepts a POST (Formspree, Getform, Web3Forms, a Google Apps Script web app,
 * or any endpoint that allows cross-origin POSTs) and enquiries are delivered
 * straight to it.
 *
 * While ENDPOINT is empty the form still works: it validates, then hands the
 * completed enquiry to the visitor's email app addressed to the Summit, and
 * also shows the text so it can be copied if no mail app opens. */

(function () {
  "use strict";

  var ENDPOINT = "";
  var SUMMIT_EMAIL = "info@africaunificationsummit.org";

  var form = document.getElementById("partner-form");
  if (!form) return;

  var status = document.getElementById("partner-status");
  var submit = form.querySelector(".aus-partner__submit");

  var errorFor = function (key) {
    return form.querySelector('[data-error-for="' + key + '"]');
  };

  var setError = function (key, field, shown) {
    var message = errorFor(key);
    if (message) message.classList.toggle("is-shown", shown);
    if (field) field.setAttribute("aria-invalid", shown ? "true" : "false");
  };

  var interests = function () {
    return Array.prototype.slice
      .call(form.querySelectorAll('input[name="Interest"]:checked'))
      .map(function (box) { return box.value; });
  };

  /* Returns the first invalid field so we can move focus to it. */
  var validate = function () {
    var firstInvalid = null;

    form.querySelectorAll("input[required], select[required], textarea[required]").forEach(function (field) {
      if (field.type === "checkbox") return;
      var ok = field.value.trim() !== "" && field.checkValidity();
      setError(field.id, field, !ok);
      if (!ok && !firstInvalid) firstInvalid = field;
    });

    var website = form.querySelector("#website");
    var websiteOk = website.value.trim() === "" || website.checkValidity();
    setError("website", website, !websiteOk);
    if (!websiteOk && !firstInvalid) firstInvalid = website;

    var chosen = interests().length > 0;
    setError("Interest", null, !chosen);
    if (!chosen && !firstInvalid) firstInvalid = form.querySelector('input[name="Interest"]');

    var consent = form.querySelector("#consent");
    setError("consent", consent, !consent.checked);
    if (!consent.checked && !firstInvalid) firstInvalid = consent;

    return firstInvalid;
  };

  var collect = function () {
    var data = {};
    ["org", "orgtype", "country", "website", "name", "role", "email", "phone", "level", "budget", "message"].forEach(function (id) {
      var field = form.querySelector("#" + id);
      var value = field.value.trim();
      if (value) data[field.name] = value;
    });
    data.Interest = interests().join(", ");
    data.Consent = "Yes";
    return data;
  };

  var asText = function (data) {
    return Object.keys(data).map(function (key) {
      return key + ": " + data[key];
    }).join("\n");
  };

  var show = function (kind, title, body, extra) {
    status.className = "aus-partner__status is-shown aus-partner__status--" + kind;
    status.innerHTML =
      '<span aria-hidden="true">' + (kind === "ok" ? "✓" : kind === "bad" ? "⚠" : "✉") + "</span>" +
      "<div><strong>" + title + "</strong><span>" + body + "</span></div>";
    if (extra) status.querySelector("div").appendChild(extra);
    status.scrollIntoView({ block: "center", behavior: "smooth" });
  };

  /* Shown when there is no endpoint, so the enquiry is never lost even if the
     visitor has no mail app configured. */
  var copyPanel = function (text) {
    var wrap = document.createElement("div");
    wrap.className = "aus-partner__copy";

    var box = document.createElement("textarea");
    box.readOnly = true;
    box.value = text;
    box.setAttribute("aria-label", "Your partnership enquiry");

    var button = document.createElement("button");
    button.type = "button";
    button.textContent = "Copy enquiry";
    button.addEventListener("click", function () {
      box.select();
      var done = function () { button.textContent = "Copied"; };
      if (navigator.clipboard) {
        navigator.clipboard.writeText(text).then(done, function () { document.execCommand("copy"); done(); });
      } else {
        document.execCommand("copy");
        done();
      }
    });

    wrap.appendChild(box);
    wrap.appendChild(button);
    return wrap;
  };

  form.addEventListener("submit", function (event) {
    event.preventDefault();

    var invalid = validate();
    if (invalid) {
      show("bad", "Please check the highlighted fields", "A few details are missing or need correcting before we can send your enquiry.");
      invalid.focus();
      return;
    }

    var data = collect();
    var subject = "Partnership enquiry - " + data.Organisation;

    if (!ENDPOINT) {
      var body = asText(data);
      window.location.href =
        "mailto:" + SUMMIT_EMAIL +
        "?subject=" + encodeURIComponent(subject) +
        "&body=" + encodeURIComponent(body);
      show(
        "warn",
        "Almost there — send the email to finish",
        "We have opened your email app with the enquiry ready to send to " + SUMMIT_EMAIL +
        ". If nothing opened, copy the details below and email them to us.",
        copyPanel(body)
      );
      return;
    }

    submit.disabled = true;
    submit.textContent = "Sending…";

    fetch(ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(Object.assign({ _subject: subject }, data))
    })
      .then(function (response) {
        if (!response.ok) throw new Error("Request failed with status " + response.status);
        form.reset();
        show("ok", "Thank you — your enquiry is on its way",
          "Our partnerships team will be in touch shortly. A copy has been sent to " + SUMMIT_EMAIL + ".");
      })
      .catch(function () {
        show("bad", "We could not send that just now",
          'Please try again, or email your enquiry to <a href="mailto:' + SUMMIT_EMAIL + '">' + SUMMIT_EMAIL + "</a>.",
          copyPanel(asText(data)));
      })
      .finally(function () {
        submit.disabled = false;
        submit.textContent = "Send partnership enquiry";
      });
  });

  /* Clear a field's error as soon as the visitor fixes it. */
  form.addEventListener("input", function (event) {
    var field = event.target;
    if (field.name === "Interest") {
      if (interests().length) setError("Interest", null, false);
      return;
    }
    if (field.id === "consent") {
      if (field.checked) setError("consent", field, false);
      return;
    }
    if (field.id && errorFor(field.id) && field.value.trim() !== "" && field.checkValidity()) {
      setError(field.id, field, false);
    }
  });
})();
