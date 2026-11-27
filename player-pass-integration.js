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

  // One Supabase Auth client for DON's GitHub session and DON's Player Pass.
  const login = mountOperatorGitHubLogin({
    host: loginHost, operatorSupabase: supabase, redirectTo,
  });
  const pass = mountPlayerPass({
    host, supabase, handles, endpoint, getTurnstileToken,
  });
  const shortcut = await installAdminControlRoomShortcut({
    supabase, controlPanel: panel,
  });
  // The existing Test Lab remains accessible via the Space Invader gesture;
  // the old robot unlock must stay disabled in index.html.
  return {
    refresh: async () => {
      await login.verify();
      await shortcut.refresh();
    },
    destroy: () => {
      shortcut.destroy();
      login.element.remove();
      pass.remove();
      host.remove();
    },
  };
}
