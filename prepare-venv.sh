#!/bin/sh

if [ -d "venv" ]; then
    echo "venv already exists. Exit."
    exit
fi

virtualenv venv
. ./venv/bin/activate
echo "Installing in Virtualenv \"$VIRTUAL_ENV\""
pip install twisted txthings

# If the following line causes an error: remove "--pre" and remove the "venv"
# directory
pip install --pre xively-python

deactivate
echo "Done"
