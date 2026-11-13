"""APK-derived key-ID contract, verified without provider requests."""

import base64
import json
import unittest
from unittest import mock

from Cryptodome.Hash import SHA256
from Cryptodome.PublicKey import ECC
from Cryptodome.Signature import DSS

from instagrapi.mixins.attestation import DeviceAttestationMixin


class UsdidKeyIdTestCase(unittest.TestCase):
    # Public P-256 test scalar 7; kid hashes standard Base64(SPKI), not raw DER.
    EXPECTED_KID = "bFEdfmetFb9BHfxRqfzSwhFGWY3xaktCnilbap-aZp4"

    def client_with_test_key(self):
        client = DeviceAttestationMixin()
        client.app_id = "567067343352427"
        client.usdid = "00000000-0000-4000-8000-000000000000"
        client.usdid_private_key = ECC.construct(curve="P-256", d=7).export_key(format="PEM")
        return client

    def test_key_id_matches_apk_golden_vector(self):
        self.assertEqual(self.client_with_test_key()._usdid_key_id(), self.EXPECTED_KID)

    def test_new_identity_uses_public_key_hash(self):
        client = DeviceAttestationMixin()
        with mock.patch("instagrapi.mixins.attestation.ECC.generate", return_value=ECC.construct(curve="P-256", d=7)):
            client.usdid_generate()
        self.assertEqual(client.usdid_kid, self.EXPECTED_KID)

    def test_registration_repairs_stale_kid_without_rotating_identity(self):
        client = self.client_with_test_key()
        original = (client.usdid, client.usdid_private_key)
        client.usdid_kid = "old-random-key-id"
        token = client.usdid_registration_token()

        def decode(value):
            return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))

        outer = json.loads(decode(token))
        signature = outer["signatures"][0]
        protected = json.loads(decode(signature["protected"]))
        payload = json.loads(decode(outer["payload"]))
        self.assertEqual(protected["kid"], self.EXPECTED_KID)
        self.assertEqual(client.usdid_kid, self.EXPECTED_KID)
        self.assertEqual((client.usdid, client.usdid_private_key), original)
        self.assertEqual(payload["sub"], original[0])
        self.assertEqual(payload["aud"], client.app_id)
        verifier = DSS.new(ECC.import_key(base64.b64decode(payload["pub"])), "fips-186-3", encoding="der")
        signing_input = f"{signature['protected']}.{outer['payload']}".encode()
        verifier.verify(SHA256.new(signing_input), decode(signature["signature"]))


if __name__ == "__main__":
    unittest.main()
