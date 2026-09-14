/* Partnership enquiry form.
 *
 * The site is a static mirror on GitHub Pages, so there is no server of our
 * own to receive submissions. Enquiries are posted to FormSubmit, which
 * forwards them by email to the address in ENDPOINT.
 *
 * FormSubmit needs a one-time activation: the first submission sends a
 * confirmation email to that address, and enquiries are only delivered once
 * the link in it has been clicked.
 *
 * If the request cannot be delivered, the form falls back to handing the
 * enquiry to the visitor's email app and showing the text with a copy button,
 * so a submission is never silently lost. */

(function () {
  "use strict";

  var SUMMIT_EMAIL = "africaunificationsummit@gmail.com";
  var ENDPOINT = "https://formsubmit.co/ajax/" + SUMMIT_EMAIL;

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

  /* Shown when the enquiry could not be posted, so it is never lost. */
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

  var fallbackToEmail = function (data, subject, title, body) {
    window.location.href =
      "mailto:" + SUMMIT_EMAIL +
      "?subject=" + encodeURIComponent(subject) +
      "&body=" + encodeURIComponent(asText(data));
    show("warn", title, body, copyPanel(asText(data)));
  };

  form.addEventListener("submit", function (event) {
    event.preventDefault();

    var invalid = validate();
    if (invalid) {
      show("bad", "Please check the highlighted fields", "A few details are missing or need correcting before we can send your enquiry.");
      invalid.focus();
      return;
    }

    /* Bots fill hidden fields; people do not. Accept it quietly and stop. */
    var honey = form.querySelector('input[name="_honey"]');
    if (honey && honey.value !== "") {
      show("ok", "Thank you — your enquiry is on its way", "Our partnerships team will be in touch shortly.");
      form.reset();
      return;
    }

    var data = collect();
    var subject = "Partnership enquiry - " + data.Organisation;

    if (!ENDPOINT) {
      fallbackToEmail(data, subject, "Almost there — send the email to finish",
        "We have opened your email app with the enquiry ready to send to " + SUMMIT_EMAIL +
        ". If nothing opened, copy the details below and email them to us.");
      return;
    }

    submit.disabled = true;
    submit.textContent = "Sending…";

    /* Underscore-prefixed keys are FormSubmit settings, not form answers. */
    var payload = Object.assign({
      _subject: subject,
      _replyto: data.Email,
      _template: "table",
      _captcha: "false"
    }, data);

    fetch(ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(payload)
    })
      .then(function (response) {
        return response.json().catch(function () { return {}; }).then(function (result) {
          /* FormSubmit reports success as the string "true". */
          if (!response.ok || String(result.success) !== "true") {
            throw new Error(result.message || "Request failed with status " + response.status);
          }
          form.reset();
          show("ok", "Thank you — your enquiry is on its way",
            "Our partnerships team will review it and be in touch shortly.");
        });
      })
      .catch(function () {
        fallbackToEmail(data, subject, "We could not send that automatically",
          "Your enquiry is ready in your email app, addressed to " + SUMMIT_EMAIL +
          ". If nothing opened, copy the details below and email them to us.");
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
