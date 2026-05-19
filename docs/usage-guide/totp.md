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

## Bloks two-factor flow

Some accounts are moved by Instagram to a newer CAA/Bloks two-factor flow. In that case the legacy `accounts/two_factor_login/` endpoint can reject a valid code with `Invalid Parameters`.

`Client.login(..., verification_code="123456")` still uses the legacy mobile endpoint first. If Instagram requires the newer flow, use the low-level Bloks helpers with the `two_step_verification_context` returned by the login challenge response:

``` python
from instagrapi import Client

cl = Client()

# The context comes from Instagram's login challenge response.
context = "<two_step_verification_context>"

cl.bloks_two_step_verification_entrypoint(context)
cl.bloks_two_step_verification_method_picker(context)
cl.bloks_two_step_verification_select_method(context, selected_method="totp")

code = cl.totp_generate_code("<totp seed>")
result = cl.bloks_two_step_verification_verify_code(context, code, challenge="totp")
login_payload = cl.bloks_extract_login_response(result)
cl.bloks_apply_login_response(login_payload)
```

For SMS, select and verify the `sms` challenge instead:

``` python
cl.bloks_two_step_verification_select_method(context, selected_method="sms")
result = cl.bloks_two_step_verification_verify_code(context, "123456", challenge="sms")
```

`bloks_extract_login_response(...)` returns decoded `login_response`, response `headers`, cookie values, raw cookie header text, and the raw embedded object when Instagram returns a successful Bloks login payload. It returns `{}` when the response is an intermediate UI state or an error. `bloks_apply_login_response(...)` can then copy the returned authorization data and cookies into the current client session.

This is intentionally low-level. The full CAA login flow that produces `two_step_verification_context` is not wired into `Client.login()` yet, because it depends on newer login response state and account-specific verification behavior.
