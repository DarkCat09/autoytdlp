#!/usr/bin/env bash
# Should not be called manually

conv_title () {
    echo "$1" | \
    # remove directory name
    sed -E 's#\./(convert|files)/##' | \
    # remove video ID and ext
    sed 's/---[A-Za-z0-9_-]*\.[A-Za-z0-9]*//' | \
    # underscore -> space
    sed 's/_/ /g' | \
    # remove "(Official Audio)"
    sed -E 's/\(.*\)//' | \
    # trim spaces
    xargs
}

rm_quotes () {
    cat | sed 's/^"//' | sed 's/"$//'
}

title=$(conv_title "$2")
title_prev="$title"

echo 'Correct the song title if needed:'
read -e -r -i "$title" title
title=${title:-$title_prev}

echo 'Searching on Genius'

link="https://genius.com/api/search/multi?q=${title// /%20}"
echo "URL: $link"

song=$(curl -sL "$link" | jq '.response.sections[1].hits[0].result')
title=$(echo "$song" | jq '.title' | rm_quotes)
artist=$(echo "$song" | jq '.primary_artist.name' | rm_quotes)
year=$(echo "$song" | jq '.release_date_components.year')
page_url=$(echo "$song" | jq '.url' | rm_quotes)

echo "Title: $title"
echo "Artist: $artist"
echo "Lyrics: $page_url"

echo 'Parsing lyrics page'

page=$(curl -sL "$page_url")
album=$(echo "$page" | pup -p 'a[class^="PrimaryAlbum__Title"] text{}' | sed -E 's#\([0-9]+\)$##' | xargs)
tracknum=$(echo "$page" | pup -p 'div[class^="HeaderTracklist__AlbumWrapper"]' | grep -oE 'Track [0-9]+' | grep -oE '[0-9]+')
trackall=$(echo "$page" | pup -p 'ol[class^="AlbumTracklist__Container"] > li:last-child div[class^="AlbumTracklist__TrackNumber"] text{}' | grep -oE '[0-9]+')
lyrics=$(echo "$page" | pup -p 'div[data-lyrics-container="true"] text{}' | sed 's#^\[#\n[#')

# remove first blank line
if [[ $(echo "$lyrics" | sed -n '1p') == "" ]]; then
    lyrics=$(echo "$lyrics" | sed '1d')
fi

echo "Album: $album"

if [[ $1 == 1 ]]; then
    newdir="./tagged/${artist}/${album}"
    mkdir -p "$newdir"
    newpath="${newdir}/${tracknum}. ${title}.mp3"
    echo "Copying to $newpath"
    cp -f "$2" "$newpath"
else
    newpath="$2"
fi

echo
echo "$lyrics"
echo

echo 'Adding ID3v2 tags'
mid3v2 \
--artist "$artist" \
--album "$album" \
--song "$title" \
--year "$year" \
--track "${tracknum}/${trackall}" \
--USLT "$lyrics" \
"$newpath"
