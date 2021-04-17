#!/usr/bin/env bash

set -euo pipefail

NO_REPLY_SUFFIX="@users.noreply.github.com"

function set_and_exit() {
  local name="${USER_NAME:-$1}"
  local email="${USER_EMAIL:-$2}"
  git config --local user.name "${name}"
  git config --local user.email "${email}"
  exit 0
}

function json_query() {
  jq -e "${1}" "${GITHUB_EVENT_PATH}"
}

if [[ "${USER_NAME}" != "" && "${USER_EMAIL}" != "" ]]; then
  set_and_exit
fi

echo "::debug::Attempting push event pusher"
if json_query ".push.pusher" > /dev/null ; then
  echo "::debug::Found push event pusher"
  set_and_exit "$(json_query '.push.pusher.name')" "$(json_query '.push.pusher.email')"
fi

echo "::debug::Attempting merge merged by"
if json_query ".pull_request.merged_by" > /dev/null ; then
  echo "::debug::Found pull request event merged by"
  LOGIN="$(json_query '.pull_request.merged_by.login')"
  set_and_exit "${LOGIN}" "${LOGIN}${NO_REPLY_SUFFIX}"
fi

echo "::debug::Attempting event sender"
if json_query ".sender" > /dev/null ; then
  echo "::debug::Found pull event sender"
  LOGIN="$(json_query '.sender.login')"
  set_and_exit "${LOGIN}" "${LOGIN}${NO_REPLY_SUFFIX}"
fi

echo "::debug::Falling back to GITHUB_ACTOR"
LOGIN="${GITHUB_ACTOR:-github_action}"
set_and_exit "${LOGIN}" "${LOGIN}${NO_REPLY_SUFFIX}"