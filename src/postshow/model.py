import math
import csv
import datetime
import re
import threading
import mutagen.id3
import mutagen.mp3
import subprocess
import mimetypes
import os.path


class Chapter(object):
    """A podcast chapter."""

    def __init__(
        self, start: int, end: int, url=None, image=None, text=None, indexed=True
    ):
        """Create a new Chapter.

        :param start: The start time of the chapter, in milliseconds.
        :param end: The end time of the chapter, in milliseconds.
        :param url: An optional URL to include in the chapter.
        :param image: An optional path to an image, which will be read and
        embedded in the chapter.
        :param text: An optional string description of the chapter.
        :param indexed: Whether to include this chapter in the Table of
        Contents.
        """
        self.elem_id = None
        self.text = text
        self.start = start
        self.end = end
        self.url = url
        self.image = image
        self.indexed = indexed

    def __repr__(self):
        """Turn this Chapter into a string."""
        return (
            "Chapter(start={start}, end={end}, url={url}, image={image}, "
            "text={text}, indexed={indexed})"
        ).format(
            start=self.start,
            end=self.end,
            url=self.url if self.url is None else '"' + self.url + '"',
            image=self.image,
            text=self.text if self.text is None else '"' + self.text + '"',
            indexed=self.indexed,
        )

    def as_chap(self) -> mutagen.id3.CHAP:
        """Convert this object into a mutagen CHAP object."""
        sub_frames = []
        if self.text is not None:
            # Fix issue #1 by replacing em-dashes with regular hyphen-minuses
            cleaned_text = self.text.replace("—", "-")
            sub_frames.append(mutagen.id3.TIT2(text=cleaned_text))
        if self.url is not None:
            sub_frames.append(mutagen.id3.WXXX(desc="chapter url", url=self.url))
        if self.image is not None:
            raise NotImplementedError("I haven't done this bit yet.")
        return mutagen.id3.CHAP(
            element_id=self.elem_id,
            start_time=self.start,
            end_time=self.end,
            sub_frames=sub_frames,
        )


class MP3Tagger(threading.Thread):
    """Tag an MP3."""

    def __init__(self):
        """Create a new tagger."""
        super().__init__()
        self.path = None
        self.tag = None
        self.progress_signal = None
        self.length_ms = None

    def setup(self, path: str, progress_signal):
        self.path = path
        self.progress_signal = progress_signal
        # Create an ID3 tag if none exists
        try:
            self.tag = mutagen.id3.ID3(path)
        except mutagen.MutagenError:
            broken = mutagen.id3.ID3FileType(path)
            broken.add_tags(ID3=mutagen.id3.ID3)
            self.tag = broken.ID3()
        # Determine the length of the MP3 and write it to a TLEN frame
        mp3 = mutagen.mp3.MP3(path)
        self.length_ms = int(round(mp3.info.length * 1000, 0))
        self.tag.add(mutagen.id3.TLEN(text=str(self.length_ms)))

    @staticmethod
    def _no_padding(arg):
        return 0

    def run(self) -> None:
        self.tag.save(self.path, v2_version=3, padding=self._no_padding)
        self.progress_signal.progressed.emit(101)

    def set_title(self, title: str) -> None:
        """Set the title of the MP3."""
        self.tag.delall("TIT2")
        self.tag.add(mutagen.id3.TIT2(text=title))

    def set_artist(self, artist: str) -> None:
        """Set the artist of the MP3."""
        self.tag.delall("TPE1")
        self.tag.add(mutagen.id3.TPE1(text=artist))

    def set_album(self, album: str) -> None:
        """Set the album of the MP3."""
        self.tag.delall("TALB")
        self.tag.add(mutagen.id3.TALB(text=album))

    def set_season(self, season: str) -> None:
        """Set the season of the MP3."""
        self.tag.delall("TPOS")
        self.tag.add(mutagen.id3.TPOS(text=season))

    def set_genre(self, genre: str) -> None:
        """Set the genre of the MP3."""
        self.tag.delall("TCON")
        self.tag.add(mutagen.id3.TCON(text=genre))

    def set_composer(self, composer: str) -> None:
        """Set the composer of the MP3."""
        self.tag.delall("TCOM")
        self.tag.add(mutagen.id3.TCOM(text=composer))

    def set_accompaniment(self, accompaniment: str) -> None:
        """Set the accompaniment of the MP3."""
        self.tag.delall("TPE2")
        self.tag.add(mutagen.id3.TPE2(text=accompaniment))

    def set_cover_art(self, path: str):
        """Set the cover art of the MP3."""
        self.tag.delall("APIC")
        mime, ignored = mimetypes.guess_type(path)
        if mime is None:
            raise PostShowError("Unable to guess MIME type of cover image.")
        data = None
        try:
            with open(path, "rb") as fp:
                data = fp.read()
        except IOError:
            raise PostShowError("Unable to read cover image file.")
        apic = mutagen.id3.APIC(
            mime=mime,
            type=mutagen.id3.PictureType.COVER_FRONT,
            desc="podcast cover art",
            data=data,
        )
        self.tag.add(apic)

    def set_date(self, year: str) -> None:
        """Set the date of recording of the MP3."""
        self.tag.delall("TDRC")
        self.tag.add(mutagen.id3.TDRC(text=[mutagen.id3.ID3TimeStamp(year)]))

    def set_trackno(self, trackno: str) -> None:
        """Set the track number of the MP3."""
        self.tag.delall("TRCK")
        self.tag.add(mutagen.id3.TRCK(text=trackno))

    def set_language(self, language: str) -> None:
        """Set the language of the MP3."""
        self.tag.delall("TLAN")
        self.tag.add(mutagen.id3.TLAN(text=language))

    def add_comment(self, lang: str, desc: str, comment: str) -> None:
        """Add a comment to the MP3."""
        self.tag.add(mutagen.id3.COMM(lang=lang, desc=desc, text=[comment]))

    def add_lyrics(self, lang: str, desc: str, lyrics: str) -> None:
        """Add lyrics to the MP3."""
        self.tag.add(mutagen.id3.USLT(lang=lang, desc=desc, text=lyrics))

    def add_chapter(self, chapter: Chapter):
        """Add a chapter to the MP3."""
        self.tag.add(chapter.as_chap())

    def add_chapters(self, chapters: list):
        """Add a whole list of chapters to the MP3."""
        child_element_ids = []
        for chapter in chapters:
            self.add_chapter(chapter)
            if chapter.indexed:
                child_element_ids.append(chapter.elem_id)
        self.tag.add(
            mutagen.id3.CTOC(
                element_id="toc",
                flags=mutagen.id3.CTOCFlags.TOP_LEVEL | mutagen.id3.CTOCFlags.ORDERED,
                child_element_ids=child_element_ids,
                sub_frames=[mutagen.id3.TIT2(text="Primary Chapter List")],
            )
        )


class MP3Encoder(threading.Thread):
    """Shell out to LAME to encode the WAV file as an MP3."""

    def __init__(self):
        super().__init__()
        self.infile = None
        self.outfile = None
        self.bitrate = None
        self.matcher = None
        self.p = None
        self.percent = 0
        self.started = False
        self.finished = False
        self.progress_updater = None

    def setup(self, infile: str, outfile: str, bitrate: str, progress_updater):
        """Configure the input and output files, and the encoder bitrate.

        :param infile: Path to WAV file.
        :param outfile: Path to create MP3 file at.
        :param bitrate: LAME CBR bitrate, in Kbps.
        """
        self.infile = infile
        self.outfile = outfile
        self.bitrate = bitrate
        self.matcher = re.compile(r"\(([0-9]?[0-9 ][0-9])%\)")
        self.progress_updater = progress_updater

    def run(self):
        self.started = True
        basedir = os.path.dirname(__file__)
        lame_path = os.path.join(basedir, "..", "..", "vendor", "lame")
        self.p = subprocess.Popen(
            [lame_path, "-t", "-b", self.bitrate, "--cbr", self.infile, self.outfile],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        for block in iter(lambda: self.p.stderr.read(1024), ""):
            # Stop when the process terminates.
            if self.p.poll() is not None:
                break
            text = block.decode("utf-8")
            groups = self.matcher.findall(text)
            if len(groups) < 1:
                continue
            percent = int(groups[-1])
            self.percent = percent
            self.progress_updater.set_progress(percent)
            if percent == 100 and self.p.poll() is not None:
                break
        self.finished = True
        self.progress_updater.set_finished()

    def request_stop(self):
        if self.started and self.p is not None:
            self.p.terminate()


class EpisodeMetadata(object):
    """Metadata about an episode."""

    def __init__(self, number: str, name: str):
        self.number = number
        self.name = name
        self.lyrics = None
        self.title = None
        self.album = None
        self.artist = None
        self.season = None
        self.genre = None
        self.language = None
        self.composer = None
        self.accompaniment = None
        self.year = None
        self.comment = None
        self.chapters = []
        self.toc = []

    def __getitem__(self, key):
        return self.__getattribute__(key)

    def __setitem__(self, key, value):
        """This is bad, and rest assured that I felt bad writing it."""
        return self.__setattr__(key, value)


class MCS:
    """Marker Conversion Space

    Load markers from a file into an internal representation, which can then
    be output as other formats. Filetype detection for input files is done
    based on the extension. If the extension is wrong, it may cause issues.

    Supported input formats:
    * Audacity labels

    Supported output formats:
    * CUE file
    * LRC file
    * Internal representation (for use in other parts of the program)

    Create a new instance and call ``load('path/to/file.ext')`` on it to load
    the markers, then ``save('path/to/file.ext', TYPE)``, where ``TYPE`` is
    one of the constants on this class:
    * LRC
    * CUE
    """

    AUDACITY = 0
    LRC = 10
    CUE = 11
    UMR = 12
    SIMPLE = 13
    FFMETADATA1 = 14

    def __init__(self, metadata=None, media_filename=None):
        self.load_path = None
        self.metadata = metadata
        self.media_filename = (
            media_filename
            if media_filename is None
            else os.path.basename(media_filename)
        )
        self.chapters = []

    def _canonicalize(self) -> None:
        """Set the element ID for each chapter."""
        for i in range(0, len(self.chapters)):
            self.chapters[i].elem_id = "chp{}".format(i)

    @staticmethod
    def _get_time(seconds: float):
        """Convert a number of seconds into the matching datetime.datetime.

        This code accepts a count of seconds from the start of the show and
        adds that time difference to midnight of the current day, returning a
        datetime that can be printed as necessary.

        :param seconds: The number of seconds to create a delta for.
        :param metadata: The metadata to use in the conversion.  If provided, it
        will cause the output plugins to write relevant metadata to the head
        of the file.
        """
        return datetime.datetime.combine(
            datetime.datetime.today().date(), datetime.time(hour=0)
        ) + datetime.timedelta(seconds=seconds)

    @staticmethod
    def _split_url(text: str):
        """Split text into a label and a URL. Return a (text, url) tuple.

        The URL part of the tuple is None if there isn't a URL in the text.
        """
        url = None
        # url_parsed = None
        if "|" in text:
            url = text[text.rindex("|") + 1 :]
            text = text[: text.rindex("|")]
            # url_parsed = urllib.parse.urlparse(url)
        return text, url

    def load(self, path: str):
        """Load a file.

        If the markers in the file are not already in chronological order,
        this class will misbehave.

        :param path: The name of the file to load.
        """
        marker_type = path.split(".")[-1:][0]
        if marker_type == "txt":
            # Decoding Audacity labels
            self._load_audacity(path)
        elif marker_type == "lrc":
            # Decoding an LRC file
            self._load_lrc(path)
        else:
            raise PostShowError("Unsupported marker file: {}".format(marker_type))
        self._canonicalize()

    def _load_audacity(self, path: str):
        """Load an Audacity labels file.

        This plugin also supports URLs, if they are appended to the end of
        the marker with a pipe character:
            Some Marker Name|https://example.com
        """
        with open(path, "r", encoding="utf-8-sig") as fp:
            reader = csv.reader(fp, delimiter="\t", quoting=csv.QUOTE_NONE)
            for row in reader:
                if not row:
                    break
                try:
                    start = float(row[0]) * 1000
                    end = float(row[1]) * 1000
                except ValueError:
                    continue
                # Round start and end times to integer milliseconds.
                start = int(round(start, 0))
                end = int(round(end, 0))
                # mark = row[2]
                text = row[2]
                text, url = self._split_url(text)
                chap = Chapter(start, end, text=text, url=url)
                self.chapters.append(chap)

    def _load_lrc(self, path: str):
        """Load an LRC file.

        This plugin also supports URLs, if they are appended to the end of the
        marker with a pipe character:
            Some Marker Name|https://example.com
        """
        with open(path, "r", encoding="utf-8-sig") as fp:
            previous = None
            for line in fp:
                if re.match(r"^[(ti|ar|al):(.*)]$", line) is not None:
                    continue
                result = re.match(r"^[(\d+):(\d\d\.\d+)](.*)$", line)
                if result is None:
                    continue
                minutes = int(result.group(1))
                seconds = float(result.group(2))
                label = result.group(3)
                millisec = (minutes * 60 * 1000) + int(round(seconds * 1000))
                if previous is not None:
                    self.chapters.append(
                        Chapter(
                            previous[0], millisec, text=previous[1], url=previous[2]
                        )
                    )
                text, url = self._split_url(label)
                previous = (millisec, text, url)
            self.chapters.append(
                Chapter(previous[0], previous[0], text=previous[1], url=previous[2])
            )

    def save(self, path: str, marker_type: int):
        if marker_type == self.LRC:
            self._save_lrc(path)
        elif marker_type == self.CUE:
            self._save_cue(path)
        elif marker_type == self.SIMPLE:
            self._save_simple(path)
        elif marker_type == self.AUDACITY:
            self._save_audacity(path)
        elif marker_type == self.FFMETADATA1:
            self._save_ffmetadata1(path)

    def _save_lrc(self, path: str):
        with open(path, "w", encoding="utf-8") as fp:
            if self.metadata is not None:
                fp.write("[ti:{}]\n".format(self.metadata.title))
                fp.write("[ar:{}]\n".format(self.metadata.artist))
                fp.write("[al:{}]\n".format(self.metadata.album))
            for chapter in self.chapters:
                minutes = chapter.start // (60 * 1000)
                seconds = (chapter.start % (60 * 1000)) // 1000
                fraction = (chapter.start % 1000) // 10
                fp.write(
                    "[{:02d}:{:02d}.{:02d}]{}\n".format(
                        minutes, seconds, fraction, chapter.text
                    )
                )

    def _save_cue(self, path: str):
        if self.media_filename is None:
            raise PostShowError(
                "Writing CUE files is not possible without "
                "the associated media file name. Pass "
                "media_filename='path' when creating the MCS."
            )
        with open(path, "w", encoding="utf-8") as fp:
            fp.write("\ufeff")  # UTF-8 BOM for foobar2000
            fp.write(
                'REM COMMENT "Generated by PostShow v2: '
                'https://github.com/vladasbarisas/XBN"\n'
            )
            fp.write('FILE "{}" MP3\n'.format(self.media_filename))
            if self.metadata is not None:
                fp.write("REM GENRE {}\n".format(self.metadata.genre))
                fp.write('TITLE "{}"\n'.format(self.metadata.title))
                fp.write('PERFORMER "{}"\n'.format(self.metadata.artist))
            for i in range(0, len(self.chapters)):
                chapter = self.chapters[i]
                minutes = chapter.start // (60 * 1000)
                seconds = (chapter.start % (60 * 1000)) // 1000
                # Magic constant is 75/1000, or the number of CUE "frames" per
                # millisecond:
                # https://en.wikipedia.org/wiki/Cue_sheet_(computing)#Essential_commands
                fraction = int(math.floor((chapter.start % 1000) * 0.075))
                fp.write(
                    "  TRACK {0:02d} AUDIO\n"
                    '    TITLE "{1}"\n'
                    "    INDEX 01 {2:02d}:{3:02d}:{4:02d}\n".format(
                        i + 1,
                        chapter.text.replace('"', "_"),
                        minutes,
                        seconds,
                        fraction,
                    )
                )

    def _save_simple(self, path: str):
        with open(path, "w", encoding="utf-8") as fp:
            for chapter in self.chapters:
                start = self._get_time(chapter.start / 1000).strftime("%H:%M:%S")
                fp.write("{0} - {1}\n".format(start, chapter.text))

    def _save_audacity(self, path: str):
        with open(path, "w", encoding="utf-8") as fp:
            for chapter in self.chapters:
                text = chapter.text
                if chapter.url is not None:
                    text += "|" + chapter.url
                fp.write(
                    "{0}\t{1}\t{2}".format(
                        chapter.start / 1000, chapter.end / 1000, text
                    )
                )

    def _save_ffmetadata1(self, path: str):
        """This function doesn't support chapters with URLs, because I don't know how to
        make `FFMPEG` write them"""
        with open(path, "w", encoding="utf-8") as fp:
            fp.write(";FFMETADATA1\n")
            if self.metadata is not None:
                fp.write("title={}\n".format(self.metadata.title))
                fp.write("artist={}\n".format(self.metadata.artist))
            for chapter in self.chapters:
                fp.write(
                    "\n[CHAPTER]\nTIMEBASE=1/1000\n"
                    "START={start}\nEND={end}\ntitle={text}\n".format(
                        start=chapter.start, end=chapter.end, text=chapter.text
                    )
                )
            if self.metadata is not None:
                fp.write("\n[STREAM]\ntitle={}".format(self.metadata.title))

    def get(self):
        return self.chapters


class PostShowError(Exception):
    """Something went wrong, use this to explain."""
