#!/usr/bin/env bash

ask () {
    read -r -p "[Y/n] " answer
    if [[ $answer =~ [NnНн] ]]; then
        echo 0
    else
        echo 1
    fi
}

echo "Enter directory where your music is located:"
read -e -r -i "./convert" directory
directory="${directory:-./convert}"

echo
echo "Copy files into ./tagged/artist/album directory?"
copy_arg=$(ask)
echo

find "$directory" -type f -name "*.mp3" -exec \
python3 ./.id3tag_helper.py "$copy_arg" {} \;
