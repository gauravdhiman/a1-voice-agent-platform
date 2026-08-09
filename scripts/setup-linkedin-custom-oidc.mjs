#!/usr/bin/env node
/**
 * Register the Supabase custom OIDC provider used by direct LinkedIn sign-in.
 *
 * The app-owned LinkedIn popup exchanges an authorization code on the backend,
 * then calls `signInWithIdToken({ provider: "custom:linkedin", ... })`. GoTrue
 * only accepts custom OIDC providers with the `custom:` prefix for ID-token
 * grants — the built-in `[auth.external.linkedin_oidc]` block in config.toml
 * does not satisfy that path.
 *
 * Usage (from repo root, with local Supabase running):
 *   node scripts/setup-linkedin-custom-oidc.mjs
 *
 * Requires in the selected root environment file (normally `.env.local`):
 *   SUPABASE_URL
 *   SUPABASE_SERVICE_KEY
 *   SUPABASE_AUTH_EXTERNAL_LINKEDIN_OIDC_CLIENT_ID (or LINKEDIN_CLIENT_ID)
 *   SUPABASE_AUTH_EXTERNAL_LINKEDIN_OIDC_CLIENT_SECRET (or LINKEDIN_CLIENT_SECRET)
 */

import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { execSync } from "node:child_process";

const IDENTIFIER = "custom:linkedin";
const LINKEDIN_ISSUER = "https://www.linkedin.com/oauth";

function loadLocalSupabaseServiceKey() {
  try {
    const raw = execSync("supabase status -o json", {
      cwd: process.cwd(),
      encoding: "utf8",
      stdio: ["ignore", "pipe", "ignore"],
    });
    const status = JSON.parse(raw);
    return status.SERVICE_ROLE_KEY || status.SECRET_KEY || null;
  } catch {
    return null;
  }
}

function loadRootEnv() {
  const envPath = resolve(process.cwd(), ".env");
  try {
    const raw = readFileSync(envPath, "utf8");
    for (const line of raw.split("\n")) {
      const trimmed = line.trim();
      if (!trimmed || trimmed.startsWith("#")) continue;
      const eq = trimmed.indexOf("=");
      if (eq === -1) continue;
      const key = trimmed.slice(0, eq).trim();
      let value = trimmed.slice(eq + 1).trim();
      if (
        (value.startsWith('"') && value.endsWith('"')) ||
        (value.startsWith("'") && value.endsWith("'"))
      ) {
        value = value.slice(1, -1);
      }
      if (!(key in process.env)) {
        process.env[key] = value;
      }
    }
  } catch {
    // `.env` is optional when vars are already exported.
  }
}

function requireEnv(name, fallbacks = []) {
  for (const key of [name, ...fallbacks]) {
    const value = process.env[key];
    if (value) return value;
  }
  throw new Error(`Missing required environment variable: ${name}`);
}

function authHeaders(serviceKey) {
  return {
    Authorization: `Bearer ${serviceKey}`,
    apikey: serviceKey,
    "Content-Type": "application/json",
  };
}

async function requestJson(url, options) {
  const response = await fetch(url, options);
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message =
      body?.msg ||
      body?.message ||
      body?.error_description ||
      JSON.stringify(body);
    throw new Error(`${response.status} ${response.statusText}: ${message}`);
  }
  return body;
}

async function listProviders(authUrl, serviceKey) {
  const body = await requestJson(`${authUrl}/admin/custom-providers`, {
    headers: authHeaders(serviceKey),
  });
  return body.providers ?? [];
}

async function createProvider(authUrl, serviceKey, payload) {
  return requestJson(`${authUrl}/admin/custom-providers`, {
    method: "POST",
    headers: authHeaders(serviceKey),
    body: JSON.stringify(payload),
  });
}

async function updateProvider(authUrl, serviceKey, payload) {
  return requestJson(
    `${authUrl}/admin/custom-providers/${encodeURIComponent(IDENTIFIER)}`,
    {
      method: "PUT",
      headers: authHeaders(serviceKey),
      body: JSON.stringify(payload),
    },
  );
}

function resolveSupabaseUrl(rawUrl) {
  let url = rawUrl.replace(/\/$/, "");
  try {
    const parsed = new URL(url);
    if (parsed.hostname === "host.docker.internal") {
      parsed.hostname = "127.0.0.1";
      url = parsed.toString().replace(/\/$/, "");
    }
  } catch {
    // Keep the original value; requestJson will surface parse errors.
  }
  return url;
}

async function main() {
  loadRootEnv();

  const supabaseUrl = resolveSupabaseUrl(
    process.env.SUPABASE_LOCAL_URL || requireEnv("SUPABASE_URL"),
  );
  const serviceKey =
    loadLocalSupabaseServiceKey() || requireEnv("SUPABASE_SERVICE_KEY");
  const clientId = requireEnv("SUPABASE_AUTH_EXTERNAL_LINKEDIN_OIDC_CLIENT_ID", [
    "LINKEDIN_CLIENT_ID",
  ]);
  const clientSecret = requireEnv(
    "SUPABASE_AUTH_EXTERNAL_LINKEDIN_OIDC_CLIENT_SECRET",
    ["LINKEDIN_CLIENT_SECRET"],
  );

  const authUrl = `${supabaseUrl}/auth/v1`;
  const providerPayload = {
    provider_type: "oidc",
    identifier: "linkedin",
    name: "LinkedIn",
    client_id: clientId,
    client_secret: clientSecret,
    issuer: LINKEDIN_ISSUER,
    scopes: ["openid", "profile", "email"],
    skip_nonce_check: true,
  };

  const existing = await listProviders(authUrl, serviceKey);
  const alreadyRegistered = existing.some(
    (provider) => provider.identifier === IDENTIFIER,
  );

  if (alreadyRegistered) {
    await updateProvider(authUrl, serviceKey, {
      name: providerPayload.name,
      client_id: clientId,
      client_secret: clientSecret,
      issuer: LINKEDIN_ISSUER,
      scopes: providerPayload.scopes,
      skip_nonce_check: true,
    });
    console.log(`Updated Supabase custom OIDC provider ${IDENTIFIER}.`);
    return;
  }

  await createProvider(authUrl, serviceKey, providerPayload);
  console.log(`Created Supabase custom OIDC provider ${IDENTIFIER}.`);
}

main().catch((error) => {
  console.error("Failed to configure LinkedIn custom OIDC provider:");
  console.error(error instanceof Error ? error.message : error);
  process.exit(1);
});
