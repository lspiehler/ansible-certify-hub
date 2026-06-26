# Certify Management Hub API — reference notes

Captured from a Certify Management Hub's **live OpenAPI spec** (v1) on 2026-06-26.
This is the authoritative source for the data the inventory plugin consumes, so a
new session does not have to re-fetch and re-read the (large) spec.

## Where the spec lives

- **Swagger/Scalar UI:** `https://ctw.example.org/api/docs/`
- **Raw OpenAPI JSON:** `https://ctw.example.org/openapi/v1.json` (~280 KB, OpenAPI 3.0.4)
- Re-fetch: `curl -sk https://ctw.example.org/openapi/v1.json -o ctw_openapi.json`
- The declared server in the spec is `http://ctw.example.org/` (note: **http** in
  the doc, but use **https** in practice).

## The endpoint the plugin uses

```
GET /internal/v1/hub/instances        # operationId GetHubManagedInstances, tag "Hub"
  -> 200: application/json: array of ManagedInstanceInfo   (a bare JSON array, no pagination wrapper)
```

Related Hub endpoints (not used by the inventory, listed for context):

```
GET  /internal/v1/hub/instances/{id}                          GetHubManagedInstance
PUT  /internal/v1/hub/instances/{id}                          UpdateHubManagedInstance
POST /internal/v1/hub/instances/{instanceId}/dashboard/register
POST /internal/v1/hub/instances/{instanceId}/dashboard/remove
POST /internal/v1/hub/instances/{instanceId}/rejoin
POST /internal/v1/hub/instances/rejoin
POST /api/v1/auth/login        # username/password -> JWT + refresh token (interactive; NOT needed for API-token auth)
```

## Authentication

`components.securitySchemes` (machine-readable, authoritative):

| Scheme | Type | Detail |
| --- | --- | --- |
| `Bearer` | http / bearer / JWT | `Authorization: Bearer <token>` |
| `ApiKeyClientId` | apiKey, in header | header name **`X-Client-ID`** |
| `ApiKeyClientSecret` | apiKey, in header | header name **`X-Client-Secret`** |

Global `security` = `Bearer` **OR** (`ApiKeyClientId` + `ApiKeyClientSecret`).
API tokens are created in the Hub UI under **Settings → Security → API Access** and
sent **directly as headers on each request** (no token-exchange step).

> ✅ **Header spelling — RESOLVED (2026-06-26, live test).** The hyphenated
> **`X-Client-ID`** / **`X-Client-Secret`** spelling from `securitySchemes` is
> correct; the plugin already sends it and it works against the live Hub. (The
> `X-ClientID` no-hyphen prose elsewhere in the spec is just a typo.) Proof: those
> headers returned **400** "X-Certify-HubAssignedId header is required" on
> `/internal/v1/hub/subscription/available` — i.e. auth *passed* — while a wrong
> secret returned 401. No code change was needed.
>
> ⚠️ **Credential scope matters.** A managed-instance service principal (the
> credentials an agent uses to join the Hub) authenticates but is **not**
> authorized for the Hub-admin `instances` listing — it returns **401**. The
> inventory needs a token whose security principal holds the **Hub Viewer** role
> (create an Application-type user with that role, then an API token for it under
> Settings → Security). See the README "Creating a read-only API token".

> Note: the `security` array on the `instances` operation itself is `[ {}, {} ]`
> (two empty requirement objects, an artifact of the .NET generator). Treat the
> **global** security as the truth — the endpoint expects auth.

## Schemas

### `ManagedInstanceInfo` (one Ansible host per object)

| Field | Type | Notes / inventory use |
| --- | --- | --- |
| `instanceId` | string | stable id |
| `internalInstanceId` | string | |
| `securityPrincipalId` | string | |
| `customTitle` | string, nullable | user-set friendly name |
| `displayTitle` | string, nullable | **default hostname source** (likely the machine name) |
| `os` | string | e.g. `Windows`, `Linux`, `macOS` → grouping / connection type |
| `osVersion` | string | |
| `clientName` | string | e.g. `Certify Certificate Manager` |
| `clientVersion` | string | |
| `tags` | array of `TagSummary` | → grouping; plugin derives `tags_by_category` + `tag_pairs` |
| `dateLastReported` | string (date-time) | |
| `dateRegistered` | string (date-time) | |
| `connectionStatus` | string | **lower case** live, e.g. `connected` → good `filters`/`keyed_groups` target (compare with `\| lower`) |
| `isAuthenticated` | boolean | |
| `isPendingConnection` | boolean | |
| `isDashboardEnabled` | boolean | |
| `requestAuthSecretHash` | string | |
| `license` | `LicenseCheckResult` | object |
| `summary` | `StatusSummary` or null | cert counts (see below) |
| `id` | string | (mirrors instanceId in practice) |
| `title` | string | |
| `description` | string | |
| `itemType` | string | |

> **There is no IP / FQDN / address field.** Agents dial out to the Hub, so the
> Hub stores no routable address. That is why the plugin derives `ansible_host`
> from `displayTitle` via `hostnames`/`compose` (optionally appending a domain
> suffix).
>
> ✅ **`displayTitle` content — RESOLVED (2026-06-26, live test).** It holds the
> instance's **short machine name** (e.g. `LCE2ADFS01`, `SMTP-RELAY-01`,
> `umc-docker03`), **not** an FQDN — so append a domain suffix to make
> `ansible_host` resolvable. The Hub's own managed instance reported a container
> id (`94bc0ec3f54c`) instead of a hostname. `os` is title-case (`Windows` /
> `Linux`); `tags` was empty in the test deployment.

### `TagSummary`

`categoryKey` (string), `categoryDisplayName` (string), `value` (string),
`colorHint` (string, nullable), `instanceId` (string, nullable),
`displayText` (string, nullable).

The plugin transforms `tags` into:
- `tags_by_category`: `{ categoryKey: [value, ...] }`
- `tag_pairs`: `[ "categoryKey:value", ... ]`

The raw array is exposed as the host var **`certify_tags`** (not `tags`, which is
a reserved Ansible variable name and triggers a warning if set on a host).

### `StatusSummary` (the `summary` field)

`instanceId`, `total`, `healthy`, `error`, `warning`, `awaitingUser`,
`invalidConfig`, `noCertificate`, `externallyManaged`, `totalDomains`,
`lastUpdateId`, `isChanged`. (Counts are int32, except `lastUpdateId` int64.)
