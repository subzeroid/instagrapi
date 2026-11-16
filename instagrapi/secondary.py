"""Bounded readers for the additional-profile flow; never execute Bloks code."""

import base64
import json
import re

FLOW = {"flow_type": "spc", "flow_name": "secondary_profile_creation_ig_default"}
DOC_ID = "356548512611906258864738750706"
APPS = {
    "entry": "com.bloks.www.bloks.caa.reg.spc_create_profile.async",
    "username": "com.bloks.www.bloks.caa.reg.username.async",
    "optin": "com.bloks.www.bloks.caa.reg.ac_optin.async",
    "create": "com.bloks.www.bloks.caa.reg.create.account.async",
}
_TOKEN = re.compile(r'\(|\)|"(?:\\.|[^"\\])*"|[^\s()]+')
_MAX_SIZE = 2_000_000


def _json(value):
    return json.loads(value) if isinstance(value, str) else value


def _vm(text):
    root = []
    stack = [root]
    for count, match in enumerate(_TOKEN.finditer(text)):
        if count > 100_000:
            raise ValueError("SPC token limit exceeded")
        symbol = match.group()
        if symbol == "(":
            if len(stack) >= 80:
                raise ValueError("SPC nesting limit exceeded")
            child = []
            stack[-1].append(child)
            stack.append(child)
        elif symbol == ")":
            if len(stack) == 1:
                raise ValueError("Unbalanced SPC payload")
            stack.pop()
        else:
            try:
                value = json.loads(symbol)
            except ValueError:
                value = symbol
            stack[-1].append(value)
    if len(stack) != 1:
        raise ValueError("Unbalanced SPC payload")
    return root


def _walk(value):
    """Expand JSON strings and literal VM syntax within strict resource limits."""
    if len(json.dumps(value)) > _MAX_SIZE:
        raise ValueError("SPC response too large")
    pending = [(value, 0)]
    seen_strings = set()
    count = 0
    expanded_bytes = 0
    while pending:
        item, depth = pending.pop()
        count += 1
        if count > 100_000 or depth > 100:
            raise ValueError("SPC structure limit exceeded")
        yield item
        if isinstance(item, dict):
            pending.extend((v, depth + 1) for v in item.values())
        elif isinstance(item, list):
            pending.extend((v, depth + 1) for v in item)
        elif isinstance(item, str) and item not in seen_strings:
            seen_strings.add(item)
            expanded_bytes += len(item)
            if expanded_bytes > 4 * _MAX_SIZE:
                raise ValueError("SPC expansion limit exceeded")
            stripped = item.strip()
            if stripped.startswith(("{", "[")):
                try:
                    decoded = json.loads(stripped)
                except ValueError:
                    continue
                pending.append((decoded, depth + 1))
            elif re.match(r"\([a-zA-Z0-9_.]+[\s)]", stripped):
                pending.append((_vm(stripped), depth + 1))


def _literal(value):
    if isinstance(value, bool):
        return int(value)
    if value is None or isinstance(value, (str, int, float)):
        return value
    if (
        isinstance(value, list)
        and len(value) == 3
        and value[0] == "f4i"
        and isinstance(value[1], list)
        and isinstance(value[2], list)
        and value[1][:1] == ["dkc"]
        and value[2][:1] == ["dkc"]
    ):
        keys, values = value[1][1:], value[2][1:]
        if len(keys) != len(values) or any(not isinstance(k, str) for k in keys) or len(set(keys)) != len(keys):
            raise ValueError("Malformed SPC literal map")
        return {k: _literal(v) for k, v in zip(keys, values)}
    raise ValueError("Nonliteral SPC continuation")


def continuation(response, stage):
    """Select a unique button transition, keeping its context and reg_info paired."""
    if stage not in ("username", "optin", "create"):
        raise ValueError("Unknown SPC stage")
    candidates = {}
    for item in _walk(response):
        if not isinstance(item, list) or item[:1] != ["f4i"]:
            continue
        try:
            mapping = _literal(item)
        except ValueError:
            continue
        if not isinstance(mapping, dict) or not mapping.get("reg_context"):
            continue
        try:
            if _json(mapping.get("flow_info")) != FLOW or not isinstance(_json(mapping.get("reg_info")), dict):
                continue
        except (ValueError, TypeError):
            continue
        matches = (
            stage == "username"
            and mapping.get("action") == 1
            or stage == "optin"
            and mapping.get("is_tds_reg_flow") == 0
            and "user_opted_out_of_ntp" not in mapping
            or stage == "create"
            and mapping.get("should_ignore_suma_check") == 0
            and mapping.get("app_id") == 0
        )
        if matches and isinstance(mapping["reg_context"], str) and isinstance(mapping.get("reg_info"), str):
            candidates[json.dumps(mapping, sort_keys=True)] = mapping
    if len(candidates) != 1:
        raise ValueError("Missing or ambiguous SPC continuation")
    return next(iter(candidates.values()))


def _root_actions(response):
    """Read only the response's root action, excluding embedded UI templates."""
    if not isinstance(response, dict):
        raise ValueError("Malformed SPC response")
    roots = [response]
    data = response.get("data", {})
    if isinstance(data, dict):
        for item in data.values():
            if not isinstance(item, dict):
                continue
            bundle = item.get("action", {}).get("action_bundle", {}).get("bloks_bundle_action")
            if bundle is not None:
                roots.append(_json(bundle))
    for root in roots:
        if isinstance(root, dict):
            payload = root.get("layout", {}).get("bloks_payload", {})
            action = payload.get("action")
            if isinstance(action, str):
                yield action


def registration(response, parent_id, username):
    """Validate the actual registration result and its embedded session together."""
    if len(json.dumps(response)) > _MAX_SIZE:
        raise ValueError("SPC response too large")
    wrappers = {}
    for action in _root_actions(response):
        for item in _walk(action):
            if isinstance(item, dict) and "registration_response" in item:
                wrappers[json.dumps(item, sort_keys=True)] = item
    if len(wrappers) != 1:
        raise ValueError("Missing or ambiguous SPC registration result")
    wrapper = next(iter(wrappers.values()))
    result = _json(wrapper["registration_response"])
    headers = _json(wrapper.get("headers"))
    if not isinstance(result, dict) or not isinstance(headers, dict):
        raise ValueError("Malformed SPC registration result")
    headers = {k.lower(): v for k, v in headers.items() if isinstance(k, str)}
    user = result.get("created_user")
    if result.get("account_created") is not True or result.get("status") != "ok" or not isinstance(user, dict):
        raise ValueError("SPC creation not confirmed")
    pk = str(user.get("pk") or user.get("id") or "")
    if (
        not pk.isdecimal()
        or int(pk) <= 0
        or pk == str(parent_id)
        or (user.get("id") is not None and str(user["id"]) != pk)
        or user.get("username", "").lower() != username.lower()
    ):
        raise ValueError("SPC returned an unexpected identity")
    authorization = headers.get("ig-set-authorization", "")
    if not isinstance(authorization, str) or not authorization.startswith("Bearer IGT:2:"):
        raise ValueError("Missing SPC authorization")
    try:
        auth = json.loads(base64.b64decode(authorization.removeprefix("Bearer IGT:2:"), validate=True))
    except (ValueError, UnicodeError) as exc:
        raise ValueError("Malformed SPC authorization") from exc
    if (
        not isinstance(auth, dict)
        or str(auth.get("ds_user_id")) != pk
        or not isinstance(auth.get("sessionid"), str)
        or not auth["sessionid"]
    ):
        raise ValueError("SPC authorization identity mismatch")
    # Use credentials from the paired token, not arbitrary cookie attributes in
    # the nested response (whose native representation is not a JSON cookie jar).
    cookies = {"sessionid": auth["sessionid"], "ds_user_id": pk}
    return dict(user, pk=pk), auth, headers, cookies
