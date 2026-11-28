/* Cloudflare Turnstile token provider for Player Pass (draft only).
 * Supply the PUBLIC site key. Never include the Turnstile secret in browser code.
 * Render an explicit widget and obtain a fresh, single-use token for each attempt.
 */
export function createPlayerPassTurnstile({ host, siteKey }) {
  if (!host || !/^[A-Za-z0-9_-]{8,100}$/.test(siteKey || "")) {
    throw new Error("Turnstile host and public site key required");
  }
  if (typeof window.turnstile?.render !== "function") {
    throw new Error("Cloudflare Turnstile script not loaded");
  }
  let destroyed = false;
  let widgetId;
  let pending = null;
  let readyToken = null;
  const widget = document.createElement("div");
  host.append(widget);
  function fail(message) {
    readyToken = null;
    if (pending) {
      pending.reject(new Error(message));
      pending = null;
    }
  }
  widgetId = window.turnstile.render(widget, {
    sitekey: siteKey,
    execution: "render",
    callback(token) {
      if (destroyed) return;
      readyToken = token;
      if (pending) {
        pending.resolve(token);
        pending = null;
        readyToken = null;
      }
    },
    "expired-callback": () => fail("Human verification expired. Please retry."),
    "error-callback": () => fail("Human verification unavailable. Please retry."),
    "timeout-callback": () => fail("Human verification timed out. Please retry."),
  });
  async function getTurnstileToken() {
    if (destroyed) throw new Error("Verification widget unavailable");
    if (pending) throw new Error("Verification already in progress");
    if (readyToken) {
      const token = readyToken;
      readyToken = null;
      // Do not reset here: resetting can invalidate the token before Siteverify.
      return token;
    }
    return new Promise((resolve, reject) => {
      pending = { resolve, reject };
      // Reset to request a new challenge, including after an expired attempt.
      window.turnstile.reset(widgetId);
    });
  }
  function destroy() {
    destroyed = true;
    fail("Verification closed");
    window.turnstile.remove(widgetId);
    widget.remove();
  }
  return { getTurnstileToken, destroy };
}
