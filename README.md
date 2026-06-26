# Ansible Collection: `lspiehler.certify_hub`

A **dynamic inventory** plugin for [Certify The Web](https://certifytheweb.com/)
(Webprofusion) **[Management Hub](https://docs.certifytheweb.com/docs/hub/)**.
It turns the instances managed by your Hub into Ansible hosts by calling the
Hub's `GET /internal/v1/hub/instances` API, so you can target the same machines
you manage certificates for — without maintaining a separate static inventory.

> **Not affiliated with Webprofusion / Certify The Web.** This is a third-party,
> community-maintained collection. "Certify The Web" and "Certify Management
> Hub" are products of Webprofusion.

- **Plugin:** `lspiehler.certify_hub.instances`
- **Type:** inventory
- **Inventory source filename must end with:** `certify_hub.yml`, `certify_hub.yaml`, `ctw.yml`, or `ctw.yaml`

---

## Features

- Lists every managed instance from a Certify Management Hub as an Ansible host.
- API-token (`X-Client-ID` / `X-Client-Secret`) **or** Bearer-JWT authentication.
- Full [constructed](https://docs.ansible.com/ansible/latest/collections/ansible/builtin/constructed_inventory.html)
  interface: `hostnames`, `compose`, `keyed_groups`, `groups`, `strict`.
- Jinja2 `filters` to include only the instances you care about (e.g. connected).
- First-class grouping on **Certify tags** via the derived `tags_by_category`.
- Optional response **caching** (`inventory_cache`).
- Configurable TLS verification (`validate_certs` / `ca_path`) for internal CAs.

---

## Requirements

- `ansible-core` >= 2.15 (control node: Linux / macOS / WSL — Ansible does not run
  as a controller on native Windows).
- Network reachability from the control node to your Hub's HTTPS endpoint.
- A Hub API token (client ID + secret) with permission to read instances, created
  under **Settings → Security → API Access** in the Hub UI.

No third-party Python packages are required; the plugin uses only `ansible-core`
and the standard library.

---

## Installation

Until this is published to Ansible Galaxy, install straight from git:

```bash
ansible-galaxy collection install git+https://github.com/lspiehler/ansible-certify-hub.git
```

Or build and install locally from a clone:

```bash
ansible-galaxy collection build .
ansible-galaxy collection install lspiehler-certify_hub-*.tar.gz
```

You can also use it in-place by pointing `ANSIBLE_COLLECTIONS_PATH` at a directory
laid out as `ansible_collections/lspiehler/certify_hub/`.

---

## Quick start

1. Create the inventory source `certify_hub.yml`:

   ```yaml
   plugin: lspiehler.certify_hub.instances
   url: https://ctw.example.org
   ```

2. Provide credentials via environment variables:

   ```bash
   export CERTIFY_HUB_CLIENT_ID='your-client-id'
   export CERTIFY_HUB_CLIENT_SECRET='your-client-secret'
   ```

3. List the inventory:

   ```bash
   ansible-inventory -i certify_hub.yml --list
   ansible-inventory -i certify_hub.yml --graph
   ```

---

## Authentication

The Hub accepts either of two schemes; configure **one**:

| Scheme | Options | Headers sent |
| --- | --- | --- |
| API token *(recommended)* | `client_id` + `client_secret` | `X-Client-ID`, `X-Client-Secret` |
| Bearer JWT | `token` | `Authorization: Bearer <token>` |

Each option has a matching environment variable so secrets stay out of the
inventory file:

| Option | Environment variable |
| --- | --- |
| `url` | `CERTIFY_HUB_URL` |
| `client_id` | `CERTIFY_HUB_CLIENT_ID` |
| `client_secret` | `CERTIFY_HUB_CLIENT_SECRET` |
| `token` | `CERTIFY_HUB_TOKEN` |

> Keep credentials out of source control. Prefer environment variables, Ansible
> Vault, or a templated `lookup('ansible.builtin.env', ...)` in the inventory file.

---

## Configuration reference

### Plugin options

| Option | Type | Default | Description |
| --- | --- | --- | --- |
| `plugin` | str | — | Must be `lspiehler.certify_hub.instances`. |
| `url` | str | — | Hub base URL, e.g. `https://ctw.example.org`. |
| `client_id` | str | — | API token client ID (`X-Client-ID`). |
| `client_secret` | str | — | API token client secret (`X-Client-Secret`). |
| `token` | str | — | Bearer JWT (alternative to the API token pair). |
| `validate_certs` | bool | `true` | Verify the Hub's TLS certificate. |
| `ca_path` | path | — | PEM CA bundle for an internal/private CA. |
| `timeout` | int | `30` | HTTP timeout in seconds. |
| `hostnames` | list[str] | `[displayTitle, customTitle, title, instanceId, id]` | Ordered Jinja2 expressions; the first non-empty result becomes the inventory hostname. |
| `filters` | list[str] | `[]` | Jinja2 boolean expressions; a host is kept only if **all** are true. |

Inherited from the `constructed` fragment: `compose`, `groups`, `keyed_groups`,
`strict`, `use_extra_vars`, `leading_separator`.
Inherited from the `inventory_cache` fragment: `cache`, `cache_plugin`,
`cache_timeout`, `cache_connection`, `cache_prefix`.

### Host variables

Every field returned by the Hub API is set verbatim on the host, plus two
convenience variables. The most useful:

| Variable | Example | Notes |
| --- | --- | --- |
| `instanceId` / `id` | `e1b2...` | Stable instance identifier. |
| `displayTitle` / `customTitle` / `title` | `WEB01` | Friendly/host name. |
| `os` / `osVersion` | `Windows` / `10.0.20348` | Useful for grouping + connection type. |
| `clientName` / `clientVersion` | `Certify Certificate Manager` / `6.0.0` | Agent identity. |
| `connectionStatus` | `Connected` | `Connected` / `Disconnected` / ... |
| `isAuthenticated`, `isPendingConnection`, `isDashboardEnabled` | `true` | Booleans. |
| `dateLastReported`, `dateRegistered` | ISO-8601 | Timestamps. |
| `tags` | `[{categoryKey, value, ...}]` | Raw tag objects from the API. |
| `tags_by_category` *(derived)* | `{environment: [production]}` | `categoryKey` → list of values. |
| `tag_pairs` *(derived)* | `[environment:production]` | Flat `key:value` strings. |
| `ansible_host` | `WEB01` | Defaults to the inventory hostname; override via `compose` or `hostnames`. |

---

## Host addressing (the important part)

The Hub does **not** store a network address for an instance — agents dial *out*
to the Hub, so the API only exposes the instance's title and OS. You therefore
decide how Ansible reaches each host. Two interchangeable mechanisms:

**1. `hostnames`** — controls the **inventory hostname** itself. Each entry is a
Jinja2 expression over the instance fields; the first non-empty result wins.

```yaml
# Use the title as-is (assumes it resolves in DNS):
hostnames:
  - displayTitle

# ...or build an FQDN by appending a domain suffix:
hostnames:
  - "displayTitle ~ '.example.org'"
```

**2. `compose`** — sets/overrides **host variables**, including `ansible_host`,
while leaving the inventory hostname short:

```yaml
hostnames:
  - displayTitle                       # inventory_hostname stays "WEB01"
compose:
  ansible_host: "displayTitle ~ '.example.org'"   # but we connect to the FQDN
```

If you set neither, `ansible_host` defaults to the resolved inventory hostname.

---

## Grouping

```yaml
keyed_groups:
  # os_windows, os_linux, ...
  - key: os
    prefix: os
    separator: "_"
  # status_connected, status_disconnected
  - key: connectionStatus
    prefix: status
  # env_production, env_dmz (from a Certify tag with categoryKey "environment")
  - key: tags_by_category.environment
    prefix: env

groups:
  windows: "'windows' in (os | default('') | lower)"
  linux: "'linux' in (os | default('') | lower)"
```

`keyed_groups` keyed on a list (such as `tags_by_category.environment`) creates one
group per element, so multi-valued tags "just work".

---

## Filtering

```yaml
filters:
  - "connectionStatus == 'Connected'"
  - "isAuthenticated"
```

Only instances for which every expression is true are added to the inventory.

---

## Caching

```yaml
cache: true
cache_plugin: ansible.builtin.jsonfile
cache_connection: /tmp/certify_hub_inventory
cache_timeout: 1800   # seconds
```

---

## TLS / internal CAs

For a Hub fronted by an internal CA, point the plugin at the CA bundle:

```yaml
ca_path: /etc/pki/tls/certs/internal-ca.pem
```

As a last resort (insecure, not for production) you can disable verification:

```yaml
validate_certs: false
```

---

## End-to-end example

`inventory/advanced.certify_hub.yml`:

```yaml
plugin: lspiehler.certify_hub.instances
url: https://ctw.example.org
validate_certs: false
filters:
  - "connectionStatus == 'Connected'"
hostnames:
  - displayTitle
compose:
  ansible_host: "displayTitle ~ '.example.org'"
  ansible_connection: "'winrm' if 'windows' in (os | default('') | lower) else 'ssh'"
keyed_groups:
  - key: os
    prefix: os
    separator: "_"
  - key: connectionStatus
    prefix: status
groups:
  windows: "'windows' in (os | default('') | lower)"
  linux: "'linux' in (os | default('') | lower)"
```

```bash
ansible-inventory -i inventory/advanced.certify_hub.yml --graph
ansible windows -i inventory/advanced.certify_hub.yml -m ansible.windows.win_ping
ansible linux   -i inventory/advanced.certify_hub.yml -m ansible.builtin.ping
```

Per-group connection details belong in `group_vars/` (e.g. `group_vars/windows.yml`
with `ansible_user`, WinRM transport/port, etc.).

---

## How it maps to the Hub API

| Step | Hub API |
| --- | --- |
| Fetch instances | `GET {url}/internal/v1/hub/instances` |
| Auth | `X-Client-ID` + `X-Client-Secret` headers, **or** `Authorization: Bearer` |
| Response | JSON array of `ManagedInstanceInfo` objects → one Ansible host each |

See your Hub's own API docs at `{url}/api/docs/` for the authoritative schema.

---

## Development & testing

```bash
# Unit tests (run from the repo root; pure Python, runs anywhere):
pytest tests/unit -q

# With the collection laid out under an ansible_collections/ tree:
ansible-test units --venv -v
ansible-test sanity --venv -v

# Inspect the generated documentation:
ansible-doc -t inventory lspiehler.certify_hub.instances
```

CI (GitHub Actions) runs sanity + unit tests against several `ansible-core`
versions — see `.github/workflows/ci.yml`.

---

## License

GPL-3.0-or-later. See [LICENSE](LICENSE).
