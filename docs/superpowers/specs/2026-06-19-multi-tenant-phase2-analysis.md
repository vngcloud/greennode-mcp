# Multi-tenant (per-user) auth for greennode-mcp — analysis & Phase 2 notes

Date: 2026-06-19
Status: **Findings + design options** (Phase 1 single-tenant done; Phase 2 not started)

> Consolidated from an empirical investigation: greennode-mcp deployed behind the
> VNG MCP Gateway (Agent Runtime, account `60108`, gateway `gw-vks-mcp-server-60108`,
> route `/vks_mcp_server`), measured with the `--auth-debug` diagnostic. Secrets are
> redacted here — never commit real keys/tokens.

## TL;DR

The current deployment is a sound **governed single-tenant** design (Gateway does
per-user authentication + per-tool authorization; greennode is a thin resource
server). It is **not** per-user *data* isolation: every user's tool calls execute
against one shared VKS service account (`GRN_CLIENT_ID`), so everyone sees the same
clusters. Making "each user sees their own clusters" is **Phase 2** and requires a
trustworthy per-user identity reaching greennode — which the current **API Key**
outbound mode does **not** provide.

There is also a **critical config gap** to fix immediately (see §4.1).

---

## 1. Current architecture (as deployed)

```
end-user (iam-user JWT) ──▶ MCP Gateway (Kong) ──▶ Agent Runtime ingress ──▶ greennode ──▶ VKS API
                            • inbound: iam-user      • outbound: api-key        • GRN_CLIENT_ID
                            • policy group (per-tool)   (static shared secret)     (global SA)
```

**Agent Runtime env for greennode (`vks-mcp-server`):**

```jsonc
{
  "GRN_CLIENT_ID":      "<vks service account client id>",   // VKS creds (global)
  "GRN_CLIENT_SECRET":  "<secret>",
  "GRN_DEFAULT_REGION": "HCM-3",
  "GRN_MCP_AUTH_DEBUG": "1",                                  // diagnostic — turn OFF in prod
  "GRN_MCP_API_KEY":    "<static api key, same value as gateway outbound>",
  "GRN_MCP_AUTH_MODE":  "api-key"                             // ⚠️ REQUIRED — currently MISSING
}
```

**Gateway config:**
- **Inbound** = `iam-user` — caller must present a VNG IAM user token; Gateway
  authenticates it and extracts the principal.
- **Outbound** = `api-key` — Gateway authenticates to greennode with a static
  shared key (`Authorization: Bearer vn-...`).
- **Policy Group** — authorizes which tools each inbound iam-user may call.

Routing note: the Gateway routes by **MCP-server name as path** (`/vks_mcp_server`),
and rewrites all subpaths to upstream `/mcp`. MCP is JSON-RPC over the single
`/mcp` streamable-http endpoint (requires `Accept: application/json, text/event-stream`).
`/whoami` and other upstream paths are **not** reachable through the Gateway.

---

## 2. What was measured (empirical contract)

Using `--auth-debug` (logs one `AUTH-DEBUG {json}` line per request; never logs the
full token), driving real calls through the Gateway:

- **Full chain works end-to-end**: `initialize` → `notifications/initialized` →
  `tools/call cluster_list` returned real clusters (region HCM-3) — i.e. greennode
  successfully calls VKS with the global `GRN_CLIENT_ID`.
- **Outbound token** greennode receives: `Authorization: Bearer <opaque ~96-char
  token, prefix "vn-...">` — **NOT a JWT** (can't decode claims; would need
  introspection). It is the **static API key** (same for every user/request) →
  **carries no identity**.
- **Forwarding headers**: the Gateway forwards arbitrary `x-*` headers **verbatim**,
  including `x-greennode-agentbase-user-id`, `x-grn-*`, `x-forwarded-*`.
- **⚠️ The Gateway does NOT sanitize identity headers**: a client calling the
  Gateway set `x-greennode-agentbase-user-id: probe-user-123` and it reached
  greennode unchanged. So that header is **client-spoofable**.
- Inbound iam-user tokens are RS256 JWTs from Keycloak realm `iam`
  (`iss=https://signin.vngcloud.vn/auth/realms/iam`), with `sub`, `azp/client_id`,
  `authUserType=user-sa`, **empty `scope`, no `aud`**. (VNG IAM = Keycloak; its
  `/certs` + `/.well-known` are nginx-blocked externally — relevant if greennode
  ever needs JWKS to verify inbound JWTs.)

---

## 3. Key distinction: tool authorization vs data isolation

| Concern | Handled by | Per-user today? |
|---|---|---|
| **Which tools** a user may call | Gateway Policy Group | ✅ yes |
| **Whose data/resources** a tool returns | greennode → VKS via `GRN_CLIENT_ID` | ❌ no (shared SA) |

The Policy Group makes *tool access* per-user, but every call still executes against
the same VKS account, so **data is shared**. "Each user sees their own clusters" is
a different problem (Phase 2).

---

## 4. Security findings

### 4.1 CRITICAL — api-key not enforced unless `GRN_MCP_AUTH_MODE=api-key`
Setting `GRN_MCP_API_KEY` alone is **not enough**. In `_resolve_auth`, mode
defaults to `none` and `BearerTokenMiddleware` is only attached when mode ==
`api-key`. With mode `none`, the endpoint is **open** and the key is ignored.

The Agent Runtime endpoint is **publicly reachable** — a direct call (bypassing the
Gateway, no key) was able to run `cluster_list`. That **bypasses the Gateway and the
Policy Group entirely**. **Fix:** set `GRN_MCP_AUTH_MODE=api-key`; then direct calls
without the key get 401, and only the Gateway can reach greennode.

(Improvement idea: make greennode warn/error if `GRN_MCP_API_KEY` is set while mode
is `none`, to prevent this footgun.)

### 4.2 `x-greennode-agentbase-user-id` is spoofable
The Gateway forwards client-supplied identity headers unchanged. Even with the
api-key channel locked, **any caller that passes the Gateway's inbound auth can set
`x-greennode-agentbase-user-id` to any value**. Therefore greennode **must not trust
that header for identity** unless the Gateway is configured to overwrite it from the
verified principal (currently it does not).

### 4.3 Secret hygiene
`GRN_CLIENT_SECRET` and `GRN_MCP_API_KEY` live in runtime env (AgentBase docs say
env is for non-sensitive values). Keep them out of git; rotate the api-key if ever
exposed; use a secret store if available.

### Immediate hardening checklist (single-tenant prod)
- [ ] Add `GRN_MCP_AUTH_MODE=api-key` and redeploy.
- [ ] Verify: direct call to runtime endpoint without key → **401**; call through
      Gateway → **200**.
- [ ] Set `GRN_MCP_AUTH_DEBUG=0` (or remove) in production.
- [ ] Rotate `GRN_MCP_API_KEY` (and update Gateway outbound) if it was exposed.

---

## 5. Phase 2 — per-user data isolation

Goal: a tool call runs against the **calling user's** VKS access, not a global SA.
Two sub-problems, solved independently:

### (A) Trustworthy per-user identity at greennode
With outbound = **API Key**, there is **no trustworthy identity** (key = identity-less;
header = spoofable). Options:

- **B1 — Switch outbound to 3LO.** Gateway sends a **user-bound token**; greennode
  validates/introspects it to get the user `sub`. Most secure. Costs: needs a
  confidential **Keycloak OIDC client** in realm `iam` (an IAM/SSO-team action; see
  security notes below), the user must consent/login, and the earlier "identity
  service unavailable" outbound-resolution error must be resolved. The token is
  opaque (`vn-...`) → greennode validates via **introspection/userinfo**, not JWT
  verify.
- **B2 — Header + Gateway sanitization.** Keep api-key for the channel, and trust
  `x-greennode-agentbase-user-id` **only if** the Gateway is confirmed to overwrite
  that header from the authenticated inbound principal (so clients can't spoof it).
  Requires an AgentBase capability/guarantee we have **not** confirmed (today it does
  not sanitize). Cheaper if available.

### (B) Per-user VKS credential (the hard part — independent of A)
Even with a verified user identity, greennode still needs a credential that calls
**VKS as that user**. The inbound/3LO IAM token has `aud` ≠ VKS and is not a VKS key
(forwarding it would be the token-passthrough anti-pattern + wrong audience). So
greennode must **map user → VKS credential**, e.g.:
- a per-user / delegated VKS API key minted via VNG IAM (if such a delegation API
  exists — needs confirmation), or
- a mapping table (user → their VKS service account creds), or
- an on-behalf-of/token-exchange flow if VNG IAM supports it.

`GRN_CLIENT_ID` can remain as a default/fallback (service-to-service), with per-user
credentials layered on top.

### Keycloak client (for B1) — security notes
A confidential OIDC client in the shared `iam` realm is a normal but
higher-blast-radius action. If created: dedicated client, least-privilege, Standard
flow + PKCE only (Implicit/Direct-access/Service-accounts off), **exact** HTTPS
redirect URIs = the Gateway callback only, secret in Vault, rotation plan. Have the
IAM/Security team own it.

---

## 6. Open questions for the AgentBase / IAM team

1. Does the MCP Gateway **overwrite/strip** client-supplied
   `x-greennode-agentbase-user-id` and set it from the verified inbound principal?
   (Decides whether B2 is viable.)
2. For **3LO** outbound: what does greennode receive — a JWT or opaque token? Is
   there an **introspection/userinfo** endpoint to resolve the user `sub`/email?
   What `aud` does it carry?
3. Is there a **delegated / per-user VKS API key** mechanism (mint a VKS-usable
   credential for a given end-user)? This is the crux of sub-problem (B).
4. VNG IAM (Keycloak realm `iam`): is there an externally reachable **JWKS /
   discovery** (its `/certs` + `/.well-known` are blocked) — needed if greennode
   ever verifies inbound JWTs directly (`--auth-mode jwt`).

---

## 7. Recommended path

1. **Now:** ship the hardened **single-tenant** setup (§4 checklist). Secure and
   sufficient if per-user data isolation isn't yet required.
2. **Phase 2:** answer §6 Q1–Q3 first.
   - If Gateway can sanitize the header (Q1 = yes) → **B2** (cheapest): api-key
     channel + trusted header + per-user VKS credential (B).
   - Else → **B1**: 3LO outbound + token introspection + per-user VKS credential (B).
   - Sub-problem (B) (per-user VKS credential) is required either way and is the
     real work — driven by Q3.

---

## 8. How to re-measure

greennode has the opt-in `--auth-debug` diagnostic (`GRN_MCP_AUTH_DEBUG=1`, HTTP
only, default off): prints one greppable `AUTH-DEBUG {json}` line per request to
stdout (redacted — 6-char token prefix only, never the full token; claims via
allow-list) and exposes `/whoami` (not reachable through the Gateway). Read the
contract from runtime logs:

```
... | grep AUTH-DEBUG | grep '"path": "/mcp"'
```

Local repro: `src/vks-mcp-server/scripts/auth-debug-local.sh`. Turn the flag OFF in
production once measuring is done.

## References
- Phase 1 (JWT Resource Server) design: `2026-06-19-jwt-resource-server-design.md`
- auth-debug diagnostic design: `2026-06-19-auth-debug-diagnostic-design.md`
- `context/auth-mcp.md` (MCP security best practices — token passthrough anti-pattern),
  `context/author.md` (OAuth 2.1), `context/agent-base/` (Gateway, Runtime, access-control).
