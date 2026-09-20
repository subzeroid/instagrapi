"""Required live CI must fail when account configuration is unavailable."""

import os
import subprocess
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = REPO_ROOT / ".github/workflows/live-account-tests.yml"
WORKFLOW = yaml.load(WORKFLOW_PATH.read_text(), Loader=yaml.BaseLoader)
LIVE_JOB = WORKFLOW["jobs"]["live-test"]
POOLED_TARGETS = [
    target for target in WORKFLOW["on"]["workflow_dispatch"]["inputs"]["test_target"]["options"] if target != "signup"
]


def run_preflight(tmp_path, target, accounts_url):
    steps = LIVE_JOB["steps"]
    preflight = next((step for step in steps if step.get("name") == "Validate live test configuration"), None)
    assert preflight is not None, "Live CI must reject missing account configuration before tests can skip"
    assert steps[0] is preflight, "Validate before checkout, dependencies, or account tests"
    summary = tmp_path / "summary.md"
    env = dict(os.environ, LIVE_TEST_TARGET=target, GITHUB_STEP_SUMMARY=str(summary))
    env.pop("TEST_ACCOUNTS_URL", None)
    if accounts_url is not None:
        env["TEST_ACCOUNTS_URL"] = accounts_url
    result = subprocess.run(
        ["bash", "--noprofile", "--norc", "-e", "-o", "pipefail", "-c", preflight["run"]],
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
    )
    return result, summary.read_text() if summary.exists() else ""


@pytest.mark.parametrize("target", ["", *POOLED_TARGETS])
@pytest.mark.parametrize("accounts_url", [None, ""])
def test_missing_account_configuration_fails_before_live_tests(tmp_path, target, accounts_url):
    result, summary = run_preflight(tmp_path, target, accounts_url)

    assert result.returncode == 1, result.stdout + result.stderr
    assert "::error::" in result.stdout + result.stderr
    assert "Live validation did not run" in summary
    assert "TEST_ACCOUNTS_URL" in summary
    assert "Configure" in summary


def test_configured_preflight_does_not_expose_account_url_or_claim_live_success(tmp_path):
    accounts_url = "synthetic-private-account-endpoint"
    result, summary = run_preflight(tmp_path, "all", accounts_url)

    assert result.returncode == 0, result.stdout + result.stderr
    assert accounts_url not in result.stdout + result.stderr + summary
    assert "PASS" not in result.stdout + result.stderr + summary


def test_signup_only_does_not_require_an_account_pool(tmp_path):
    result, _ = run_preflight(tmp_path, "signup", None)

    assert result.returncode == 0, result.stdout + result.stderr


def test_preflight_receives_account_secret_and_selected_target():
    assert LIVE_JOB["env"]["TEST_ACCOUNTS_URL"] == "${{ secrets.TEST_ACCOUNTS_URL }}"
    step = LIVE_JOB["steps"][0]
    assert step["env"]["LIVE_TEST_TARGET"] == "${{ github.event.inputs.test_target }}"


def test_live_workflow_remains_manual_only():
    assert list(WORKFLOW["on"]) == ["workflow_dispatch"]
