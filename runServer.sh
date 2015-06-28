#!/bin/sh
if [ ! -d "venv" ]; then
    ./prepare-venv.sh
fi
. ./venv/bin/activate
./coap2xively.py
deactivate
