#!/usr/bin/env bash

debug=1
watching=1
links=()
success=0
error=0

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

safename () {
    safe="${1//[^A-Za-z0-9А-ЯЁа-яё ().,_-]/_}"
    echo "${safe// /_}" | sed -E 's/_+/_/'
}

bold () {
    echo -e "\033[1m$1\033[0m"
}

# ------------------------
# yt-dlp and piped api wrappers

dlwith_piped () {

    bold 'Enter Piped API instance URL'
    bold '(ytapi.dc09.ru is used by default)'
    read -r pipedurl
    pipedurl="${pipedurl:-ytapi.dc09.ru}"
    pipedurl=$(echo "$pipedurl" | sed -E 's#https?://##')

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
    bold 'Here is an expression for JQ utility'
    echo 'Correct it or just press Enter'
    read -e -r -i "$jqexpr" newexpr
    jqexpr="${newexpr:-$jqexpr}"

    echo
    bold 'Started'
    echo

    for link in "${links[@]}"; do

        echo "Parsing link"
        video_id=$(ytlink "$link")

        if [[ $video_id == "" ]]; then
            echo 'Unable to parse YT video ID, skipping'
            continue
        fi
        echo "Found YT video ID: $video_id"

        echo "Requesting URL for $link"
        video_obj=$(curl -sL "https://$pipedurl/streams/$video_id")

        stream_obj=$(echo "$video_obj" | jq "$jqexpr")
        stream_url=$(echo "$stream_obj" | jq ".url" | sed s/^\"// | sed s/\"$//)

        stream_mime=$(echo "$stream_obj" | jq ".mimeType")
        case "$stream_mime" in
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

        video_title=$(echo "$video_obj" | jq ".title")
        video_file="./files/$(safename "$video_title").${ext}"
        echo "Filename: $video_file"

        if [[ $debug == 1 ]]
        then continue
        fi
        
        echo "Downloading with wget"

        if wget -O "$video_file" "$stream_url"
        then
            bold "OK"
            success=$(( success + 1 ))
        else
            bold "Error"
            error=$(( error + 1 ))
        fi

        echo
    done
}

dlwith_ytdlp () {

    bold 'Enter the format to download:'
    echo 'Use "b" without quotes for video and audio'
    echo '    "bv" to download only video'
    echo '    "ba" to download only audio'
    echo 'Defaults to "b" if an empty string is passed'
    echo 'Details: https://github.com/yt-dlp/yt-dlp#format-selection'
    read -e -r format
    format="${format:-b}"

    echo
    bold 'Started'
    echo

    for link in "${links[@]}"; do

        video_id=$(ytlink "$link")
        if [[ $video_id != "" ]]; then
            # Convert YT and Piped links to YT
            echo "Found YT video ID: $video_id"
            newlink="https://youtube.com/watch?v=$video_id"
        else
            newlink="$link"
        fi
        echo "URL: $newlink"

        echo "Generating safe name for the file"
        video_title=$(yt-dlp --print title "$newlink")
        video_file="$(safename "$video_title")---%(id)s.%(ext)s"
        echo "Template: $video_file"

        if [[ $debug == 1 ]]
        then continue
        fi

        echo "Downloading with yt-dlp"
        
        if yt-dlp -f "$format" -o "$video_file" -P ./files/ "$newlink"
        then
            bold "OK"
            success=$(( success + 1 ))
        else
            bold "Error"
            error=$(( error + 1 ))
        fi

        echo
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

    # Show result
    bold "Downloaded: $success"
    bold "Errors: $error"
    echo

    # Waiting for the response
    echo 'Press Ctrl+C to exit'
    while true; do :; done
}

main
