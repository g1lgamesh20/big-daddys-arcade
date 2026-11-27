/* DON operator GitHub OAuth login — DEVELOPMENT ONLY.
 * Supabase GitHub provider and redirect allowlist must be configured first.
 * GitHub identity alone NEVER grants administrator privileges: the server must
 * also check the allowlisted Auth UUID, active device binding and admin role.
 */
export function mountOperatorGitHubLogin({ host, operatorSupabase, redirectTo, onVerified }) {
  if (!host || !operatorSupabase?.auth || !redirectTo) throw new Error("Operator login setup incomplete");
  const section = document.createElement("section");
  section.className = "player-pass-operator-login";
  const button = document.createElement("button");
  button.type = "button";
  button.textContent = "🐙 SIGN IN WITH GITHUB (DON)";
  const status = document.createElement("p");
  status.setAttribute("role", "status");
  status.setAttribute("aria-live", "polite");
  section.append(button, status);
  host.append(section);
  async function verify() {
    button.hidden = false;
    try {
      const { data: userData, error: userError } = await operatorSupabase.auth.getUser();
      if (userError || !userData?.user || userData.user.is_anonymous ||\n          !userData.user.app_metadata?.providers?.includes("github")) return false;
      const { data, error } = await operatorSupabase.rpc("arcade_my_player_pass_role");
      const role = Array.isArray(data) ? data[0] : data;
      if (error || role?.iscored_handle !== "DON" || role?.is_admin !== true) {\n        button.hidden = true;\n        status.textContent = "GitHub signed in. DON Player Pass activation and administrator approval are still required.";\n        return false;\n      }
      button.hidden = true;
      status.textContent = "🤖 DON — administrator session verified";
      if (typeof onVerified === "function") onVerified();
      return true;
    } catch (_) { return false; }
  }
  button.addEventListener("click", async () => {
    button.disabled = true;
    status.textContent = "Opening GitHub sign-in…";
    try {
      const { error } = await operatorSupabase.auth.signInWithOAuth({
        provider: "github",
        options: { redirectTo, scopes: "read:user" },
      });
      if (error) throw error;
    } catch (_) {
      status.textContent = "GitHub sign-in unavailable. Please try again.";
      button.disabled = false;
    }
  });
  void verify();
  return { verify, element: section };
}
