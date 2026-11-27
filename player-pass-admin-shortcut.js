/* DON-only Developer Control Room shortcut.
 * DEVELOPMENT ONLY: activate after Player Pass auth and role RPC are deployed.
 * Requires the existing #arcade-developer-template and Arcade Control Panel.
 * The hidden robot gesture stays intact until this integration is enabled.
 */
export async function installAdminControlRoomShortcut({
  supabase, controlPanel, refreshOnAuthChange = true,
}) {
  if (!supabase?.auth || !controlPanel) throw new Error("Admin shortcut setup incomplete");
  const template = document.getElementById("arcade-developer-template");
  const room = document.getElementById("arcade-developer-control");
  if (!template || !room) throw new Error("Existing Developer Control Room not found");
  const entry = document.createElement("button");
  entry.type = "button";
  entry.id = "arcade-admin-room-shortcut";
  entry.textContent = "🤖 DEVELOPER CONTROL ROOM";
  entry.hidden = true;
  entry.style.cssText = "display:none;width:100%;margin-top:16px;padding:13px;border:1px solid #6deeff;border-radius:10px;background:#170d2c;color:#8cff7b;font:700 15px system-ui,sans-serif;cursor:pointer";
  controlPanel.append(entry); // last item at bottom of existing Control Panel

  let verified = false;
  let generation = 0;
  function conceal() {
    verified = false;
    entry.hidden = true;
    entry.style.display = "none";
    const inner = document.getElementById("arcade-developer-control-inner");
    if (inner) inner.open = false;
    room.hidden = true;
    room.style.setProperty("display", "none", "important");
  }
  async function refresh() {
    const current = ++generation;
    conceal();
    try {
      const { data: sessionData, error: sessionError } = await supabase.auth.getSession();
      if (sessionError || !sessionData?.session?.access_token) return;
      const { data: userData, error: userError } = await supabase.auth.getUser();
      if (userError || !userData?.user || userData.user.id !== sessionData.session.user.id) return;
      const { data, error } = await supabase.rpc("arcade_my_player_pass_role");
      if (current !== generation || error) return;
      const role = Array.isArray(data) ? data[0] : data;
      // DON is the only approved administrator. The server role is authoritative;
      // the initials check is a display guard, NOT a substitute for that role.
      if (role?.iscored_handle !== "DON" || role?.is_admin !== true) return;
      verified = true;
      entry.hidden = false;
      entry.style.display = "block";
    } catch (_) { /* fail closed */ }
  }
  entry.addEventListener("click", () => {
    if (!verified) return;
    // The existing template is moved into the room only after authorization.
    if (!room.querySelector("#arcade-developer-control-inner")) {
      room.append(template.content);
    }
    const inner = document.getElementById("arcade-developer-control-inner");
    if (!inner) return;
    room.hidden = false;
    room.style.setProperty("display", "block", "important");
    inner.hidden = false;
    inner.open = !inner.open;
    if (inner.open) inner.scrollIntoView({ behavior: "smooth", block: "nearest" });
  });
  let subscription;
  if (refreshOnAuthChange) {
    const result = supabase.auth.onAuthStateChange(() => {
      // Schedule outside Auth's synchronous callback to avoid auth-lock deadlocks.
      queueMicrotask(() => { void refresh(); });
    });
    subscription = result?.data?.subscription;
  }
  await refresh();
  return { refresh, destroy() { ++generation; conceal(); subscription?.unsubscribe(); entry.remove(); } };
}
