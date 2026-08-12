import base64
import time
from typing import Any, Dict, Optional
from uuid import uuid4

from Cryptodome.Hash import SHA256
from Cryptodome.PublicKey import ECC
from Cryptodome.Random import get_random_bytes
from Cryptodome.Signature import DSS

from instagrapi.utils.serialization import dumps

# IGUSDIDRegistrationMutation in the Android 428 app profile emulated by instagrapi.
USDID_REGISTRATION_CLIENT_DOC_ID = "124930351917786857261002920888"
USDID_TOKEN_TTL = 3600
USDID_REFRESH_MARGIN = 300
ATTESTATION_KEYSTORE_ERROR = -1013


def _b64u(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


class DeviceAttestationMixin:
    """Device signals used by the current Android CAA login flow."""

    usdid = ""
    usdid_kid = ""
    usdid_private_key = ""
    usdid_registered = False
    attestation_challenge_nonce = ""
    attestation_key_nonce = ""
    _usdid_header_cache = ""
    _usdid_header_expires_at = 0

    def get_usdid_settings(self) -> Dict[str, Any]:
        """Return persisted USDID key material, if it has been generated."""
        if not self.usdid_private_key:
            return {}
        return {
            "usdid": self.usdid,
            "kid": self.usdid_kid,
            "private_key": self.usdid_private_key,
            "registered": self.usdid_registered,
        }

    def set_usdid_settings(self, settings: Optional[Dict[str, Any]] = None) -> bool:
        """Restore USDID key material and reset per-login attestation state."""
        settings = settings or {}
        self.usdid = str(settings.get("usdid") or "")
        self.usdid_kid = str(settings.get("kid") or "")
        self.usdid_private_key = str(settings.get("private_key") or "")
        self.usdid_registered = bool(settings.get("registered"))
        self.attestation_challenge_nonce = ""
        self.attestation_key_nonce = ""
        self._usdid_header_cache = ""
        self._usdid_header_expires_at = 0
        private = getattr(self, "private", None)
        if private is not None:
            private.headers.pop("X-Meta-Usdid", None)
        return bool(self.usdid_private_key)

    def usdid_generate(self, force: bool = False) -> str:
        """Generate the local P-256 signing identity used by ``X-Meta-Usdid``."""
        if self.usdid_private_key and not force:
            return self.usdid
        key = ECC.generate(curve="P-256")
        self.usdid_private_key = key.export_key(format="PEM")
        self.usdid = str(uuid4())
        self.usdid_kid = _b64u(get_random_bytes(32))
        self.usdid_registered = False
        self._usdid_header_cache = ""
        self._usdid_header_expires_at = 0
        return self.usdid

    def _usdid_key(self) -> ECC.EccKey:
        if not self.usdid_private_key:
            self.usdid_generate()
        return ECC.import_key(self.usdid_private_key)

    def _usdid_sign(self, message: str) -> bytes:
        signer = DSS.new(self._usdid_key(), "fips-186-3", encoding="der")
        return signer.sign(SHA256.new(message.encode()))

    @property
    def usdid_public_key_der(self) -> bytes:
        """DER SubjectPublicKeyInfo for the USDID P-256 public key."""
        return self._usdid_key().public_key().export_key(format="DER")

    def usdid_header(self, ttl: int = USDID_TOKEN_TTL) -> str:
        """Build the app's three-part ``X-Meta-Usdid`` signed value."""
        now = int(time.time())
        if self._usdid_header_cache and self._usdid_header_expires_at - now > USDID_REFRESH_MARGIN:
            return self._usdid_header_cache
        expires_at = now + ttl
        signed_part = f"{self.usdid}.{expires_at}"
        value = f"{signed_part}.{_b64u(self._usdid_sign(signed_part))}"
        self._usdid_header_cache = value
        self._usdid_header_expires_at = expires_at
        return value

    def usdid_registration_token(self, ttl: int = USDID_TOKEN_TTL) -> str:
        """Build the ES256 registration token sent by the Android app."""
        now = int(time.time())
        payload = _b64u(
            dumps(
                {
                    "sub": self.usdid,
                    "iat": now,
                    "aud": self.app_id,
                    "exp": now + ttl,
                    "pub": base64.b64encode(self.usdid_public_key_der).decode(),
                    "alg": "ES256",
                }
            ).encode()
        )
        protected = _b64u(
            dumps(
                {
                    "typ": "JWT",
                    "alg": "ES256",
                    "kid": self.usdid_kid,
                    "aid": self.app_id,
                    "ver": "1",
                }
            ).encode()
        )
        token = {
            "payload": payload,
            "signatures": [
                {
                    "protected": protected,
                    "signature": _b64u(self._usdid_sign(f"{protected}.{payload}")),
                }
            ],
        }
        return _b64u(dumps(token).encode())

    def usdid_register(self, client_doc_id: str = USDID_REGISTRATION_CLIENT_DOC_ID) -> bool:
        """Register the local USDID public key with Instagram."""
        if not self.usdid_private_key:
            self.usdid_generate()
        variables = {
            "input": {
                "usdid_token": {"sensitive_string_value": self.usdid_registration_token()},
                "fdid": {"sensitive_string_value": self.phone_id},
            }
        }
        result = self.private_graphql_www_request(
            "IGUSDIDRegistrationMutation",
            variables,
            client_doc_id=client_doc_id,
            extra_headers={
                "X-Root-Field-Name": "usdid_registration",
                "X-Graphql-Client-Library": "pando",
            },
        )
        registration = next(
            (
                value
                for key, value in (result.get("data") or {}).items()
                if "usdid_registration" in key and isinstance(value, dict)
            ),
            {},
        )
        self.usdid_registered = bool(registration.get("success"))
        return self.usdid_registered

    def attestation_create_android_keystore(self, key_hash: str = "", domain: Optional[str] = None) -> Dict:
        """Request the server nonce used by the CAA login attestation header."""
        kwargs = {
            "data": {"app_scoped_device_id": self.uuid, "key_hash": key_hash},
            "with_signature": False,
            "headers": {"X-FB-Friendly-Name": "IgApi: attestation/create_android_keystore/"},
            "login": True,
        }
        if domain:
            kwargs["domain"] = domain
        result = self.private_request("attestation/create_android_keystore/", **kwargs)
        self.attestation_challenge_nonce = str(result.get("challenge_nonce") or "")
        self.attestation_key_nonce = str(result.get("key_nonce") or "")
        return result

    def attestation_params(self, challenge_nonce: str = "") -> str:
        """Build the accepted keystore-unavailable ``X-IG-Attest-Params`` state."""
        nonce = challenge_nonce or self.attestation_challenge_nonce
        if not nonce:
            return ""
        return dumps(
            {
                "attestation": [
                    {
                        "version": 2,
                        "type": "keystore",
                        "errors": [ATTESTATION_KEYSTORE_ERROR],
                        "challenge_nonce": nonce,
                        "signed_nonce": "",
                        "key_hash": "",
                    }
                ]
            }
        )
