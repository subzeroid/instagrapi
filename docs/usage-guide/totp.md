# TOTP

TOTP setup and code generation

| Method | Return | Description |
| --- | --- | --- |
| totp_generate_seed() | str | Generate 2FA TOTP seed |
| totp_enable(verification_code: str) | List[str] | Enable TOTP 2FA and return backup codes |
| totp_disable() | bool | Disable TOTP 2FA |
| totp_generate_code(seed: str) | str | Generate a current 2FA TOTP code from a seed |


Example:

``` python
>>> from instagrapi import Client
>>> cl = Client()
>>> cl.login(USERNAME, PASSWORD)

>>> seed = cl.totp_generate_seed()
"67EIYPWCIJDTTVX632NEODKEU2PY5BIW"

>>> code = cl.totp_generate_code(seed)
"123456"

>>> cl.totp_enable(code)
["1234 5678", "1234 5678", "1234 5678", "1234 5678", "1234 5678"]

>>> cl.totp_disable()
True
```

Notes:

* `totp_generate_seed()` gives you the secret key you would normally scan into an authenticator app.
* `totp_generate_code()` is a local helper and can be used anywhere you already have the TOTP seed.
* Save the backup codes returned by `totp_enable()` immediately. Instagram does not guarantee that you can fetch the same codes again later.
