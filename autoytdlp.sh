#!/usr/bin/env bash

watching=1
links=()

# -------
# Helpers

getcb () {
    xclip -selection clipboard -o
}

sigint () {
    echo
    if [[ $watching == 1 ]]; then
        watching=0
    else
        echo 'Ctrl+C was pressed'
        echo 'Exit'
        exit 0
    fi
}

ytlink () {
    echo -n "$1" | \
    sed -E 's#^https?://([A-Za-z0-9.-]+/watch\?v=|(yt\.be|youtu\.be)/)([A-Za-z0-9_-]+)|.+#\3#'
}

bold () {
    echo -e "\033[1m$1\033[0m"
}

# ------------------------
# yt-dlp and piped api wrappers

dlwith_piped () {

    bold 'Choose the type of stream: 1.audio or 2.video'
    read -r stream_num
    if [[ $stream_num == 1 ]]; then
        stream='audio'
        maxby='.bitrate'
    else
        stream='video'
        maxby='.width*.height'
    fi

    jqexpr=".${stream}Streams|map(select(.videoOnly==false))|max_by(${maxby})"

    echo
    bold 'Here is an expression for JQ utility.'
    echo 'Press Enter to leave it intact, or type another expression.'
    echo "$jqexpr"
    read -r newexpr
    if [[ $newexpr == "" ]]; then
        :
    else
        jqexpr="$newexpr"
    fi

    echo
    bold 'Started'
    echo

    for link in "${links[@]}"; do

        echo "Parsing link"
        video_id=$(ytlink "$link")

        echo "Requesting URL for $link"
        video_obj=$(curl -sL "https://ytapi.dc09.ru/streams/$video_id" | jq "$jqexpr")

        video_url=$(echo "$video_obj" | jq ".url" | sed s/^\"// | sed s/\"$//)

        video_mime=$(echo "$video_obj" | jq ".mimeType")
        case "$video_mime" in
            "\"audio/mp4\"")
                ext='m4a'
                ;;
            "\"audio/webm\"")
                ext='webm'
                ;;
            "\"video/mp4\"")
                ext='mp4'
                ;;
            "\"video/webm\"")
                ext='webm'
                ;;
            *)
                ext='mp4'
                ;;
        esac

        video_file="./files/${video_id}.${ext}"
        
        echo "Downloading with wget"
        wget -O "$video_file" "$video_url"

        echo
    done
}

dlwith_ytdlp () {

    bold 'Enter the format to download:'
    echo 'Use "b" without quotes for video and audio'
    echo '    "bv" to download only video'
    echo '    "ba" to download only audio'
    echo 'details: https://github.com/yt-dlp/yt-dlp#format-selection'
    read -r format

    echo
    bold 'Started'
    echo

    for link in "${links[@]}"; do

        video_id=$(ytlink "$link")
        if [[ $video_id != "" ]]; then
            # Convert YT and Piped links to YT
            newlink="https://youtube.com/watch?v=$video_id"
        else
            newlink="$link"
        fi

        echo "URL: $newlink"

        yt-dlp -f "$format" -o "%(id)s.%(ext)s" -P ./files/ "$newlink"
    done
}

# ---------
# Functions

# A title and a small manual
title () {
    echo
    echo -ne '\033[1m'
    echo -ne '***'
    echo -ne '\033[1;34m'
    echo -ne ' Auto YT-DLP Script '
    echo -ne '\033[0m\033[1m'
    echo -ne '***'
    echo -e  '\033[0m'
}

usage () {
    echo 'Copy video links to the clipboard,'
    echo 'the script will automatically'
    echo 'detect them.'
    echo 'Then press Ctrl+C'
    echo 'to stop clipboard watcher.'
    echo
}

# Watching for the clipboard content
watch () {
    prev=$(getcb)
    while [[ $watching == 1 ]]; do
        cb=$(getcb)
        if [[ "$cb" != "$prev" ]]; then
            prev="$cb"
            if [[ "$cb" =~ ^https?:// ]]; then
                links+=("$cb")
                echo "Found link: $cb"
            fi
        fi
        sleep 0.01
    done
}

# ----
# Main

main() {
    # Setup
    trap 'sigint' SIGINT

    # Some info
    title
    usage

    # Clipboard watching
    watch

    # Create a directory for downloaded files
    mkdir -p ./files

    # Ask for downloading method
    bold 'The script can work with 1.yt-dlp and 2.Piped API'
    echo -n 'Which one you prefer? (1 or 2) '
    read -r downloader
    echo
    if [[ $downloader == 2 ]]; then
        dlwith_piped
    else
        dlwith_ytdlp
    fi

    # Waiting for the response
    echo 'Press Ctrl+C to exit'
    while true; do :; done
}

main
