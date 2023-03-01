#!/usr/bin/env python3

import os
import sys
import shutil
from pathlib import Path

import logging

import mimetypes
import subprocess

from typing import TypedDict
from typing import Optional, Any

import re

import requests
from bs4 import BeautifulSoup  # type: ignore

from mutagen.id3 import ID3  # type: ignore
from mutagen.id3 import TPE1, TIT2, TALB
from mutagen.id3 import TYER, TRCK
from mutagen.id3 import USLT, APIC

BASEURL = 'https://www.azlyrics.com'
USERAGENT = (
    'Mozilla/5.0 (X11; Linux x86_64; rv:109.0) '
    'Gecko/20100101 Firefox/110.0'
)

LYRICS_ROW = '.main-page>.row>.col-xs-12'

safename_re = re.compile(
    r'[^A-Za-z0-9А-ЯЁа-яё \'".,()\[\]&!#$@_~=*+-]'
)

session = requests.Session()
session.headers['User-Agent'] = USERAGENT


class ParseResult(TypedDict):
    title: str
    artist: str
    album: str
    year: int
    track_no: int
    tracks: int
    lyrics: str
    cover: Optional[bytes]
    cover_mime: Optional[str]


class ParseError(Exception):

    EDIT = 'edit'

    def __init__(self, parsing_obj: str) -> None:

        super().__init__(
            f'Unable to parse {parsing_obj}'
        )
        self.parsing_obj = parsing_obj


parsed = ParseResult(
    title='', artist='',
    album='', year=0,
    track_no=0, tracks=0,
    lyrics='',
    cover=None,
    cover_mime=None,
)


def main() -> None:

    global parsed

    copy = int(sys.argv[1]) == 1
    file = sys.argv[2]

    title = conv_title(file)
    print(
        'Enter new title to correct it, '
        'or press Enter to continue',
        '"!--" without quotes means that '
        'you want to enter info and lyrics manually',
        sep='\n',
    )
    print('Title:', title)
    correct = input().strip()

    if correct == '!--':
        manual_info_input()

    else:

        if correct != '':
            title = correct.lower()

        try:
            url = search_azurl(title)
            print(url)
            parse_azlyrics(url)

        except Exception as err:

            print(err)

            # pylint: disable=no-member
            if isinstance(err, ParseError) \
                    and err.parsing_obj == ParseError.EDIT:
                pass
            # pylint: enable=no-member

            else:
                print(
                    'In most cases, this error means that '
                    'the script have received some incorrect data, '
                    'so you should enter song info manually.'
                )

            manual_info_input(False)

    tagmp3(file, copy)


# pylint: disable=redefined-builtin
def input(msg: str = '', def_: Any = '') -> str:

    subprocess.call(
        (
            f'read -e -r -i "{def_}" -p "{msg}" input; '
            'echo -n "$input" >./input'
        ),
        shell=True,
        executable='bash',
    )

    try:
        with open('./input', 'rt', encoding='utf-8') as f:
            return f.read() \
                .removesuffix('\n') \
                .removesuffix('\r')
    except Exception:
        return def_
# pylint: enable=redefined-builtin


def input_num(msg: str, def_: int = 0) -> int:

    try:
        return int(input(msg, def_))
    except ValueError:
        return def_


def safename(value: str) -> str:

    return safename_re.sub(' ', value)


def conv_title(file: str) -> str:

    # Remove file path
    title = file \
        .replace('./convert/', '') \
        .replace('./files/', '')

    # Remove a YT ID and an extension
    title = re.sub(
        r'-{3}[\w_-]*\.[\w_-]*',
        '', title,
    )

    # Remove "(Official Audio)"
    title = re.sub(
        r'\(.*\)',
        '', title,
    )

    # underscore -> space
    title = title \
        .replace('_', ' ') \
        .strip() \
        .lower()

    return title


def search_azurl(title: str) -> str:

    print('Searching...')

    page = session.get(
        'https://searx.dc09.ru/search',
        params={  # type: ignore
            'q': f'{title} site:azlyrics.com',
            'language': 'ru-RU',
            'safesearch': 0,
        },
    )

    soup = BeautifulSoup(page.text, 'html.parser')
    link = soup.select_one(
        'div#urls>article>h3>a'
        '[href*="azlyrics.com/lyrics/"]'
    )

    if link is None:
        raise ParseError('song URL')

    return str(link.get('href'))


def parse_azlyrics(link: str) -> None:

    global parsed

    print('Please wait...')

    page = session.get(link)
    soup = BeautifulSoup(page.text, 'html.parser')

    lyrics = soup.select_one(
        f'{LYRICS_ROW}>div'
        ':not(.div-share)'
        ':not(.lyricsh)'
        ':not(.ringtone)'
    )
    if lyrics is None:
        raise ParseError('song lyrics')
    parsed['lyrics'] = lyrics.get_text().strip()

    lyrics_file = Path('.') / 'lyrics.txt'
    with lyrics_file.open('wt', encoding='utf-8') as f:
        f.write(parsed['lyrics'])

    title_elem = soup.select_one(f'{LYRICS_ROW}>b')
    if title_elem is None:
        raise ParseError('song title')
    parsed['title'] = title_elem.get_text().strip('" ')

    artist_elem = soup.select_one(f'{LYRICS_ROW}>.lyricsh>h2')
    if artist_elem is None:
        raise ParseError('artist name')
    parsed['artist'] = artist_elem.get_text() \
        .removesuffix(' Lyrics') \
        .strip()

    album_blocks = soup.select('.songinalbum_title')
    album = None

    if len(album_blocks) > 1:
        album = album_blocks[-2]
    elif len(album_blocks) > 0:
        album = album_blocks[0]
    else:
        raise ParseError('album name')

    album_re = re.search(
        r'album:\s*"(.+?)"\s*\((\d+)\)',
        album.get_text()
    )
    if album_re is None:
        raise ParseError('album name')

    parsed['album'] = album_re[1]
    parsed['year'] = int(album_re[2])

    cover = album.select_one('img.album-image')

    if cover is not None:

        cover_url = str(cover.get('src'))
        if cover_url.startswith('/'):
            cover_url = BASEURL + cover_url

        req = session.get(cover_url)
        parsed['cover'] = req.content
        parsed['cover_mime'] = req.headers.get(
            'Content-Type', 'image/jpeg'
        )

    tracklist_elem = soup.select_one('.songlist-panel')
    if tracklist_elem is not None:

        tracklist = tracklist_elem.select(
            '.listalbum-item'
        )
        parsed['tracks'] = len(tracklist)

        current_url = re.search(
            r'/(lyrics/.+?\.html)',
            link,
        )

        parsed['track_no'] = 0
        if current_url is not None:
            for i, track in enumerate(tracklist):

                track_url = track.select_one('a')
                if track_url is None:
                    continue

                track_href = str(track_url.get('href'))
                if current_url[0] in track_href:
                    parsed['track_no'] = (i + 1)
                    break

    print('Succesfully parsed')
    print('Title:', parsed['title'])
    print('Artist:', parsed['artist'])
    print('Album:', parsed['album'])
    print('Track:', parsed['track_no'], '/', parsed['tracks'])
    print('Correct something?')

    if input('[y/N] ').lower() == 'y':
        print('Raising ParseError')  # <-- TODO
        raise ParseError(ParseError.EDIT)

    print()


def manual_info_input(overwrite_lyrics: bool = True) -> None:

    global parsed

    parsed['title'] = input('Song title: ', parsed['title'])
    parsed['artist'] = input('Artist name: ', parsed['artist'])
    parsed['album'] = input('Album name: ', parsed['album'])
    parsed['year'] = input_num('Release year: ', parsed['year'])
    parsed['track_no'] = input_num('Track #', parsed['track_no'])
    parsed['tracks'] = input_num('Tracks in album: ', parsed['tracks'])

    editor = os.getenv('EDITOR', 'nano')
    print('Now, paste the lyrics into a text editor')
    print(f'Default editor: {editor}')
    print('Enter another or press Enter to continue')
    other_editor = input().strip()

    if other_editor != '':
        editor = other_editor

    try:
        lyrics_file = Path('.') / 'lyrics.txt'

        if overwrite_lyrics or not lyrics_file.exists():
            with lyrics_file.open('wt') as f:
                f.write('\n')

        subprocess.call([
            editor,
            lyrics_file,
        ])

        print('Reading file...')
        with open('lyrics.txt', 'rt', encoding='utf-8') as f:
            parsed['lyrics'] = f.read().strip()
        print('Done')

    except OSError as err:
        logging.exception(err)

    cover = input('Insert an album cover? [Y/n] ')
    if cover.lower() != 'n':
        try:
            print(
                'Download the cover and enter its path:',
                '(relative path is not recommended)',
                sep='\n',
            )
            cover_file = Path(input().strip())

            with cover_file.open('rb') as f:
                parsed['cover'] = f.read()

            parsed['cover_mime'] = (
                mimetypes.guess_type(cover_file)[0]
                or 'image/jpeg'
            )
        except Exception as err:
            logging.exception(err)

    print()


def tagmp3(
        file: str,
        copy: bool) -> None:

    global parsed

    oldpath = Path(file)
    newpath = oldpath

    if copy:

        newdir = (
            Path('./tagged') /
            safename(parsed['artist']) /
            safename(parsed['album'])
        )
        os.makedirs(newdir, exist_ok=True)

        newpath = newdir / safename(
            f"{parsed['track_no']}. " +
            f"{parsed['title']}.mp3"
        )
        shutil.copy(oldpath, newpath)

        if parsed['cover'] is not None:

            ext = mimetypes.guess_extension(
                parsed['cover_mime'] or ''
            ) or '.jpg'

            cover = newdir / f'cover{ext}'
            with cover.open('wb') as f:
                f.write(parsed['cover'])

    id3 = ID3(str(newpath))
    id3['TPE1'] = TPE1(text=parsed['artist'])
    id3['TIT2'] = TIT2(text=parsed['title'])
    id3['TALB'] = TALB(text=parsed['album'])
    id3['TYER'] = TYER(text=f"{parsed['year']}")
    id3['TRCK'] = TRCK(
        text=(
            f"{parsed['track_no']}/"
            f"{parsed['tracks']}"
        )
    )
    id3['USLT'] = USLT(text=parsed['lyrics'])
    if parsed['cover'] is not None:
        id3['APIC'] = APIC(
            data=parsed['cover'],
            mime=parsed['cover_mime'],
        )
    id3.save()


if __name__ == '__main__':
    main()
