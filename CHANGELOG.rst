====================================
lspiehler.certify\_hub Release Notes
====================================

.. contents:: Topics

v0.1.0
======

Release Summary
---------------

Initial release of the ``lspiehler.certify_hub`` collection, providing the
``lspiehler.certify_hub.instances`` dynamic inventory plugin that builds an
Ansible inventory from the instances managed by a Certify Management Hub
(``GET /internal/v1/hub/instances``).

Authenticates with an API token (``X-Client-ID`` / ``X-Client-Secret``) or a
Bearer JWT, supports the full ``constructed`` interface (``hostnames``,
``compose``, ``groups``, ``keyed_groups``, ``strict``) plus Jinja2 ``filters``
and ``inventory_cache``. Since the Hub stores no network address, ``ansible_host``
is derived from ``displayTitle`` (the short machine name) via ``hostnames`` /
``compose``. The API tag list is exposed as ``certify_tags`` (``tags`` is a
reserved Ansible name), alongside the derived ``tags_by_category`` and
``tag_pairs`` helpers. Validated end-to-end against a live Hub.

New Plugins
-----------

Inventory
~~~~~~~~~

- instances - Certify Management Hub instances inventory source
