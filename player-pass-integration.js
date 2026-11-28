/* Stage 1 Player Pass integration adapter. DEVELOPMENT ONLY — not loaded by index.html.
 * Caller supplies the existing configured Supabase client, approved handles,
 * deployed Edge Function base URL and a real Turnstile token callback.
 * Do not enable until migrations, endpoints, operator bootstrap and tests pass.
 */
import { mountPlayerPass } from "./player-pass-ui.js";
import { mountOperatorGitHubLogin } from "./player-pass-github-operator.js";
import { installAdminControlRoomShortcut } from "./player-pass-admin-shortcut.js";

export async function mountArcadePlayerPass({
  supabase, handles, endpoint, getTurnstileToken,
  redirectTo = "https://g1lgamesh20.github.io/big-daddys-arcade/",
}) {
  if (!supabase?.auth || !Array.isArray(handles) || !endpoint ||
      typeof getTurnstileToken !== "function") {
    throw new Error("Player Pass integration prerequisites missing");
  }
  const panel = document.querySelector("#arcade-settings-panel > .arcade-settings-body");
  if (!panel) throw new Error("Arcade Control Panel missing");
  if (document.getElementById("arcade-player-pass-host")) {
    throw new Error("Player Pass already mounted");
  }

  const host = document.createElement("div");
  host.id = "arcade-player-pass-host";
  panel.append(host);
  const loginHost = document.createElement("div");
  host.append(loginHost);
  const operatorHost = document.createElement("div");
  host.append(operatorHost);

  // Roll back partial UI mounts if the operator shortcut cannot initialize.
  let login, pass, shortcut;
  let operatorGeneration = 0;
  async function refreshOperator() {
    const current = ++operatorGeneration;
    operatorHost.replaceChildren();
    try {
      const { data: userData, error: userError } = await supabase.auth.getUser();
      if (userError || !userData?.user || userData.user.is_anonymous ||
          !userData.user.app_metadata?.providers?.includes("github")) return;
      const { data, error } = await supabase.rpc("arcade_my_player_pass_role");
      if (current !== operatorGeneration || error) return;
      const role = Array.isArray(data) ? data[0] : data;
      if (role?.iscored_handle !== "DON" || role?.is_admin !== true) return;
      // The issuance endpoint independently checks DON UUID, bound device and role.
      mountPlayerPass({
        host: operatorHost, supabase, handles, endpoint, getTurnstileToken,
        operatorHost, operatorEnabled: true, operatorSupabase: supabase,
      }).remove(); // Operator controls remain; discard duplicate player form.
    } catch (_) { operatorHost.replaceChildren(); }
  }
  try {
    login = mountOperatorGitHubLogin({
      host: loginHost, operatorSupabase: supabase, redirectTo,
      onVerified: () => { void refreshOperator(); },
    });
    pass = mountPlayerPass({
      host, supabase, handles, endpoint, getTurnstileToken,
    });
    await refreshOperator();
    shortcut = await installAdminControlRoomShortcut({
      supabase, controlPanel: panel,
    });
  } catch (error) {
    ++operatorGeneration;
    shortcut?.destroy();
    login?.element.remove();
    pass?.remove();
    host.remove();
    throw error;
  }
  // The existing Test Lab remains accessible via the Space Invader gesture;
  // the old robot unlock must stay disabled in index.html.
  return {
    refresh: async () => {
      await login.verify();
      await shortcut.refresh();
      await refreshOperator();
    },
    destroy: () => {
      ++operatorGeneration;
      shortcut.destroy();
      login.element.remove();
      pass.remove();
      host.remove();
    },
  };
}
