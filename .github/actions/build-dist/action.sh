set -euo pipefail

echo "Ensuring pip is up to date"
python -m pip install --upgrade pip
echo "Installing the latest version of pypa/build"
pip install build

python -m build --sdist --wheel --outdir dist/ .
