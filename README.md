# PostShow v3

This is the third iteration of the XBN Studios post-show encoding/tagging tool. 
Because our network is expanding and adding more hosts, “just run this Python script
that only works on *nix-alikes” was becoming untenable. This version of the script is
now a full-fledged application that works on macOS, Windows, and Linux (untested).

It uses Qt 6 (through PySide 6) as a UI library, and does not specify a style, so that
it kinda looks at home on every platform.  Kinda.

## Features

* Encode WAV recording to MP3 using LAME
* Tag encoded file using standardized tags, for episode file consistency
* Add MP3 chapters to encoded file
  * Chapter images not supported (yet)
  * Chapter URLs not supported (yet)
* Convenient copy buttons for MP3 file size & duration (for pasting into your CMS)
* Creates MP3 files that can be properly seeked/skipped by all tested players

## Anti-Features

* AAC support ([basically only Anchor](https://blubrry.com/podcast-insider/2019/12/09/podcast-stats-soundbites-mp3-vs-m4a/) uses AAC podcasts, and MP3 is no longer patent 
  encumbered)
* Chapter position editing on a timeline view (other tools are better suited for this, 
  like Audacity, Reaper, etc.)
* Apple Notarization (I love macOS, but I don't want to throw $99/year at Apple's 
  increasingly hostile Developer Program)

## Things Not Implemented Yet / Known Bugs
* If your MP3 file is small (or your computer is fast), the encoder can finish 
  before you finish reviewing the metadata screen, and then it locks you out of 
  editing the metadata.
* Chapter images
* Chapter URLs

## Building

1. Obtain LAME from somewhere (Homebrew, [RareWares](https://www.rarewares.org/mp3-lame-bundle.php), compiling it yourself) and put it in `vendor/`
2. Copy `PostShow Icon.ico` to `dist/PostShow/PostShow.ico`
3. On Windows, `poetry run pyinstaller Windows.spec`
4. `candle.exe PostShow.wxs`
5. `cd dist\PostShow`
6. `light.exe ..\..\PostShow.wixobj`
7. `mv dist dist-win`
8. On macOS, `poetry run pyinstaller macOS.spec`