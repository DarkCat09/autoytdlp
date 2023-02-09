# Auto YT-DLP
The Bash script which automatically finds links in the clipboard
and downloads video/audio from these URLs using [yt-dlp](https://github.com/yt-dlp/yt-dlp).

Created mainly for downloading music albums from YouTube.

## Requirements
It requires Python 3.7 or newer and `yt-dlp`.  
Additionally, if you want to use `convert.sh`, you'll need to install `ffmpeg`.  
For `id3tag.sh` requirements are `mutagen`, `requests` and `bs4` libraries.

You can run `make deps` to install all requirements,  
or this command:
```bash
pip install -r requirements.txt
```

## Usage: autoytdlp
1. Run the script with `./autoytdlp.sh` or `make run` command.
2. Just copy video links from YouTube or another supported website.
3. Return to the terminal window and press Ctrl+C.
4. Choose which tool will be used for downloading videos:
    - **`yt-dlp` CLI utility** provides much better
    performance and supports many sources.
    - **Piped API client** implementation works slower,
    but all requests are proxied with Piped server.
    Note that Piped works only with YouTube.
5. Enter file format (and instance URL for Piped),
then wait while videos are downloading.

## Usage: convert
// TODO

## Usage: id3tag
// TODO
