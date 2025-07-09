set -euo pipefail

echo "Ensuring pip is up to date"
python -m pip install --upgrade pip

if [[ "${INSTALL_REQUIREMENTS}" == "true"  ]]; then
  echo "Installing code requirements"
  pip install -r requirements.txt
fi

if [[ "${INSTALL_TEST_REQUIREMENTS}" == "true"  ]]; then
  echo "Installing test requirements"
  pip install -r requirements-test.txt
fi

if [[ "${INSTALL_DOCS_REQUIREMENTS}" == "true"  ]]; then
  echo "Installing docs requirements"
  pip install -r requirements-docs.txt
fi
