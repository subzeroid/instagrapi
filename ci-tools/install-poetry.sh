pip install pipx==1.1.0
pipx install poetry==1.4.2
ln -s /root/.local/bin/poetry /usr/local/bin/
poetry config virtualenvs.create false
python -m venv /venv/  # create an empty venv
echo "source /venv/bin/activate" >> /root/.bashrc  # use it by default
