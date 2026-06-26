# CLAUDE.md

Handoff + working guidance for this repository. **Read this first** when resuming
development (intended to continue on a **Linux** control node).

## What this is

`lspiehler.certify_hub` — an **Ansible dynamic inventory collection** for
**Certify The Web (Webprofusion) Management Hub**. The single plugin,
`lspiehler.certify_hub.instances`, calls the Hub's
`GET /internal/v1/hub/instances` API and turns each managed instance into an
Ansible host. Example Hub URL: `https://ctw.example.org` (point the inventory source at your own Hub).

It is third-party / community (not vendor-affiliated). Licensed GPL-3.0-or-later
(Ansible plugin convention).

## Status (2026-06-26)

**Validated end-to-end on Linux against the live Hub.** All scaffold TODOs are
done:

- [x] `ansible-doc -t inventory lspiehler.certify_hub.instances` renders cleanly.
- [x] `pytest tests/unit` passes (10 tests).
- [x] **Live run** against the real Hub (10 instances; `--list` and `--graph`
      green) with a read-only API token.
- [x] `ansible-test sanity` / `ansible-test units` pass. Run here via `--venv`
      (this box has no Docker); use `--docker` where available. CI runs `--docker`.
- [x] Header spelling resolved: hyphenated **`X-Client-ID`** / **`X-Client-Secret`**
      is correct (the `X-ClientID` prose was a typo). No code change needed.
- [x] `displayTitle` resolved: it's the instance's **short machine name**, not an
      FQDN (the Hub's own instance shows a container id). Append a domain suffix
      for `ansible_host`; examples do this.
- [x] TLS resolved: `validate_certs: true` (default) works against the Hub's
      publicly-trusted (Let's Encrypt) cert.

Empirical findings folded into code/docs: `connectionStatus` is **lower case**
(`connected`) so filters compare with `| lower`; the API `tags` array is exposed
as **`certify_tags`** (the var `tags` is reserved). **Credential scope matters:** a
managed-instance service principal authenticates but is *not* authorized for the
`instances` listing (401) — the inventory needs a token whose principal holds the
**Hub Viewer** role (see README "Creating a read-only API token").

Remaining before a 0.1.0 tag: claim the Galaxy namespace and publish.

## ⚠️ Environment: control node must be Linux/macOS/WSL

Ansible does not support **native Windows** as a control node — `ansible-core`
imports `grp`/`pwd`/`fcntl` at import time. `pip install ansible-core` succeeds on
Windows but `ansible*`/`pytest` of the plugin fail with
`ModuleNotFoundError: No module named 'grp'`. Continue on Linux (or WSL). This is
purely a development/testing constraint; the plugin itself is fine on a Linux
controller.

## Repo layout

```
ansible-certify-hub/
├── galaxy.yml                  # collection metadata: lspiehler.certify_hub v0.1.0, GPL-3.0-or-later
├── meta/runtime.yml            # requires_ansible: '>=2.15.0'
├── plugins/inventory/
│   └── instances.py            # THE plugin (DOCUMENTATION/EXAMPLES + InventoryModule)
├── examples/
│   ├── certify_hub.yml             # minimal inventory source
│   └── advanced.certify_hub.yml    # worked example (suffix FQDN, os/status/tag groups)
├── tests/unit/
│   ├── requirements.txt
│   └── plugins/inventory/test_instances.py   # pytest; mocks _compose with real jinja2
├── docs/hub-api.md             # captured Hub API reference (schema, auth, endpoints)
├── changelogs/                 # antsibull-changelog config + fragments
├── .github/workflows/ci.yml    # sanity + units across ansible-core versions
├── README.md                   # user-facing docs
├── LICENSE                     # GPLv3 (full text)
├── CLAUDE.md                   # this file
└── .gitignore
```

## Design decisions (locked in with the user)

1. **Form:** inventory **plugin in a collection** (not a script).
2. **Naming:** namespace `lspiehler` (the user's GitHub handle — do **not** squat the
   vendor's `certifytheweb`/`webprofusion`; `community.*` is reserved for adopted
   collections), collection `certify_hub`, plugin `instances` →
   FQCN **`lspiehler.certify_hub.instances`**. Repo dir `ansible-certify-hub`.
3. **Host addressing:** the API exposes no address, so use the **constructed**
   interface — `hostnames` (ordered Jinja2 expressions for the inventory hostname)
   and/or `compose` (to set `ansible_host`). The user specifically wanted both
   "displayTitle as-is" and "displayTitle + domain suffix" to be possible; both are.
4. **Auth:** API-token pair via `X-Client-ID`/`X-Client-Secret` headers (primary) or
   Bearer `token` (alternative). Each option also reads an env var
   (`CERTIFY_HUB_URL`, `CERTIFY_HUB_CLIENT_ID`, `CERTIFY_HUB_CLIENT_SECRET`,
   `CERTIFY_HUB_TOKEN`). Never put secrets in the inventory file.
5. **Live validation:** validate parsing and the header spelling against a real
   Hub using a read-only API token.

## Conventions for this collection

- **API field names stay as the API returns them** (camelCase: `displayTitle`,
  `connectionStatus`, `osVersion`). Host vars mirror the API 1:1, plus the derived
  `tags_by_category` (dict) and `tag_pairs` (list). The one exception: the API
  `tags` array is exposed as **`certify_tags`** because `tags` is a reserved
  Ansible variable name.
- Keep the full **constructed** + **inventory_cache** doc fragments; don't
  re-implement `compose`/`groups`/`keyed_groups`/`strict`/`cache`.
- Inventory source files must end with `certify_hub.{yml,yaml}` or `ctw.{yml,yaml}`
  (enforced in `verify_file`).
- GPLv3 header on every `.py` file; `from __future__ import ...` + `__metaclass__`
  for sanity-test compliance.
- Add a `changelogs/fragments/*.yml` entry for every user-visible change.
- Don't log request bodies / secrets. `client_secret`/`token` should never be
  printed (the plugin only sends them as headers).

## Setup & validation on Linux (copy/paste)

```bash
# 1) Toolchain
python3 -m venv .venv && . .venv/bin/activate
pip install "ansible-core>=2.16" pytest

# 2) Make the collection importable as lspiehler.certify_hub.
#    Easiest: symlink this repo into a collections tree.
mkdir -p ~/.ansible/collections/ansible_collections/lspiehler
ln -s "$PWD" ~/.ansible/collections/ansible_collections/lspiehler/certify_hub
#    (alternatively: `ansible-galaxy collection build . && ansible-galaxy collection install lspiehler-certify_hub-*.tar.gz`)

# 3) Docs render?
ansible-doc -t inventory lspiehler.certify_hub.instances

# 4) Unit tests
pytest tests/unit -q

# 5) LIVE test (needs a real token). Point url at the real Hub.
export CERTIFY_HUB_CLIENT_ID='...'
export CERTIFY_HUB_CLIENT_SECRET='...'
cat > /tmp/ctw.certify_hub.yml <<'YAML'
plugin: lspiehler.certify_hub.instances
url: https://ctw.example.org
# validate_certs: false   # only if the cert isn't trusted by the box
YAML
ansible-inventory -i /tmp/ctw.certify_hub.yml --list -vvv
ansible-inventory -i /tmp/ctw.certify_hub.yml --graph

# 6) Collection test suite (run from INSIDE the collection path from step 2)
cd ~/.ansible/collections/ansible_collections/lspiehler/certify_hub
ansible-test sanity --docker -v
ansible-test units  --docker -v

# 7) Build a release artifact
ansible-galaxy collection build .
```

If the live call 401s with a valid token, edit `_build_headers` in
`plugins/inventory/instances.py` to send `X-ClientID` (no hyphen) instead of — or
in addition to — `X-Client-ID`, then re-run step 5. See `docs/hub-api.md`.

## Plugin internals (quick map of `plugins/inventory/instances.py`)

- `verify_file` — restricts to the `*certify_hub.{yml,yaml}` / `*ctw.{yml,yaml}` suffixes.
- `_build_headers` — chooses API-key vs Bearer; raises on a half-set key pair.
- `_fetch_instances` — `open_url` GET, maps HTTP/URL errors to friendly
  `AnsibleError`s, returns the decoded JSON array.
- `_build_hostvars` — copies API fields verbatim (renaming `tags` →
  `certify_tags`, a reserved name), adds `tags_by_category` / `tag_pairs`.
- `_passes_filters` — every `filters` Jinja expr must be truthy (via `_compose` + `boolean`).
- `_resolve_hostname` — first non-empty `hostnames` expr wins (treats `None`/`"none"` as empty).
- `_populate` — add host, set vars, default `ansible_host`, then
  `_set_composite_vars` / `_add_host_to_composed_groups` / `_add_host_to_keyed_groups`.
- `parse` — reads config, wires up the cache plugin (`inventory_cache`), fetches, populates.

The unit tests load the plugin **by file path** (importlib) so they run both under
plain `pytest` (repo root) and `ansible-test units` (collection path). They stub
`_compose` with a real `jinja2.Environment` to mirror `Constructable._compose`.

## Likely next features (after green validation)

- Optional richer host vars (flatten `summary` cert counts; expose
  `dateLastReported` as an age).
- `tags_as_groups`-style convenience (auto group by every tag category).
- Pagination/server-side filtering only if the API later grows them (today it
  returns a bare array).
- A second inventory source-name pattern if users dislike the suffix requirement.
- Publish to Galaxy once a namespace is claimed.

## Pointers

- `docs/hub-api.md` — Hub API schema/auth/endpoints (captured from the live spec).
- `README.md` — end-user configuration reference and examples.
- Product docs: https://docs.certifytheweb.com/docs/hub/
