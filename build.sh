#!/bin/bash
# installs virtualenv
pip install virtualenv

# set ups virtual environment
virtualenv  --no-site-packages venv

source venv/Scripts/activate

# updates pip
pip install --upgrade setuptools

deactivate

printf '\n\nPress enter to finish'
read -s -n 1