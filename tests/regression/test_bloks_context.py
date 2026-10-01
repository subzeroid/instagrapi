import copy
import json

import pytest

from instagrapi.mixins.bloks import BloksMixin

ENTRYPOINT = "com.bloks.www.two_step_verification.entrypoint"


def result_for(parameters, app_id=ENTRYPOINT, container="action"):
    program = f'"{app_id}" {parameters}'
    return {"layout": {"bloks_payload": {container: program}}}


def context_map(value='"expected-context"'):
    return f'(f4i (dkc "two_step_verification_context") (dkc {value}))'


@pytest.mark.parametrize("prefix", ['"device"', "false", "42", "null", '(f6m 0 "dynamic")'])
def test_two_step_context_preserves_value_positions(prefix):
    result = result_for(
        '(f4i (dkc "device_id" "two_step_verification_context" "flow_source") '
        f'(dkc {prefix} "expected-context" "wrong-context"))'
    )
    before = copy.deepcopy(result)
    assert BloksMixin().bloks_extract_two_step_verification_context(result) == "expected-context"
    assert result == before


@pytest.mark.parametrize("value", ["false", "42", "null", '(f6m 0 "wrong-context")'])
def test_two_step_context_rejects_non_literal_values(value):
    result = result_for(f'(f4i (dkc "two_step_verification_context" "device_id") (dkc {value} "wrong-context"))')
    assert BloksMixin().bloks_extract_two_step_verification_context(result) == ""


@pytest.mark.parametrize("client_first", [False, True])
def test_two_step_context_uses_only_static_server_parameters(client_first):
    client = context_map('"wrong-context"')
    server = context_map()
    keys = '"client_input_params" "server_params"' if client_first else '"server_params" "client_input_params"'
    values = f"{client} {server}" if client_first else f"{server} {client}"
    result = result_for(f"(f4i (dkc {keys}) (dkc {values}))")
    assert BloksMixin().bloks_extract_two_step_verification_context(result) == "expected-context"


@pytest.mark.parametrize("value", [f"(f6m 0 {context_map()})", json.dumps(context_map())])
def test_two_step_context_does_not_evaluate_server_parameters(value):
    result = result_for(f'(f4i (dkc "server_params") (dkc {value}))')
    assert BloksMixin().bloks_extract_two_step_verification_context(result) == ""


def test_two_step_context_ignores_earlier_unrelated_map():
    foreign = context_map('"wrong-context"')
    program = f'"com.bloks.www.unrelated.action" {foreign} '
    program += f'"{ENTRYPOINT}" {context_map()}'
    result = {"layout": {"bloks_payload": {"action": program}}}
    assert BloksMixin().bloks_extract_two_step_verification_context(result) == "expected-context"


@pytest.mark.parametrize("suffix", ["_help", ".async", "2"])
def test_context_extractors_require_exact_app_id(suffix):
    client = BloksMixin()
    result = result_for(context_map(), app_id=ENTRYPOINT + suffix)
    assert client.bloks_extract_two_step_verification_context(result) == ""
    profile = result_for('(f4i (dkc "context_data") (dkc "wrong-context"))', app_id=ENTRYPOINT + suffix)
    assert client.bloks_extract_context_data(profile, ENTRYPOINT) == ""


def test_two_step_context_does_not_borrow_later_app_map():
    result = result_for(f'(noop) "com.bloks.www.unrelated.action" {context_map()}')
    assert BloksMixin().bloks_extract_two_step_verification_context(result) == ""


def test_two_step_context_decodes_escapes():
    expected = 'context-with-"quotes"-and-\\slashes)'
    result = result_for(context_map(json.dumps(expected)))
    assert BloksMixin().bloks_extract_two_step_verification_context(result) == expected


@pytest.mark.parametrize(
    "parameters",
    [
        '(f4i (dkc "two_step_verification_context" "device_id") (dkc "wrong-context"))',
        '(f4i (dkc "two_step_verification_context") (dkc "wrong-context" "extra"))',
        '(f4i (dkc "two_step_verification_context") (dkc "wrong-context")',
    ],
)
def test_two_step_context_rejects_malformed_maps(parameters):
    assert BloksMixin().bloks_extract_two_step_verification_context(result_for(parameters)) == ""


@pytest.mark.parametrize(
    "result",
    [
        {},
        {"layout": {"bloks_payload": {"action": 42}}},
        result_for(context_map(), app_id="com.bloks.www.unrelated.action"),
    ],
)
def test_two_step_context_requires_matching_navigation(result):
    assert BloksMixin().bloks_extract_two_step_verification_context(result) == ""


@pytest.mark.parametrize(
    "result",
    [
        {"two_step_verification_context": "  expected-context  "},
        {"nested": [{"two_step_verification_context": "expected-context"}]},
        {"encoded": '{"two_step_verification_context": "expected-context"}'},
    ],
)
def test_two_step_context_preserves_json_fallback(result):
    assert BloksMixin().bloks_extract_two_step_verification_context(result) == "expected-context"


def test_two_step_context_does_not_use_template_only_app_mentions():
    result = result_for(context_map(), container="ft")
    result["layout"]["bloks_payload"]["ft"] = {"template": result["layout"]["bloks_payload"]["ft"]}
    assert BloksMixin().bloks_extract_two_step_verification_context(result) == ""


@pytest.mark.parametrize("reference", [f'"prefix-{ENTRYPOINT}"', ENTRYPOINT])
def test_context_extractors_reject_non_exact_app_literals(reference):
    result = {"layout": {"bloks_payload": {"action": f"{reference} {context_map()}"}}}
    assert BloksMixin().bloks_extract_two_step_verification_context(result) == ""
    result["layout"]["bloks_payload"]["action"] = f'{reference} (f4i (dkc "context_data") (dkc "wrong-context"))'
    assert BloksMixin().bloks_extract_context_data(result, ENTRYPOINT) == ""
