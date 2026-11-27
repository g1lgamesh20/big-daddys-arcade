// Player Pass operator issuance — DRAFT ONLY; not deployed.
// Operator must have a verified Supabase Auth account whose immutable user ID
// matches PLAYER_PASS_OPERATOR_USER_ID configured server-side.
import { createClient } from "npm:@supabase/supabase-js@2";

const ORIGIN = "https://g1lgamesh20.github.io";
const cors = {
  "Access-Control-Allow-Origin": ORIGIN,
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Access-Control-Allow-Headers": "authorization, apikey, content-type, x-client-info",
  "Cache-Control": "no-store",
  Vary: "Origin",
};
const reply = (status: number, value: Record<string, unknown>) =>
  new Response(JSON.stringify(value), {
    status, headers: { ...cors, "Content-Type": "application/json" },
  });
const PREFIXES = ["PACMAN", "GALAGA", "FROGGER", "DIGDUG", "QBERT", "CENTIPEDE", "ASTEROIDS", "TEMPEST"];
const ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"; // omit ambiguous 0/O, 1/I
const enc = new TextEncoder();
function randomSuffix(): string {
  // Rejection sampling avoids modulo bias for the 32-symbol alphabet.
  const bytes = crypto.getRandomValues(new Uint8Array(4));
  return Array.from(bytes, n => ALPHABET[n & 31]).join("");
}
async function digest(pepper: string, code: string): Promise<string> {
  const key = await crypto.subtle.importKey("raw", enc.encode(pepper),
    { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const bytes = new Uint8Array(await crypto.subtle.sign("HMAC", key, enc.encode(code)));
  return Array.from(bytes, b => b.toString(16).padStart(2, "0")).join("");
}
Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") return new Response(null, { status: 204, headers: cors });
  if (req.method !== "POST") return reply(405, { error: "Method not allowed" });
  if (req.headers.get("origin") !== ORIGIN) return reply(403, { error: "Forbidden" });
  const url = Deno.env.get("SUPABASE_URL");
  const anonKey = Deno.env.get("SUPABASE_ANON_KEY");
  const serviceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
  const pepper = Deno.env.get("PLAYER_PASS_PEPPER");
  const operatorId = Deno.env.get("PLAYER_PASS_OPERATOR_USER_ID");
  if (!url || !anonKey || !serviceKey || !pepper || pepper.length < 32 || !operatorId) {
    return reply(503, { error: "Operator service not configured" });
  }
  const bearer = req.headers.get("authorization") || "";
  if (!/^Bearer\s+\S+$/i.test(bearer)) return reply(401, { error: "Sign in required" });
  const auth = createClient(url, anonKey, { auth: { persistSession: false, autoRefreshToken: false } });
  const { data, error } = await auth.auth.getUser(bearer.replace(/^Bearer\s+/i, ""));
  if (error || !data.user || data.user.id !== operatorId || data.user.is_anonymous === true) {
    return reply(403, { error: "Operator access required" });
  }
  if (!(req.headers.get("content-type") || "").toLowerCase().startsWith("application/json")) {
    return reply(415, { error: "JSON required" });
  }
  let body: Record<string, unknown>;
  try {
    const raw = await req.text();
    if (raw.length > 512) return reply(413, { error: "Request too large" });
    body = JSON.parse(raw);
    if (!body || typeof body !== "object" || Array.isArray(body)) throw Error("invalid");
  } catch { return reply(400, { error: "Invalid request" }); }
  const initials = typeof body.initials === "string" ? body.initials.trim().toUpperCase() : "";
  if (!/^[A-Z0-9 ]{1,24}$/.test(initials)) return reply(400, { error: "Invalid player initials" });
  const prefix = typeof body.prefix === "string" ? body.prefix.toUpperCase() : "PACMAN";
  if (!PREFIXES.includes(prefix)) return reply(400, { error: "Invalid arcade prefix" });
  const db = createClient(url, serviceKey, { auth: { persistSession: false, autoRefreshToken: false } });
  // Require a live, non-revoked DON Player Pass binding and server-assigned admin role.
  // A matching operator UUID by itself is insufficient after a device is revoked.
  const { data: authorized, error: roleError } = await db.rpc("arcade_operator_is_active_admin", { p_auth_user_id: data.user.id });
  if (roleError || authorized !== true) return reply(403, { error: "Operator Player Pass required" });
  // Player existence and issuance are checked atomically by a service-only RPC.
  // Do not expose arcade_private in the Supabase Data API.
  // Four characters provide only 32^4 possibilities per prefix. Require a
  // separate global anti-automation gate before production activation.
  for (let i = 0; i < 5; i++) {
    const code = prefix + "-" + randomSuffix();
    const codeDigest = await digest(pepper, code);
    const expiresAt = new Date(Date.now() + 7 * 86400_000).toISOString();
    const { data: issued, error: insertError } = await db.rpc("arcade_issue_player_pass", {
      p_handle: initials, p_digest: codeDigest, p_expires_at: expiresAt, p_operator_id: operatorId,
    });
    if (!insertError && issued === true) {
      return reply(200, { code, initials, expires_at: expiresAt });
    }
    if (!insertError && issued === false) return reply(404, { error: "Player not registered in verified directory" });
    if (insertError?.code !== "23505") {
      console.error("Player Pass issuance failed", insertError?.code || "unknown");
      return reply(503, { error: "Unable to issue Player Pass" });
    }
  }
  return reply(503, { error: "Unable to generate unique code; retry" });
});
