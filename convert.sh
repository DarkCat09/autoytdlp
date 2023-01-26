#!/usr/bin/env bash

trap 'echo; echo "Exit"; exit 0' SIGINT

echo "Enter input files extension:"
echo "(empty string to match all)"
read -r ext_input

if [[ $ext_input == "" ]]; then
    ext_input="*"
fi

echo "Enter output files extension:"
echo "(must not be empty)"
read -r ext_output

find ./files -type f -name "*.$ext_input" -exec \
bash ./.convert_helper.sh {} "$ext_output" \;
