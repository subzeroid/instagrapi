# protects: Docs commits retain decoded event identities and explicit action inputs.
# fails_when: JSON quotes, ignored inputs, or the wrong push path alter Git identity.
# why_new: No existing regression executes the docs identity helper against real Git.
# seam: none; the real Bash helper, jq, action metadata and temporary Git config are used.
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

ACTION = Path(__file__).resolve().parents[2] / ".github/actions/publish-docs-with-mike"


@unittest.skipUnless(all(shutil.which(tool) for tool in ("bash", "git", "jq")), "Bash, Git and jq are required")
class DocsGitIdentityTestCase(unittest.TestCase):
    def configure_identity(self, event, *, inputs=None, actor="workflow-actor"):
        metadata = yaml.safe_load((ACTION / "action.yml").read_text())
        # Resolve the composite action's simple input bindings, as the runner does.
        provided = {name: spec.get("default", "") for name, spec in metadata["inputs"].items()}
        provided.update(inputs or {})
        env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
        for key in ("USER_NAME", "USER_EMAIL"):
            binding = metadata["runs"]["steps"][0]["env"][key]
            match = re.fullmatch(r"\$\{\{\s*inputs\.(\w+)\s*\}\}", binding)
            self.assertIsNotNone(match, binding)
            env[key] = provided.get(match[1], "")
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            event_path = folder / "event.json"
            event_path.write_text(json.dumps(event))
            env.update(GITHUB_EVENT_PATH=str(event_path), GITHUB_ACTOR=actor)
            subprocess.run(["git", "init", "--quiet", directory], env=env, check=True, capture_output=True)
            subprocess.run(
                ["bash", str(ACTION / "configure_git_user.sh")],
                cwd=folder,
                env=env,
                check=True,
                capture_output=True,
                text=True,
            )
            return tuple(
                subprocess.check_output(
                    ["git", "config", "--local", "--get", key], cwd=folder, env=env, text=True
                ).rstrip("\n")
                for key in ("user.name", "user.email")
            )

    def test_event_identity_selection_and_json_decoding(self):
        cases = [
            (
                {
                    "pusher": {"name": 'Docs "Maintainer" \\ Team', "email": "docs@example.test"},
                    "sender": {"login": "sender"},
                },
                ('Docs "Maintainer" \\ Team', "docs@example.test"),
            ),
            (
                {"pull_request": {"merged_by": {"login": "merger"}}, "sender": {"login": "sender"}},
                ("merger", "merger@users.noreply.github.com"),
            ),
            ({"sender": {"login": "sender"}}, ("sender", "sender@users.noreply.github.com")),
            ({}, ("workflow-actor", "workflow-actor@users.noreply.github.com")),
            (
                {"pusher": {"name": None, "email": "pusher@example.test"}, "sender": {"login": "sender"}},
                ("sender", "sender@users.noreply.github.com"),
            ),
            (
                {"pusher": {"email": "pusher@example.test"}, "sender": {"login": "sender"}},
                ("sender", "sender@users.noreply.github.com"),
            ),
            (
                {"pusher": {"name": "Pusher", "email": None}, "sender": {"login": "sender"}},
                ("sender", "sender@users.noreply.github.com"),
            ),
            (
                {"pusher": {"name": "Pusher"}, "sender": {"login": "sender"}},
                ("sender", "sender@users.noreply.github.com"),
            ),
        ]
        for event, expected in cases:
            with self.subTest(event=event):
                self.assertEqual(self.configure_identity(event), expected)

    def test_declared_action_inputs_override_each_field(self):
        cases = [
            (
                {"commit_user_name": 'Custom "Name"', "commit_user_email": "custom@example.test"},
                ('Custom "Name"', "custom@example.test"),
            ),
            ({"commit_user_name": "Custom Name"}, ("Custom Name", "sender@users.noreply.github.com")),
            ({"commit_user_email": "custom@example.test"}, ("sender", "custom@example.test")),
        ]
        for inputs, expected in cases:
            with self.subTest(inputs=inputs):
                self.assertEqual(self.configure_identity({"sender": {"login": "sender"}}, inputs=inputs), expected)

    def test_empty_actor_uses_existing_default(self):
        self.assertEqual(
            self.configure_identity({}, actor=""), ("github_action", "github_action@users.noreply.github.com")
        )
