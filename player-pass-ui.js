/* Big Daddy's Arcade Player Pass UI — DEVELOPMENT ONLY.
 * Import and call mountPlayerPass() after server endpoints are deployed/tested.
 * No auth secrets are bundled here. Operator UI visibility is NOT authorization.
 */
export function mountPlayerPass({ host, supabase, handles, endpoint, operatorHost, operatorEnabled = false }) {
  if (!host || !supabase || !endpoint || !Array.isArray(handles)) throw new Error("Player Pass setup incomplete");
  const cleanHandles = [...new Set(handles.map(x => String(x).trim().toUpperCase()).filter(x => /^[A-Z0-9 ]{1,24}$/.test(x)))].sort();
  const wrapper = document.createElement("section");
  wrapper.className = "player-pass";
  wrapper.innerHTML = `
    <style>
      .player-pass{padding:16px;border:1px solid #fe47c7;border-radius:14px;background:#120d24;color:#fff;margin:16px 0}
      .player-pass h3{color:#8cff7b;margin:0 0 8px}
      .player-pass label{display:block;margin:12px 0 5px;font-weight:700}
      .player-pass select,.player-pass input{box-sizing:border-box;width:100%;max-width:420px;padding:11px;border-radius:8px;border:1px solid #6deeff;background:#080718;color:#fff;font:inherit}
      .player-pass button{margin-top:12px;padding:11px 16px;border:1px solid #fe47c7;border-radius:9px;background:#291136;color:#fff;font-weight:700;cursor:pointer}
      .player-pass button:disabled{opacity:.55;cursor:wait}
      .player-pass [role=status]{margin-top:10px;min-height:20px}
    </style>
    <h3>👾 ACTIVATE YOUR PLAYER PASS</h3>
    <p>One code. One device. No password. Ask Big Daddy for your private code.</p>
    <form>
      <label for="player-pass-handle">WHO ARE YOU?</label>
      <select id="player-pass-handle" name="handle" required><option value="">Choose your iScored initials</option></select>
      <label for="player-pass-code">YOUR SECRET ARCADE CODE</label>
      <input id="player-pass-code" name="code" placeholder="PACMAN-1A2B" autocapitalize="characters" autocomplete="off" spellcheck="false" maxlength="17" required>
      <button type="submit">🔐 ACTIVATE PLAYER PASS</button>
    </form>
    <div role="status" aria-live="polite"></div>
  `;
  const form = wrapper.querySelector("form");
  const status = wrapper.querySelector('[role="status"]');
  const select = wrapper.querySelector("select");
  const button = form.querySelector("button");
  for (const handle of cleanHandles) select.add(new Option(handle, handle));
  host.append(wrapper);

  async function authSession() {
    const { data: current } = await supabase.auth.getSession();
    if (current?.session?.access_token) return current.session;
    const { data, error } = await supabase.auth.signInAnonymously();
    if (error || !data?.session) throw new Error("Device sign-in unavailable");
    return data.session;
  }
  async function send(action, payload) {
    const session = await authSession();
    const response = await fetch(endpoint.replace(/\/$/, "") + "/" + action, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + session.access_token,
        "apikey": supabase.supabaseKey,
      },
      body: JSON.stringify(payload),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error || "Unable to complete request");
    return data;
  }
  form.addEventListener("submit", async event => {
    event.preventDefault();
    const initials = select.value;
    const code = form.elements.code.value.trim().toUpperCase();
    if (!/^[A-Z]{3,12}-[A-Z0-9]{4}$/.test(code)) {
      status.textContent = "Enter your arcade code, for example PACMAN-1A2B.";
      return;
    }
    button.disabled = true;
    status.textContent = "Activating your Player Pass…";
    try {
      const result = await send("player-pass-redeem", { initials, code });
      if (!result.activated) throw new Error("Activation could not be confirmed");
      status.textContent = "🏆 " + result.initials + " — PLAYER PASS ACTIVATED!";
      form.hidden = true;
    } catch (error) {
      status.textContent = error.message || "Activation unavailable. Ask Big Daddy for help.";
    } finally {
      button.disabled = false;
    }
  });

  // Only mount the operator controls after a server-verified operator session.
  // operatorEnabled is a UI hint; server independently enforces operator user ID.
  if (operatorEnabled && operatorHost) {
    const admin = document.createElement("section");
    admin.className = "player-pass";
    admin.innerHTML = `
      <h3>🤖 ISSUE ARCADE PLAYER PASS</h3>
      <form>
        <label for="player-pass-admin-handle">PLAYER</label>
        <select id="player-pass-admin-handle" required><option value="">Select player</option></select>
        <label for="player-pass-admin-prefix">ARCADE GAME</label>
        <select id="player-pass-admin-prefix">
          <option>PACMAN</option><option>GALAGA</option><option>FROGGER</option>
          <option>DIGDUG</option><option>QBERT</option><option>CENTIPEDE</option>
          <option>ASTEROIDS</option><option>TEMPEST</option>
        </select>
        <button type="submit">🎟️ GENERATE SINGLE-USE CODE</button>
      </form>
      <output aria-live="polite"></output>
      <p>Copy and send privately. Codes expire after seven days.</p>
    `;
    const adminSelect = admin.querySelector("#player-pass-admin-handle");
    for (const handle of cleanHandles) adminSelect.add(new Option(handle, handle));
    admin.querySelector("form").addEventListener("submit", async event => {
      event.preventDefault();
      const output = admin.querySelector("output");
      const btn = admin.querySelector("button");
      btn.disabled = true;
      output.textContent = "Generating…";
      try {
        // Operator auth is separate from anonymous player activation.
        // Never silently sign in anonymously for an operator action.
        const { data } = await supabase.auth.getSession();
        if (!data?.session || data.session.user?.is_anonymous) throw new Error("Verified operator sign-in required");
        const response = await fetch(endpoint.replace(/\/$/, "") + "/player-pass-operator", {
          method: "POST",
          headers: { "Content-Type": "application/json", Authorization: "Bearer " + data.session.access_token, apikey: supabase.supabaseKey },
          body: JSON.stringify({ initials: adminSelect.value, prefix: admin.querySelector("#player-pass-admin-prefix").value }),
        });
        const result = await response.json().catch(() => ({}));
        if (!response.ok || !result.code) throw new Error(result.error || "Could not issue code");
        output.textContent = result.initials + ": " + result.code + " (expires " + new Date(result.expires_at).toLocaleDateString() + ")";
      } catch (error) {
        output.textContent = error.message || "Unable to generate code";
      } finally { btn.disabled = false; }
    });
    operatorHost.append(admin);
  }
  return wrapper;
}
