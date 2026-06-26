# Contributing

Thanks for helping improve `lspiehler.certify_hub`! This is a short checklist;
**[`CLAUDE.md`](CLAUDE.md)** has the full dev guide (setup, internals, open
questions) and **[`docs/hub-api.md`](docs/hub-api.md)** documents the Hub API.

## Development environment

Ansible runs as a controller only on **Linux / macOS / WSL** (not native Windows).

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install "ansible-core>=2.16" pytest
# make the repo importable as the collection (symlink into a collections tree):
mkdir -p ~/.ansible/collections/ansible_collections/lspiehler
ln -s "$PWD" ~/.ansible/collections/ansible_collections/lspiehler/certify_hub
```

## Before opening a PR

```bash
pytest tests/unit -q                         # unit tests (from the repo root)
ansible-doc -t inventory lspiehler.certify_hub.instances   # docs render

# from inside the collection path (the symlink target above):
ansible-test sanity --docker -v
ansible-test units  --docker -v
```

All three should be green. If you changed live behaviour, also do a real
`ansible-inventory -i <source>.certify_hub.yml --list` against a Hub.

## Conventions

- **API fidelity:** host variables mirror the Hub API field names verbatim
  (camelCase: `displayTitle`, `connectionStatus`, …). Derived helpers
  (`tags_by_category`, `tag_pairs`) are additive.
- **Use the framework:** keep the `constructed` + `inventory_cache` doc fragments;
  don't re-implement `compose` / `groups` / `keyed_groups` / `strict` / `cache`.
- **Source filenames:** inventory sources must end with `certify_hub.{yml,yaml}`
  or `ctw.{yml,yaml}` (enforced in `verify_file`).
- **Secrets:** never log request bodies, `client_secret`, or `token`. Prefer the
  `CERTIFY_HUB_*` environment variables over inline values.
- **Python:** every `.py` file keeps the GPL-3.0-or-later header plus
  `from __future__ import ...` and `__metaclass__ = type` (sanity-test compliance).
- **Docs:** update the README option table and `docs/hub-api.md` when the
  configuration surface or API usage changes.

## Changelog

Add a fragment under `changelogs/fragments/` for every user-visible change, e.g.:

```yaml
# changelogs/fragments/add-foo-option.yml
minor_changes:
  - instances inventory - add ``foo`` option to do X (https://github.com/lspiehler/ansible-certify-hub/pull/NN).
```

Sections: `minor_changes`, `bugfixes`, `breaking_changes`, `deprecated_features`,
`security_fixes`, `known_issues`, `major_changes`. Releases are assembled with
`antsibull-changelog release`.

## Versioning

Semantic versioning in `galaxy.yml`. Bump on release and generate the changelog
before tagging.

## Reporting issues

Open an issue with the Hub version, `ansible --version`, your (redacted) inventory
source, and the command + output (run with `-vvv` for inventory problems).
