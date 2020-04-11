#!/bin/sh

exec xvfb-run -a --server-args='-screen 0 1920x5760x24' "$(dirname "$0")"/main.py
