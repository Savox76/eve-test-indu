from __future__ import annotations

import json
import unittest

from new_eden_foundry_backend.sso_registration import (
    EXPECTED_SCOPE_PACKAGES,
    SSO_REDIRECT_URI,
    SsoRegistrationError,
    load_bundled_sso_registration_profile,
    parse_sso_registration_profile,
)


class SsoRegistrationProfileTests(unittest.TestCase):
    def test_bundled_profile_is_valid_and_registered(self) -> None:
        profile = load_bundled_sso_registration_profile()

        self.assertEqual(profile.redirect_uri, SSO_REDIRECT_URI)
        self.assertEqual(profile.scope_packages, EXPECTED_SCOPE_PACKAGES)
        self.assertEqual(profile.developer_contact.name, "Savox76")
        self.assertEqual(profile.client_id, "a8409de72d5b4cab9b0424819d0abdec")
        self.assertTrue(profile.is_registered)
        self.assertEqual(profile.as_status_payload()["state"], "registered")
        self.assertEqual(
            profile.as_status_payload()["clientId"],
            "a8409de72d5b4cab9b0424819d0abdec",
        )

    def test_registered_profile_accepts_a_public_client_id(self) -> None:
        profile = load_bundled_sso_registration_profile()
        payload = {
            "applicationName": profile.application_name,
            "applicationType": profile.application_type,
            "clientId": "SyntheticClientIdForTestsOnly1234",
            "redirectUri": profile.redirect_uri,
            "developerContact": {
                "name": profile.developer_contact.name,
                "url": profile.developer_contact.url,
            },
            "scopePackages": {
                name: list(scopes) for name, scopes in profile.scope_packages.items()
            },
            "sourceReviewedAt": profile.source_reviewed_at,
        }

        registered = parse_sso_registration_profile(json.dumps(payload).encode())

        self.assertTrue(registered.is_registered)
        self.assertEqual(registered.as_status_payload()["state"], "registered")

    def test_callback_drift_is_rejected(self) -> None:
        raw = (
            load_bundled_sso_registration_profile()
        )
        payload = {
            "applicationName": raw.application_name,
            "applicationType": raw.application_type,
            "clientId": None,
            "redirectUri": "http://127.0.0.1:17892/oauth/callback",
            "developerContact": {
                "name": raw.developer_contact.name,
                "url": raw.developer_contact.url,
            },
            "scopePackages": {
                name: list(scopes) for name, scopes in raw.scope_packages.items()
            },
            "sourceReviewedAt": raw.source_reviewed_at,
        }

        with self.assertRaisesRegex(SsoRegistrationError, "fixed callback"):
            parse_sso_registration_profile(json.dumps(payload).encode())

    def test_scope_drift_is_rejected(self) -> None:
        profile = load_bundled_sso_registration_profile()
        packages = {name: list(scopes) for name, scopes in profile.scope_packages.items()}
        packages["industry-core"].append("esi-mail.send_mail.v1")
        payload = {
            "applicationName": profile.application_name,
            "applicationType": profile.application_type,
            "clientId": None,
            "redirectUri": profile.redirect_uri,
            "developerContact": {
                "name": profile.developer_contact.name,
                "url": profile.developer_contact.url,
            },
            "scopePackages": packages,
            "sourceReviewedAt": profile.source_reviewed_at,
        }

        with self.assertRaisesRegex(SsoRegistrationError, "has drifted"):
            parse_sso_registration_profile(json.dumps(payload).encode())


if __name__ == "__main__":
    unittest.main()
