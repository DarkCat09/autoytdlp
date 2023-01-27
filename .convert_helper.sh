#!/usr/bin/env bash
ffmpeg -i "$1" "$(echo "$1" | sed -E "s/\.[A-Za-z0-9]+$/.$2/" | sed "s#\./files#./convert#")"
