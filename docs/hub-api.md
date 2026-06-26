# Certify Management Hub API — reference notes

Captured from the **live OpenAPI spec** of the LCMC deployment on 2026-06-26.
This is the authoritative source for the data the inventory plugin consumes, so a
new session does not have to re-fetch and re-read the (large) spec.

## Where the spec lives

- **Swagger/Scalar UI:** `https://ctw.lcmchealth.org/api/docs/`
- **Raw OpenAPI JSON:** `https://ctw.lcmchealth.org/openapi/v1.json` (~280 KB, OpenAPI 3.0.4)
- Re-fetch: `curl -sk https://ctw.lcmchealth.org/openapi/v1.json -o ctw_openapi.json`
  (the deployment was reachable from the internal network; the public internet was
  firewalled on the Windows authoring box — gnu.org/etc. timed out).
- The declared server in the spec is `http://ctw.lcmchealth.org/` (note: **http** in
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

> ⚠️ **Header-name discrepancy to verify against the live API.** The
> `securitySchemes` block says **`X-Client-ID`** (with a hyphen). However, a prose
> summary elsewhere in the same spec (the certificate-download endpoint, line
> ~3437) writes it as **`X-ClientID`** (no hyphen): *"use an API token (using
> X-ClientID and X-Client-Secret HTTP headers)."* The plugin currently sends the
> machine-readable spelling `X-Client-ID`. **If a live call returns 401/403 with a
> valid token, switch to `X-ClientID` (or send both spellings).** This is the #1
> thing to confirm with real credentials.

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
| `connectionStatus` | string | e.g. `Connected` → good `filters`/`keyed_groups` target |
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
> suffix). Confirm what `displayTitle` actually contains in this deployment.

### `TagSummary`

`categoryKey` (string), `categoryDisplayName` (string), `value` (string),
`colorHint` (string, nullable), `instanceId` (string, nullable),
`displayText` (string, nullable).

The plugin transforms `tags` into:
- `tags_by_category`: `{ categoryKey: [value, ...] }`
- `tag_pairs`: `[ "categoryKey:value", ... ]`

### `StatusSummary` (the `summary` field)

`instanceId`, `total`, `healthy`, `error`, `warning`, `awaitingUser`,
`invalidConfig`, `noCertificate`, `externallyManaged`, `totalDomains`,
`lastUpdateId`, `isChanged`. (Counts are int32, except `lastUpdateId` int64.)
