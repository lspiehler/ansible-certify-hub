# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Lyas Spiehler (@lspiehler)
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import importlib.util
import os

import pytest
from jinja2 import Environment

from ansible.errors import AnsibleError

# Load the plugin by file path so the tests run both under `ansible-test units`
# and under a plain `pytest` invocation from the repo root.
_HERE = os.path.dirname(__file__)
_PLUGIN_PATH = os.path.abspath(
    os.path.join(_HERE, "..", "..", "..", "..", "plugins", "inventory", "instances.py")
)
_spec = importlib.util.spec_from_file_location("ctw_instances_under_test", _PLUGIN_PATH)
instances = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(instances)
InventoryModule = instances.InventoryModule

_JINJA = Environment()


def _fake_compose(expr, variables):
    """Mirror Constructable._compose: wrap in {{ }} and render with Jinja2."""
    return _JINJA.from_string("{{ %s }}" % expr).render(**variables)


SAMPLE = {
    "instanceId": "abc-123",
    "id": "abc-123",
    "displayTitle": "web01",
    "customTitle": None,
    "title": "web01",
    "os": "Windows",
    "osVersion": "10.0.20348",
    "clientName": "Certify Certificate Manager",
    "clientVersion": "6.0.0",
    "connectionStatus": "connected",
    "tags": [
        {"categoryKey": "environment", "value": "production"},
        {"categoryKey": "environment", "value": "dmz"},
        {"categoryKey": "datacenter", "value": "nola"},
    ],
}


@pytest.fixture
def module():
    m = InventoryModule()
    # Bypass the real templar; expressions are simple Jinja2.
    m._compose = _fake_compose
    return m


def test_build_hostvars_copies_fields_and_adds_tag_helpers():
    hv = InventoryModule._build_hostvars(SAMPLE)
    assert hv["displayTitle"] == "web01"
    assert hv["os"] == "Windows"
    # 'tags' is reserved; the raw list is exposed as 'certify_tags'.
    assert "tags" not in hv
    assert hv["certify_tags"] == SAMPLE["tags"]
    assert hv["tags_by_category"] == {
        "environment": ["production", "dmz"],
        "datacenter": ["nola"],
    }
    assert "environment:production" in hv["tag_pairs"]
    assert "datacenter:nola" in hv["tag_pairs"]


def test_build_hostvars_handles_missing_tags():
    hv = InventoryModule._build_hostvars({"displayTitle": "x"})
    assert "tags" not in hv
    assert "certify_tags" not in hv
    assert hv["tags_by_category"] == {}
    assert hv["tag_pairs"] == []


def test_build_headers_api_key(module):
    opts = {"client_id": "cid", "client_secret": "csec", "token": None}
    module.get_option = lambda name: opts[name]
    headers = module._build_headers()
    assert headers["X-Client-ID"] == "cid"
    assert headers["X-Client-Secret"] == "csec"
    assert "Authorization" not in headers


def test_build_headers_bearer(module):
    opts = {"client_id": None, "client_secret": None, "token": "jwt"}
    module.get_option = lambda name: opts[name]
    headers = module._build_headers()
    assert headers["Authorization"] == "Bearer jwt"
    assert "X-Client-ID" not in headers


def test_build_headers_partial_credentials_raises(module):
    opts = {"client_id": "cid", "client_secret": None, "token": None}
    module.get_option = lambda name: opts[name]
    with pytest.raises(AnsibleError):
        module._build_headers()


def test_resolve_hostname_first_non_empty_wins(module):
    # customTitle is None -> should fall through to displayTitle.
    name = module._resolve_hostname(
        dict(SAMPLE), ["customTitle", "displayTitle", "id"], strict=False
    )
    assert name == "web01"


def test_resolve_hostname_supports_suffix_expression(module):
    name = module._resolve_hostname(
        dict(SAMPLE), ["displayTitle ~ '.example.org'"], strict=False
    )
    assert name == "web01.example.org"


def test_resolve_hostname_returns_none_when_all_empty(module):
    name = module._resolve_hostname({"displayTitle": None}, ["displayTitle"], strict=False)
    assert name is None


def test_passes_filters_true_and_false(module):
    hv = dict(SAMPLE)
    # The live Hub reports connectionStatus in lower case; compare with | lower.
    assert module._passes_filters(hv, ["connectionStatus | lower == 'connected'"], False) is True
    assert module._passes_filters(hv, ["connectionStatus | lower == 'disconnected'"], False) is False


def test_passes_filters_empty_list_includes(module):
    assert module._passes_filters(dict(SAMPLE), [], False) is True
