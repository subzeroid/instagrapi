set -euo pipefail

MODULE_NAME=$1
WHEEL_LOCATION=$2

echo "Ensuring pip is up to date"
python -m pip install --upgrade pip

APP_DIR=$(pwd)

# move into root dir so Python will import the installed package instead of the local source files
cd /
echo "------------------"
echo "Installing package"
pip install ${APP_DIR}/${WHEEL_LOCATION}/*.whl

echo "-----------------------------"
echo "Attempting to import package"
python "${GITHUB_ACTION_PATH}/test_module_import.py" "${MODULE_NAME}"
