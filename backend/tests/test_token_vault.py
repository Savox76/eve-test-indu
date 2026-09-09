from __future__ import annotations

import sys
import unittest
import uuid

from new_eden_foundry_backend.token_vault import (
    MemoryCredentialStore,
    RefreshTokenVault,
    SERVICE_PREFIX,
    TokenVaultError,
    WindowsCredentialStore,
)


CHARACTER_ID = 2_112_345_678


class FailingCredentialStore(MemoryCredentialStore):
    def __init__(self) -> None:
        super().__init__()
        self.fail_active_write = False

    def write(self, target: str, value: str) -> None:
        if self.fail_active_write and target.endswith("/refresh"):
            raise TokenVaultError("credential-write-failed")
        super().write(target, value)


class RefreshTokenVaultTests(unittest.TestCase):
    def setUp(self) -> None:
        self.store = FailingCredentialStore()
        self.vault = RefreshTokenVault(self.store)

    def test_stages_and_verifies_before_replacing_active_credential(self) -> None:
        self.vault.replace(CHARACTER_ID, "refresh-one")

        self.assertEqual(self.vault.read(CHARACTER_ID), "refresh-one")
        self.assertNotIn(
            f"{SERVICE_PREFIX}/{CHARACTER_ID}/refresh.pending",
            self.store.values,
        )

    def test_failed_commit_preserves_old_value_and_recovery_candidate(self) -> None:
        self.vault.replace(CHARACTER_ID, "refresh-old")
        candidate = self.vault.stage(CHARACTER_ID, "refresh-new")
        self.store.fail_active_write = True

        with self.assertRaisesRegex(TokenVaultError, "cr{×M6¶‰žËkºwµçom": {
          "optional": true
        },
        "vite": {
          "optional": false
        }
      }
    },
    "node_modules/w3c-xmlserializer": {
      "version": "5.0.0",
      "resolved": "https://registry.npmjs.org/w3c-xmlserializer/-/w3c-xmlserializer-5.0.0.tgz",
      "integrity": "sha512-o8qghlI8NZHU1lLPrpi2+Uq7abh4GGPpYANlalzWxyWteJOCsr/P+oPBA49TOLu5FTZO4d3F9MnWJfiMo4BkmA==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "xml-name-validator": "^5.0.0"
      },
      "engines": {
        "node": ">=18"
      }
    },
    "node_modules/webidl-conversions": {
      "version": "8.0.1",
      "resolved": "https://registry.npmjs.org/webidl-conversions/-/webidl-conversions-8.0.1.tgz",
      "integrity": "sha512-BMhLD/Sw+GbJC21C/UgyaZX41nPt8bUTg+jWyDeg7e7YN4xOM05YPSIXceACnXVtqyEw/LMClUQMtMZ+PGGpqQ==",
      "dev": true,
      "license": "BSD-2-Clause",
      "engines": {
        "node": ">=20"
      }
    },
    "node_modules/whatwg-mimetype": {
      "version": "5.0.0",
      "resolved": "https://registry.npmjs.org/whatwg-mimetype/-/whatwg-mimetype-5.0.0.tgz",
      "integrity": "sha512-sXcNcHOC51uPGF0P/D4NVtrkjSU2fNsm9iog4ZvZJsL3rjoDAzXZhkm2MWt1y+PUdggKAYVoMAIYcs78wJ51Cw==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": ">=20"
      }
    },
    "node_modules/whatwg-url": {
      "version": "17.1.0",
      "resolved": "https://registry.npmjs.org/whatwg-url/-/whatwg-url-17.1.0.tgz",
      "integrity": "sha512-3GeworPmc2ZfEEHP7lEbUfBX/L75wdEsi0rLNhXcXxnoN5jyq0SL5gCy06SGW2cyTIZdTvWIDQNQoza++vKeaw==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@exodus/bytes": "^1.15.1",
        "tr46": "^6.0.0",
        "webidl-conversions": "^8.0.1"
      },
      "engines": {
        "node": "^22.14.0 || >=24.0.0"
      }
    },
    "node_modules/why-is-node-running": {
      "version": "2.3.0",
      "resolved": "https://registry.npmjs.org/why-is-node-running/-/why-is-node-running-2.3.0.tgz",
      "integrity": "sha512-hUrmaWBdVDcxvYqnyh09zunKzROWjbZTiNy8dBEjkS7ehEDQibXJ7XvlmtbwuTclUiIyN+CyXQD4Vmko8fNm8w==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "siginfo": "^2.0.0",
        "stackback": "0.0.2"
      },
      "bin": {
        "why-is-node-running": "cli.js"
      },
      "engines": {
        "node": ">=8"
      }
    },
    "node_modules/xml-name-validator": {
      "version": "5.0.0",
      "resolved": "https://registry.npmjs.org/xml-name-validator/-/xml-name-validator-5.0.0.tgz",
      "integrity": "sha512-EvGK8EJ3DhaHfbRlETOWAS5pO9MZITeauHKJyb8wyajUfQUenkIg2MvLDTZ4T/TgIcm3HU0TFBgWWboAZ30UHg==",
      "dev": true,
      "license": "Apache-2.0",
      "engines": {
        "node": ">=18"
      }
    },
    "node_modules/xmlchars": {
      "version": "2.2.0",
      "resolved": "https://registry.npmjs.org/xmlchars/-/xmlchars-2.2.0.tgz",
      "integrity": "sha512-JZnDKK8B0RCDw84FNdDAIpZK+JuJw+s7Lz8nksI7SIuU3UXJJslUthsi+uWBUYOwPFwW7W7PRLRfUKpxjtjFCw==",
      "dev": true,
      "license": "MIT"
    }
  }
}
