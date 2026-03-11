/**
 * companion.js
 */

// ─── XP TOAST ───────────────────────────────────────────────
function showXpToast(amount, alreadyMastered) {
  const toast = document.getElementById("xp-toast");
  if (!toast) return;

  if (alreadyMastered) {
    toast.textContent = "MASTERED ✓";
  } else if (amount > 0) {
    toast.textContent = "+" + amount + " XP";
  } else {
    return;
  }

  toast.classList.add("show");
  setTimeout(function () {
    toast.classList.remove("show");
  }, 1800);
}


// ─── ANSWER BUTTONS ─────────────────────────────────────────
// BUG FIX: disable OTHER buttons only AFTER the clicked one
// has already been included in the form submission.
// We do this by letting the submit happen naturally, then
// disabling the rest in the next event loop tick.
document.addEventListener("DOMContentLoaded", function () {
  const opts = document.querySelectorAll(".opt");

  opts.forEach(function (btn) {
    btn.addEventListener("click", function () {
      // Use setTimeout(0) so the browser registers this button's
      // value in the form submission BEFORE we disable anything
      setTimeout(function () {
        opts.forEach(function (o) {
          o.disabled = true;
        });
      }, 0);
    });
  });
});


// ─── BACK BUTTON GUARD ──────────────────────────────────────
document.addEventListener("DOMContentLoaded", function () {
  const guard = document.querySelector("[data-session-ended]");
  if (guard) {
    window.location.replace("/");
  }
});


