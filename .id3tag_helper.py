#!/usr/bin/env python3

import os
import sys
import shutil
from pathlib import Path

import logging

import mimetypes
import subprocess

from typing import TypedDict
from typing import Optional

import re

import requests
from bs4 import BeautifulSoup

from mutagen.id3 import ID3
from mutagen.id3 import TPE1, TIT2, TALB
from mutagen.id3 import TYER, TRCK
from mutagen.id3 import USLT, APIC

BASEURL = 'https://www.azlyrics.com'
USERAGENT = (
    'Mozilla/5.0 (X11; Linux x86_64; rv:109.0) '
    'Gecko/20100101 Firefox/110.0'
)

LYRICS_ROW = '.main-page>.row>.col-xs-12'

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

    def __init__(self, parsing_obj: str) -> None:

        super().__init__(
            f'Unable to parse {parsing_obj}'
        )


def main() -> None:

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

    parsed: Optional[ParseResult] = None

    if correct == '!--':
        parsed = manual_info_input()
    else:
        if correct != '':
            title = correct.lower()
        url = search_azurl(title)
        print(url)
        parsed = parse_azlyrics(url)

    #print(parsed)
    tagmp3(file, parsed, copy)


def input_num(msg: str, def_: int = 0) -> int:

    try:
        return int(input(msg))
    except ValueError:
        return def_


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
        params={
            'q': f'{title} site:azlyrics.com',
            'category_general': 1,
            'language': 'ru-RU',
            'time_range': '',
            'safesearch': 0,
            'theme': 'simple',
        },
    )

    soup = BeautifulSoup(page.text, 'html.parser')
    link = soup.select_one(
        'div#urls>article>h3>a[href*="azlyrics.com/lyrics/"]'
    )

    if link is None:
        raise ParseError('song URL')
    
    return str(link.get('href'))


def parse_azlyrics(link: str) -> ParseResult:

    result = ParseResult(
        title='', artist='',
        album='', year=0,
        track_no=0, tracks=0,
        lyrics='',
        cover=None,
        cover_mime=None,
    )

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
    result['lyrics'] = lyrics.get_text().strip()

    artist_elem = soup.select_one(f'{LYRICS_ROW}>.lyricsh>h2')
    if artist_elem is None:
        print('Unable to parse artist name')
        result['artist'] = input('Enter the artist name: ')
    else:
        result['artist'] = artist_elem.get_text() \
            .removesuffix(' Lyrics') \
            .strip()

    title_elem = soup.select_one(f'{LYRICS_ROW}>b')
    if title_elem is None:
        print('Unable to parse song title')
        result['title'] = input('Enter the title: ')
    else:
        result['title'] = title_elem.get_text().strip('" ')

    album_blocks = soup.select('.songinalbum_title')
    album = None

    if len(album_blocks) > 1:
        album = album_blocks[-2]

    elif len(album_blocks) > 0:
        album = album_blocks[0]
    
    if album is None:
        album_re = None
    else:
        album_re = re.search(
            r'album:\s*"(.+?)"\s*\((\d+)\)',
            album.get_text()
        )

    if album_re is None:
        print('Unable to parse album name')
        result['album'] = input('Enter the album name: ')
        result['year'] = input_num('Enter the release year: ')
        result['track_no'] = input_num('This is the track #')
        result['tracks'] = input_num('Number of tracks in the album: ')

        cover = input('Insert an album cover? [Y/n] ')
        if cover.lower() not in ('n','н'):
            try:
                print(
                    'Download the cover and enter its path:',
                    '(relative path is not recommended)',
                    sep='\n',
                )
                cover_file = Path(input().strip())

                with cover_file.open('rb') as f:
                    result['cover'] = f.read()

                result['cover_mime'] = (
                    mimetypes.guess_type(cover_file)[0]
                    or 'image/jpeg'
                )
            except Exception as err:
                logging.exception(err)

    else:
        result['album'] = album_re[1]
        result['year'] = int(album_re[2])

        assert album is not None
        cover = album.select_one('img.album-image')

        if cover is not None:

            cover_url = str(cover.get('src'))
            if cover_url.startswith('/'):
                cover_url = BASEURL + cover_url

            req = session.get(cover_url)
            result['cover'] = req.content
            result['cover_mime'] = req.headers.get(
                'Content-Type', 'image/jpeg'
            )
    
        tracklist_elem = soup.select_one('.songlist-panel')
        if tracklist_elem is not None:

            tracklist = tracklist_elem.select(
                '.listalbum-item'
            )
            result['tracks'] = len(tracklist)

            current_url = re.search(
                r'/(lyrics/.+?\.html)',
                link,
            )

            result['track_no'] = 0
            if current_url is not None:
                for i, track in enumerate(tracklist):

                    track_url = track.select_one('a')
                    if track_url is None:
                        continue

                    track_href = str(track_url.get('href'))
                    if current_url[0] in track_href:
                        result['track_no'] = (i + 1)
                        break

    return result


def manual_info_input() -> ParseResult:

    result = ParseResult(
        title=input('Song title: '),
        artist=input('Artist name: '),
        album=input('Album name: '),
        year=input_num('Release year: '),
        track_no=input_num('Track #'),
        tracks=input_num('Tracks in album: '),
        lyrics='', cover=None, cover_mime=None,
    )

    editor = os.getenv('EDITOR', 'nano')
    print('Now, paste the lyrics into a text editor')
    print(f'Default editor: {editor}')
    print('Enter another or press Enter to continue')
    other_editor = input().strip()

    if other_editor != '':
        editor = other_editor

    try:
        lyrics_file = Path('.') / 'lyrics.txt'
        with lyrics_file.open('wt') as f:
            f.write('\n')

        subprocess.call([
            editor,
            lyrics_file,
        ])

        print('Reading file...')
        with open('lyrics.txt', 'rt', encoding='utf-8') as f:
            result['lyrics'] = f.read().strip()
        print('Done')

    except OSError as err:
        logging.exception(err)

    cover = input('Insert an album cover? [Y/n] ')
    if cover.lower() not in ('n','н'):
        try:
            print(
                'Download the cover and enter its path:',
                '(relative path is not recommended)',
                sep='\n',
            )
            cover_file = Path(input().strip())

            with cover_file.open('rb') as f:
                result['cover'] = f.read()

            result['cover_mime'] = (
                mimetypes.guess_type(cover_file)[0]
                or 'image/jpeg'
            )
        except Exception as err:
            logging.exception(err)
    
    return result


def tagmp3(
        file: str,
        parsed: ParseResult,
        copy: bool) -> None:

    oldpath = Path(file)
    newpath = oldpath
    
    if copy:

        newdir = (
            Path('./tagged') /
            parsed['artist'] /
            parsed['album']
        )
        os.makedirs(newdir, exist_ok=True)

        newpath = newdir / (
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
