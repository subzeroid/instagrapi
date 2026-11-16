import json
import math
import re
import time
from copy import deepcopy
from uuid import uuid4

from instagrapi.exceptions import LoginRequired, SecondaryAccountError
from instagrapi.extractors import extract_user_short
from instagrapi.secondary import APPS, DOC_ID, FLOW, continuation, registration
from instagrapi.types import SecondaryAccount


class MultipleAccountsMixin:
    """
    Helpers for multiple accounts.
    """

    def featured_accounts_v1(self, target_user_id: str) -> dict:
        target_user_id = str(target_user_id)
        return self.private_request(
            "multiple_accounts/get_featured_accounts/",
            params={"target_user_id": target_user_id},
        )

    def get_account_family_v1(self) -> dict:
        return self.private_request("multiple_accounts/get_account_family/")

    def create_secondary_account(self, username: str, *, link_to_main_account: bool = True) -> SecondaryAccount:
        """Create a linked additional profile, leaving this client's session unchanged.

        Returns a typed user and separate session settings. Creating an account
        accepts Instagram's terms for that account. Only the observed Accounts
        Center flow is supported; verification/unknown screens stop the method.
        A failed final submission may have created an account: do not retry it
        automatically. Legacy ``get_account_family_v1`` may remain empty.
        """
        if not isinstance(username, str) or re.fullmatch(r"[A-Za-z0-9_.]{1,30}", username) is None:
            raise ValueError("username must contain 1-30 ASCII letters, digits, underscores or periods")
        if link_to_main_account is not True:
            raise ValueError("Only linked Accounts Center creation is supported")
        timeout = self.read_timeout
        if type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("read_timeout must be a finite positive number")
        parent_id = str(self.user_id or "")
        parent_auth = self.authorization
        if not parent_id or not parent_auth:
            raise LoginRequired("An authenticated main account is required")

        # Import here to avoid the Client/mixin import cycle. Do not instantiate
        # a potentially stateful user subclass or reuse its transport/cookie jar.
        from instagrapi import Client

        source = self.get_settings()
        keys = (
            "uuids",
            "mid",
            "device_settings",
            "user_agent",
            "country",
            "country_code",
            "locale",
            "timezone_offset",
            "timezone_name",
            "push_disabled",
            "request_timeout",
            "private_transport",
            "public_transport",
            "public_transport_impersonate",
            "tls_verify",
            "usdid",
        )
        settings = deepcopy({k: source[k] for k in keys if k in source})
        settings.update(cookies={}, authorization_data={}, session_retry_total=0)
        worker = Client.__new__(Client)
        stage = "setup"
        submitted = False
        completed = False
        try:
            Client.__init__(worker, settings=settings, proxy=self.proxy, override_app_version=self.override_app_version)
            worker.read_timeout = timeout
            stage = "entry"
            state = worker._caa_initial_state()
            state["waterfall_id"] = str(uuid4())
            entry = {
                "logged_out_user": "",
                "qpl_join_id": str(int(time.time() * 1000)),
                "family_device_id": worker.phone_id,
                "reg_info": json.dumps(
                    {"device_id": worker.android_device_id, "soap_creation_source": "profile_switcher"}
                ),
                "device_id": worker.android_device_id,
                "offline_experiment_group": "caa_iteration_v3_perf_ig_4",
                "waterfall_id": state["waterfall_id"],
                "logout_source": "",
                "auth_token": parent_auth,
                "flow_info": json.dumps(FLOW),
                "qe_device_id": worker.uuid,
            }

            def send(name, params, entry_request=False):
                variables = {
                    "params": {
                        "params": json.dumps(params) if entry_request else json.dumps({"params": json.dumps(params)}),
                        "bloks_versioning_id": worker.bloks_versioning_id,
                        "infra_params": {"device_id": worker.uuid},
                        "app_id": APPS[name],
                    },
                    "bk_context": {
                        "is_flipper_enabled": False,
                        "theme_params": [],
                        "debug_tooling_metadata_token": None,  # nosec B105 - absent native field
                    },
                }
                return worker.private_graphql_www_request(
                    f"IGBloksAppRootQuery-{APPS[name]}",
                    variables,
                    client_doc_id=DOC_ID,
                    allow_redirects=False,
                    timeout=worker.read_timeout,
                )

            response = send(stage, entry, entry_request=True)
            for stage in ("username", "optin", "create"):
                servers = continuation(response, stage)
                common = worker._caa_common_client_input(state)
                inputs = {k: common[k] for k in ("aac", "lois_settings", "cloud_trust_token", "network_bssid")}
                if stage == "username":
                    inputs.update({k: common[k] for k in ("device_id", "family_device_id", "qe_device_id")})
                    inputs.update(
                        validation_text=username,
                        zero_balance_state="",
                        si_device_param_network_info=worker._caa_network_info(),
                    )
                elif stage == "optin":
                    inputs["spc_disco_allow_suggestions"] = 1
                else:
                    inputs.update(
                        {
                            "passkey_eligible_device": 0,
                            "ck_error": "",
                            "device_id": worker.android_device_id,
                            "waterfall_id": servers["waterfall_id"],
                            "zero_balance_state": "",
                            "failed_birthday_year_count": "",
                            "headers_last_infra_flow_id": "",
                            "ig_partially_created_account_nonce_expiry": 0,
                            "machine_id": worker.mid or "",
                            "should_ignore_existing_login": 0,
                            "reached_from_tos_screen": 1,
                            "ig_partially_created_account_nonce": "",
                            "has_dismissed_suma_pre_conf": 0,
                            "ck_nonce": "",
                            "force_sessionless_nux_experience": 0,
                            "ig_partially_created_account_user_id": 0,
                            "ck_id": "",
                            "no_contact_perm_email_oauth_token": "",  # nosec B105 - absent native field
                            "encrypted_msisdn": "",
                        }
                    )
                servers["INTERNAL__latency_qpl_instance_id"] = int(time.time() * 1_000_000)
                servers["INTERNAL__latency_qpl_marker_id"] = 36707139
                if stage == "create":
                    submitted = True
                response = send(stage, {"client_input_params": inputs, "server_params": servers})
            user, auth, headers, cookies = registration(response, parent_id, username)
            result_settings = worker.get_settings()
            result_settings.update(authorization_data=auth, cookies=cookies, last_login=time.time())
            for setting, header in (
                ("mid", "ig-set-x-mid"),
                ("ig_u_rur", "ig-set-ig-u-rur"),
                ("ig_www_claim", "x-ig-set-www-claim"),
            ):
                value = headers.get(header)
                if isinstance(value, str):
                    result_settings[setting] = value
            result = SecondaryAccount(user=extract_user_short(user), settings=deepcopy(result_settings))
            completed = True
            return result
        except Exception:
            # Never expose embedded credentials or raw Bloks bodies in errors.
            raise SecondaryAccountError(stage, creation_may_have_succeeded=submitted) from None
        finally:
            errors = []
            for name in ("private", "public", "graphql"):
                session = vars(worker).get(name)
                if session is None:
                    continue
                try:
                    session.close()
                except BaseException as error:
                    # Close every owned session, including after interruption.
                    errors.append(error)
            if completed and errors:
                for error in errors:
                    if not isinstance(error, Exception):
                        raise error
                raise SecondaryAccountError("cleanup", creation_may_have_succeeded=submitted) from None
