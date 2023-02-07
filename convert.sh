#!/usr/bin/env bash

trap 'echo; echo "Exit"; exit 0' SIGINT
mkdir -p ./convert

echo "Enter input files extension:"
echo "(empty string to match all)"
read -r ext_input
ext_input="${ext_input:-*}"

echo "Enter output files extension:"
echo "(must not be empty)"
read -r ext_output

find ./files -type f -name "*.$ext_input" -exec \
bash ./.convert_helper.sh {} "$ext_output" \;
