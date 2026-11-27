// Player Pass redemption Edge Function — development branch, NOT DEPLOYED.
// Requires review-only migrations and Supabase Anonymous Sign-Ins enabled.
// Required secret: PLAYER_PASS_PEPPER (long random value, never in frontend).
import { createClient } from "npm:@supabase/supabase-js@2";

const ORIGIN = "https://g1lgamesh20.github.io";
const headers = {
  "Access-Control-Allow-Origin": ORIGIN,
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Access-Control-Allow-Headers": "authorization, apikey, content-type, x-client-info",
  "Vary": "Origin",
  "Cache-Control": "no-store",
};
function respond(status: number, body: Record<string, unknown>) {
  return new Response(JSON.stringify(body), {
    status, headers: { ...headers, "Content-Type": "application/json" },
  });
}
function bytesHex(bytes: Uint8Array): string {
  return Array.from(bytes, b => b.toString(16).padStart(2, "0")).join("");
}
async function hmacHex(key: string, message: string): Promise<string> {
  const encoder = new TextEncoder();
  const cryptoKey = await crypto.subtle.importKey(
    "raw", encoder.encode(key), { name: "HMAC", hash: "SHA-256" }, false, ["sign"],
  );
  return bytesHex(new Uint8Array(await crypto.subtle.sign("HMAC", cryptoKey, encoder.encode(message))));
}
Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") return new Response(null, { status: 204, headers });
  if (req.method !== "POST") return respond(405, { error: "Method not allowed" });
  if (req.headers.get("origin") !== ORIGIN) return respond(403, { error: "Origin not allowed" });
  if (!(req.headers.get("content-type") || "").toLowerCase().startsWith("application/json")) {
    return respond(415, { error: "JSON required" });
  }

  const url = Deno.env.get("SUPABASE_URL");
  const serviceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
  const publicKey = Deno.env.get("SUPABASE_ANON_KEY");
  const pepper = Deno.env.get("PLAYER_PASS_PEPPER");
  const turnstileSecret = Deno.env.get("TURNSTILE_SECRET_KEY");
  if (!url || !serviceKey || !publicKey || !pepper || pepper.length < 32 || !turnstileSecret) {
    return respond(503, { error: "Player Pass not configured" });
  }

  // Auth token is checked by Supabase Auth; no user_id from request body is trusted.
  const bearer = req.headers.get("authorization") || "";
  if (!/^Bearer\s+\S+$/i.test(bearer)) return respond(401, { error: "Sign in required" });
  const token = bearer.replace(/^Bearer\s+/i, "");
  const auth = createClient(url, publicKey, { auth: { persistSession: false, autoRefreshToken: false } });
  const { data: authData, error: authError } = await auth.auth.getUser(token);
  if (authError || !authData.user) return respond(401, { error: "Sign in required" });

  let body: { initials?: unknown; code?: unknown; turnstile_token?: unknown };
  try {
    const raw = await req.text();
    if (raw.length > 512) return respond(413, { error: "Request too large" });
    body = JSON.parse(raw);
    if (!body || typeof body !== "object" || Array.isArray(body)) throw new Error("Invalid");
  } catch {
    return respond(400, { error: "Invalid request" });
  }

  const initials = typeof body.initials === "string" ? body.initials.trim().toUpperCase() : "";
  const code = typeof body.code === "string" ? body.code.trim().toUpperCase() : "";
  if (!/^[A-Z0-9 ]{1,24}$/.test(initials) || !/^[A-Z]{3,12}-[A-Z0-9]{4}$/.test(code)) {
    return respond(400, { error: "Invalid request" });
  }

  // Four-character codes require a human-verification gate on EVERY attempt.
  // Turnstile verification is performed server-side; never trust a client flag.
  const challenge = typeof body.turnstile_token === "string" ? body.turnstile_token : "";
  if (!challenge || challenge.length > 2048) return respond(403, { error: "Human verification required" });
  try {
    const verify = await fetch("https://challenges.cloudflare.com/turnstile/v0/siteverify", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({ secret: turnstileSecret, response: challenge }),
      signal: AbortSignal.timeout(8000),
    });
    if (!verify.ok) return respond(503, { error: "Verification unavailable" });
    const result = await verify.json();
    if (result.success !== true || result.hostname !== "g1lgamesh20.github.io") {
      return respond(403, { error: "Human verification failed" });
    }
  } catch { return respond(503, { error: "Verification unavailable" }); }

  // The database RPC performs atomic attempt accounting and code redemption.
  // Never rely on an in-memory rate limiter (each edge instance has its own memory).
  const db = createClient(url, serviceKey, { auth: { persistSession: false, autoRefreshToken: false } });
  const digest = await hmacHex(pepper, code);
  // HMAC the IP as well: store only an opaque per-installation hash in the rate-limit table.
  // IP is defense in depth; user-ID limits remain authoritative.
  const forwardedIp = req.headers.get("cf-connecting-ip") || "";
  const ipDigest = await hmacHex(pepper, forwardedIp || "unknown");
  const { data, error } = await db.rpc("arcade_redeem_player_pass_limited", {
    p_auth_user_id: authData.user.id,
    p_iscored_handle: initials,
    p_code_digest: digest,
    p_ip_digest: ipDigest,
  });
  if (error) {
    // Do not expose SQL errors or disclose whether player/code exists.
    console.error("Player Pass redemption rejected", error.code || "unknown");
    return respond(429, { error: "Unable to activate. Ask Big Daddy for a fresh code or try later." });
  }
  const record = Array.isArray(data) ? data[0] : data;
  if (!record?.player_id) return respond(429, { error: "Unable to activate. Ask Big Daddy for a fresh code or try later." });
  return respond(200, { activated: true, initials: record.iscored_handle });
});
