#!/usr/bin/env bash

set -eo pipefail

push_gh_pages() {
  local attempt
  for attempt in 1 2 3; do
    echo "git push origin gh-pages (attempt ${attempt}/3)"
    if git push origin gh-pages; then
      return 0
    fi
    if [[ "${attempt}" == "3" ]]; then
      break
    fi
    sleep $((attempt * 10))
  done
  return 1
}

echo "::group::Configure Git User"
"${GITHUB_ACTION_PATH}/configure_git_user.sh"
echo "::endgroup::"

echo "::group::Pull down latest docs commit"
if git ls-remote --exit-code --heads origin gh-pages >/dev/null 2>&1; then
  git fetch --no-tags --prune --progress --no-recurse-submodules --depth=1 origin gh-pages
else
  echo "gh-pages branch does not exist yet; publishing docs will initialize it."
fi
echo "::endgroup::"

echo "::group::Publish documentation"
if [[ "${NEW_VERSION}" == "false" ]]; then
  if [[ "${VERSION_NAME}" == "" ]]; then
    echo "::error::'version_name' must be specified when 'NEW_VERSION' is false."
    exit 1
  fi
  echo "mike deploy \"${VERSION_NAME}\""
  mike deploy "${VERSION_NAME}"
elif [[ "${GITHUB_EVENT_NAME:-}" != "release" ]]; then
  echo "::error::new_version can only be used for release events."
  exit 1
else
  # drop leading "v" from tag name to have just the version number
  "${GITHUB_ACTION_PATH}/update_docs_for_version.sh" "${RELEASE_TAG:1}"
fi
push_gh_pages
echo "::endgroup::"
