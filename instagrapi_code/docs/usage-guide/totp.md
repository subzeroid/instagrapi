# TOTP

TOTP setup and code generation

| Method                              | Return    | Description
| ----------------------------------- | --------- | ----------------------------------------------------------
| totp_generate_seed()                | str       | Generate 2FA TOTP seed
| totp_enable(verification_code: str) | List[str] | Enable TOTP 2FA (return backup keys, save it)
| totp_disable()                      | bool      | Disable TOTP 2FA
| totp_generate_code(seed: str)       | str       | Generate 2FA TOTP code (you can use it instead of Google Authenticator)


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
