set -euo pipefail

retry_pip_install() {
  local attempts=${1}
  shift
  local try=1

  until python -m pip install "$@"; do
    if [[ ${try} -ge ${attempts} ]]; then
      return 1
    fi
    echo "pip install failed, retrying (${try}/${attempts})..."
    try=$((try + 1))
    sleep 2
  done
}

echo "Ensuring pip is up to date"
retry_pip_install 3 --upgrade pip

if [[ "${INSTALL_REQUIREMENTS}" == "true"  ]]; then
  echo "Installing code requirements"
  retry_pip_install 3 -r requirements.txt
fi

if [[ "${INSTALL_TEST_REQUIREMENTS}" == "true"  ]]; then
  echo "Installing test requirements"
  retry_pip_install 3 -r requirements-test.txt
fi
