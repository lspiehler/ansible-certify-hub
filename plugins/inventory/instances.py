# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Lyas Spiehler (@lspiehler)
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
name: instances
short_description: Certify Management Hub instances inventory source
version_added: "0.1.0"
author:
  - Lyas Spiehler (@lspiehler)
description:
  - Builds an Ansible inventory from the instances managed by a Certify The Web
    (Webprofusion) Management Hub.
  - Calls the C(GET /internal/v1/hub/instances) Hub API endpoint; every managed
    instance becomes an Ansible host.
  - Because the Hub does not store a network address for an instance (agents dial
    out to the Hub), use O(hostnames) and/or O(compose) to derive a reachable
    C(ansible_host). See the examples.
  - Uses a YAML configuration source whose filename ends with C(certify_hub.yml),
    C(certify_hub.yaml), C(ctw.yml) or C(ctw.yaml).
extends_documentation_fragment:
  - constructed
  - inventory_cache
options:
  plugin:
    description:
      - Token that ensures this is a source file for the
        C(lspiehler.certify_hub.instances) plugin.
    type: str
    required: true
    choices:
      - lspiehler.certify_hub.instances
      - certify_hub.instances
      - instances
  url:
    description:
      - Base URL of the Certify Management Hub, scheme and host (and optional
        port), e.g. V(https://ctw.example.org).
    type: str
    required: true
    env:
      - name: CERTIFY_HUB_URL
  client_id:
    description:
      - API token client ID, sent in the C(X-Client-ID) request header.
      - Create an API token in the Hub UI under Settings > Security > API Access.
        The token needs permission to read Hub instances.
      - Required together with O(client_secret), unless O(token) is supplied.
    type: str
    required: false
    env:
      - name: CERTIFY_HUB_CLIENT_ID
  client_secret:
    description:
      - API token client secret, sent in the C(X-Client-Secret) request header.
      - Required together with O(client_id), unless O(token) is supplied.
    type: str
    required: false
    env:
      - name: CERTIFY_HUB_CLIENT_SECRET
  token:
    description:
      - A Bearer JWT, sent in the C(Authorization) header instead of an API token
        pair. Mutually exclusive with O(client_id)/O(client_secret).
    type: str
    required: false
    env:
      - name: CERTIFY_HUB_TOKEN
  validate_certs:
    description:
      - Whether to verify the Hub's TLS certificate.
      - Set to V(false) only for an internal/self-signed certificate; this is
        insecure and should be avoided in production.
    type: bool
    default: true
  ca_path:
    description:
      - Path to a PEM CA bundle used to verify the Hub's TLS certificate.
    type: path
    required: false
  timeout:
    description:
      - HTTP request timeout, in seconds.
    type: int
    default: 30
  hostnames:
    description:
      - An ordered list of Jinja2 expressions used to compose each host's
        inventory hostname. Each expression is evaluated against the instance
        fields (e.g. C(displayTitle), C(os), C(instanceId)); the first one that
        yields a non-empty value wins.
      - A bare field name such as V(displayTitle) is itself a valid expression.
      - 'For example V("displayTitle ~ ''.example.org''") appends a domain suffix
        to build an FQDN.'
    type: list
    elements: str
    default:
      - displayTitle
      - customTitle
      - title
      - instanceId
      - id
  filters:
    description:
      - A list of Jinja2 boolean expressions evaluated against each instance.
      - An instance is included only when every expression is true.
      - 'The Hub reports C(connectionStatus) in lower case (e.g. V(connected)),
        so compare case-insensitively, for example
        V("connectionStatus | lower == ''connected''").'
    type: list
    elements: str
    default: []
notes:
  - One of (O(client_id) plus O(client_secret)) or O(token) is normally required;
    the Hub rejects unauthenticated requests.
  - In addition to the raw API fields, each host receives a C(tags_by_category)
    dict (categoryKey to list of values) and a C(tag_pairs) list of
    C(categoryKey:value) strings, to make grouping on Certify tags easier.
  - The API's C(tags) array is exposed as C(certify_tags) rather than C(tags),
    because C(tags) is a reserved Ansible variable name.
  - C(displayTitle) holds the instance's short machine name (e.g. V(WEB01)), not
    a fully-qualified domain name, so append a domain suffix via O(hostnames) or
    O(compose) when the short name is not resolvable. The Hub's own instance may
    report a container/host id rather than a hostname.
seealso:
  - name: Certify Management Hub
    description: Product documentation.
    link: https://docs.certifytheweb.com/docs/hub/
"""

EXAMPLES = r"""
# certify_hub.yml --- minimal; credentials come from the environment
# (CERTIFY_HUB_CLIENT_ID / CERTIFY_HUB_CLIENT_SECRET) or from CERTIFY_HUB_TOKEN.
plugin: lspiehler.certify_hub.instances
url: https://ctw.example.org

# ---------------------------------------------------------------------------
# Append a domain suffix to the instance title to form a resolvable FQDN,
# group by OS and connection status, choose the connection type per OS, and
# only include instances that are currently connected.
plugin: lspiehler.certify_hub.instances
url: https://ctw.example.org
client_id: "{{ lookup('ansible.builtin.env', 'CERTIFY_HUB_CLIENT_ID') }}"
client_secret: "{{ lookup('ansible.builtin.env', 'CERTIFY_HUB_CLIENT_SECRET') }}"
filters:
  - "connectionStatus | lower == 'connected'"
hostnames:
  - "displayTitle ~ '.example.org'"
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

# ---------------------------------------------------------------------------
# Build groups from a Certify tag category (e.g. tags with categoryKey
# 'environment'), and cache results for 30 minutes.
plugin: lspiehler.certify_hub.instances
url: https://ctw.example.org
cache: true
cache_plugin: ansible.builtin.jsonfile
cache_connection: /tmp/certify_hub_inventory
cache_timeout: 1800
keyed_groups:
  - key: tags_by_category.environment
    prefix: env
"""

import json

from ansible.errors import AnsibleError
from ansible.module_utils.common.text.converters import to_native, to_text
from ansible.module_utils.parsing.convert_bool import boolean
from ansible.module_utils.six.moves.urllib.error import HTTPError, URLError
from ansible.module_utils.urls import open_url
from ansible.plugins.inventory import BaseInventoryPlugin, Cacheable, Constructable
from ansible.utils.display import Display

display = Display()

INSTANCES_PATH = "/internal/v1/hub/instances"


class InventoryModule(BaseInventoryPlugin, Constructable, Cacheable):

    NAME = "lspiehler.certify_hub.instances"

    def verify_file(self, path):
        """Return True only for files this plugin should handle."""
        if super(InventoryModule, self).verify_file(path):
            return path.endswith(
                ("certify_hub.yml", "certify_hub.yaml", "ctw.yml", "ctw.yaml")
            )
        return False

    def _build_headers(self):
        """Assemble auth + accept headers from the configured options."""
        headers = {"Accept": "application/json"}
        client_id = self.get_option("client_id")
        client_secret = self.get_option("client_secret")
        token = self.get_option("token")

        if client_id and client_secret:
            headers["X-Client-ID"] = client_id
            headers["X-Client-Secret"] = client_secret
        elif token:
            headers["Authorization"] = "Bearer %s" % token
        elif client_id or client_secret:
            raise AnsibleError(
                "certify_hub: 'client_id' and 'client_secret' must be set together."
            )
        else:
            display.warning(
                "certify_hub: no credentials configured (client_id/client_secret "
                "or token); the Hub will likely reject the request."
            )
        return headers

    def _fetch_instances(self):
        """Call the Hub API and return the decoded list of instances."""
        url = self.get_option("url")
        if not url:
            raise AnsibleError("certify_hub: 'url' is required.")
        endpoint = url.rstrip("/") + INSTANCES_PATH
        headers = self._build_headers()

        display.vvv("certify_hub: GET %s" % endpoint)
        try:
            response = open_url(
                endpoint,
                headers=headers,
                method="GET",
                validate_certs=self.get_option("validate_certs"),
                ca_path=self.get_option("ca_path"),
                timeout=self.get_option("timeout"),
                follow_redirects="safe",
            )
            body = response.read()
        except HTTPError as e:
            detail = ""
            try:
                detail = to_text(e.read())
            except Exception:
                pass
            if e.code in (401, 403):
                raise AnsibleError(
                    "certify_hub: authentication failed (HTTP %s) calling %s. "
                    "Check client_id/client_secret or token and the token's "
                    "permissions. %s" % (e.code, endpoint, detail)
                )
            raise AnsibleError(
                "certify_hub: HTTP %s calling %s. %s" % (e.code, endpoint, detail)
            )
        except URLError as e:
            raise AnsibleError(
                "certify_hub: could not reach %s: %s"
                % (endpoint, to_native(e.reason))
            )
        except Exception as e:
            raise AnsibleError(
                "certify_hub: error calling %s: %s" % (endpoint, to_native(e))
            )

        try:
            data = json.loads(body)
        except ValueError as e:
            raise AnsibleError(
                "certify_hub: invalid JSON from %s: %s" % (endpoint, to_native(e))
            )
        if not isinstance(data, list):
            raise AnsibleError(
                "certify_hub: expected a JSON array of instances from %s, got %s"
                % (endpoint, type(data).__name__)
            )
        return data

    @staticmethod
    def _build_hostvars(instance):
        """Copy the raw instance fields and add tag convenience vars."""
        hostvars = dict(instance)

        # 'tags' is a reserved Ansible variable name; setting it as a host var
        # triggers a "Found variable using reserved name" warning on every run.
        # Expose the raw API list under 'certify_tags' instead.
        if "tags" in hostvars:
            hostvars["certify_tags"] = hostvars.pop("tags")

        tags_by_category = {}
        tag_pairs = []
        for tag in instance.get("tags") or []:
            if not isinstance(tag, dict):
                continue
            category = tag.get("categoryKey")
            if category is None:
                continue
            value = tag.get("value")
            tags_by_category.setdefault(category, [])
            if value is not None:
                tags_by_category[category].append(value)
                tag_pairs.append("%s:%s" % (category, value))

        hostvars["tags_by_category"] = tags_by_category
        hostvars["tag_pairs"] = tag_pairs
        return hostvars

    def _passes_filters(self, hostvars, filters, strict):
        """Return True when every filter expression evaluates truthy."""
        for expr in filters:
            try:
                result = self._compose(expr, hostvars)
            except Exception as e:
                if strict:
                    raise AnsibleError(
                        "certify_hub: error evaluating filter %r: %s"
                        % (expr, to_native(e))
                    )
                return False
            if not boolean(result, strict=False):
                return False
        return True

    def _resolve_hostname(self, hostvars, hostnames, strict):
        """Return the first non-empty hostname expression result."""
        for expr in hostnames:
            try:
                value = self._compose(expr, hostvars)
            except Exception as e:
                if strict:
                    raise AnsibleError(
                        "certify_hub: error evaluating hostname expression %r: %s"
                        % (expr, to_native(e))
                    )
                continue
            if value is None:
                continue
            value = to_text(value).strip()
            if value and value.lower() != "none":
                return value
        return None

    def _populate(self, instances):
        strict = self.get_option("strict")
        hostnames = self.get_option("hostnames")
        filters = self.get_option("filters")
        compose = self.get_option("compose")
        groups = self.get_option("groups")
        keyed_groups = self.get_option("keyed_groups")

        for instance in instances:
            if not isinstance(instance, dict):
                continue

            hostvars = self._build_hostvars(instance)
            if not self._passes_filters(hostvars, filters, strict):
                continue

            hostname = self._resolve_hostname(hostvars, hostnames, strict)
            if not hostname:
                display.vvv(
                    "certify_hub: skipping instance with no resolvable hostname: %s"
                    % instance.get("instanceId") or instance.get("id")
                )
                continue

            self.inventory.add_host(hostname)
            for key, value in hostvars.items():
                self.inventory.set_variable(hostname, key, value)

            # Default ansible_host to the resolved name; a compose entry for
            # ansible_host (below) takes precedence if the user defines one.
            self.inventory.set_variable(hostname, "ansible_host", hostname)

            self._set_composite_vars(compose, hostvars, hostname, strict=strict)
            self._add_host_to_composed_groups(groups, hostvars, hostname, strict=strict)
            self._add_host_to_keyed_groups(
                keyed_groups, hostvars, hostname, strict=strict
            )

    def parse(self, inventory, loader, path, cache=True):
        super(InventoryModule, self).parse(inventory, loader, path, cache)
        self._read_config_data(path)

        self.load_cache_plugin()
        cache_key = self.get_cache_key(path)

        # 'cache' is the user's setting; 'cache' arg is whether the manager
        # allows reading the cache this run.
        use_cache = self.get_option("cache")
        read_cache = use_cache and cache
        update_cache = use_cache and not cache

        instances = None
        if read_cache:
            try:
                instances = self._cache[cache_key]
            except KeyError:
                update_cache = True

        if instances is None:
            instances = self._fetch_instances()

        if update_cache:
            self._cache[cache_key] = instances

        self._populate(instances)
