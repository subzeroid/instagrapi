import base64
import binascii
import datetime
import struct
import time
from typing import Tuple, Optional

from Cryptodome import Random
from Cryptodome.Cipher import AES, PKCS1_v1_5
from Cryptodome.PublicKey import RSA
from Cryptodome.Random import get_random_bytes
from nacl.public import PublicKey, SealedBox


class PasswordMixin:
    @staticmethod
    def _encrypt_with_rsa(public_key: bytes, data: bytes) -> bytes:
        key = RSA.import_key(public_key)
        cipher = PKCS1_v1_5.new(key)
        return cipher.encrypt(data)

    @staticmethod
    def _encrypt_with_aes(session_key: bytes, iv: bytes, data: bytes, timestamp: str) -> Tuple[bytes, bytes]:
        cipher = AES.new(session_key, AES.MODE_GCM, iv)
        cipher.update(timestamp.encode())
        return cipher.encrypt_and_digest(data)

    def password_encrypt_v4(self, password: str) -> str:
        public_key_id, public_key = self.password_public_keys()
        session_key = get_random_bytes(32)
        iv = get_random_bytes(12)
        timestamp = str(int(time.time()))
        public_key_decoded = base64.b64decode(public_key.encode())

        rsa_encrypted_session_key = self._encrypt_with_rsa(public_key_decoded, session_key)
        aes_encrypted_data, tag = self._encrypt_with_aes(session_key, iv, password.encode("utf8"), timestamp)

        size_buffer = len(rsa_encrypted_session_key).to_bytes(2, byteorder="little")
        encrypted_payload = base64.b64encode(
            b"\x01" +
            public_key_id.to_bytes(1, byteorder="big") +
            iv +
            size_buffer +
            rsa_encrypted_session_key +
            tag +
            aes_encrypted_data
        )

        return f"#PWD_INSTAGRAM:4:{timestamp}:{encrypted_payload.decode()}"

    def password_encrypt_v10(self, password: str) -> str:
        public_key_id, public_key = self.password_public_keys()

        key = Random.get_random_bytes(32)
        iv = bytes([0] * 12)

        timestamp = int(datetime.datetime.now().timestamp())

        aes = AES.new(key, AES.MODE_GCM, nonce=iv, mac_len=16)
        aes.update(str(timestamp).encode('utf-8'))
        encrypted_password, current_cipher_tag = aes.encrypt_and_digest(password.encode('utf-8'))

        pub_key_bytes = binascii.unhexlify(public_key)
        seal_box = SealedBox(PublicKey(pub_key_bytes))
        encrypted_key = seal_box.encrypt(key)

        encrypted = bytes([1,
                           int(public_key_id),
                           *list(struct.pack('<h', len(encrypted_key))),
                           *list(encrypted_key),
                           *list(current_cipher_tag),
                           *list(encrypted_password)])
        encrypted = base64.b64encode(encrypted).decode('utf-8')

        return f"#PWD_INSTAGRAM:10:{timestamp}:{encrypted}"

    def password_encrypt(self, password: str, version: Optional[int] = 4) -> str:
        match version:
            case 4:
                return self.password_encrypt_v4(password)

            case 10:
                return self.password_encrypt_v10(password)

            case _:
                raise ValueError(f"Unknown password encryption version: {version}")

    def password_public_keys(self) -> Tuple[int, str]:
        response = self.public.get("https://i.instagram.com/api/v1/qe/sync/")
        public_key_id = int(response.headers.get("ig-set-password-encryption-key-id"))
        public_key = response.headers.get("ig-set-password-encryption-pub-key")
        return public_key_id, public_key
