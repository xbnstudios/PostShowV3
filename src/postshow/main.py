#!/usr/bin/env python3
# coding: utf-8

import sys
from PySide6.QtWidgets import (
    QApplication,
    QWizard,
)
import IOSetupPage
import MetadataPage
import EncoderProgressPage
import FinalizingPage
import config
import model

import os
import tempfile
import datetime


class Controller:
    """Define the control flow of the application as a whole.

    The path is a little confusing, since urwid's event loop doesn't make
    that part easy:
    1. Start the encoder in a separate thread
    2. Display the ``EnterBasics`` view
    3. Use the data from ``EnterBasics`` to fill out the rest of the metadata
    4. Display the ``ConfirmMetadata`` view
    5. Display the ``EncoderProgress`` view
    6. Display the ``TaggerProgress`` view
    7. Save the tags to the file, which will lock up the UI ( threading :( )
    8. Exit
    """

    def __init__(self, args, config):
        self.encoder = model.MP3Encoder()

        self.args = args
        self.config = config
        self.skip_encoding = False
        self.metadata = None
        self.mp3_path = None
        self.chapters = None
        self.tmp_path = None

    def exit_handler(self):
        self.encoder.request_stop()

    def start_encoder(self):
        # Encode the mp3 to a temp file first, then move it later
        self.tmp_path = tempfile.TemporaryDirectory()
        if not self.skip_encoding:
            self.mp3_path = self.build_output_file_path(
                "mp3", parent=self.tmp_path.name
            )
            self.encoder.setup(
                self.args.wav,
                self.mp3_path,
                self.config.get(self.args.profile, "bitrate"),
            )
            # Start the encoder on its own thread
            self.encoder.start()

    def set_metadata(self, metadata: model.EpisodeMetadata):
        self.metadata = metadata
        # Metadata conversion
        self.complete_metadata()
        self.build_chapters()

    def finalize_metadata(self, metadata: model.EpisodeMetadata):
        self.metadata = metadata

    def exit(self):
        if self.encoder is not None and self.encoder.started:
            print("Waiting for the encoder to stop...")
            self.encoder.request_stop()
            self.encoder.join()

    def build_output_file_path(self, ext: str, parent=None):
        """Create the path for an output file with the given extension.

        This requires a bunch of code, which would be better in its own
        function.
        """
        if parent is None:
            return os.path.join(
                self.args.outdir,
                self.config.get(self.args.profile, "filename").format(
                    slug=self.config.get(self.args.profile, "slug").lower(),
                    epnum=self.metadata.number,
                    ext=ext,
                ),
            )
        else:
            return os.path.join(parent, "encoding." + ext)

    def build_chapters(self):
        """Create a chapter list"""
        mcs = model.MCS(
            metadata=self.metadata, media_filename=self.build_output_file_path("mp3")
        )
        mcs.load(self.args.markers)
        self.chapters = mcs.get()
        mcs.save(self.build_output_file_path("lrc"), model.MCS.LRC)
        mcs.save(self.build_output_file_path("cue"), model.MCS.CUE)
        mcs.save(self.build_output_file_path("txt"), model.MCS.SIMPLE)
        self.metadata.lyrics = "\n".join([chapter.text for chapter in self.chapters])

    def do_tag(self):
        """Tag the file, and do step 8.

        8. Exit
        """
        t = model.MP3Tagger(self.mp3_path)
        t.set_title(self.metadata.title)
        t.set_album(self.metadata.album)
        t.set_artist(self.metadata.artist)
        t.set_season(self.metadata.season)
        t.set_genre(self.metadata.genre)
        t.set_language(self.metadata.language)
        if self.metadata.composer is not None:
            t.set_composer(self.metadata.composer)
        if self.metadata.accompaniment is not None:
            t.set_accompaniment(self.metadata.accompaniment)
        if self.metadata.lyrics is not None and self.metadata.lyrics != "":
            t.add_comment(self.metadata.language, "track list", self.metadata.comment)
            if self.metadata.comment is not None:
                t.add_lyrics(self.metadata.language, "track list", self.metadata.lyrics)
        if self.config.getboolean(self.args.profile, "write_date"):
            t.set_date(datetime.datetime.now().strftime("%Y"))
        if self.config.getboolean(self.args.profile, "write_trackno"):
            t.set_trackno(self.metadata.track)
        if self.chapters is not None:
            t.add_chapters(self.chapters)
        if "cover_art" in self.config[self.args.profile].keys():
            t.set_cover_art(self.config.get(self.args.profile, "cover_art"))
        t.save()

    def progress_view_finished(self):
        """Do steps 6 and 7.

        6. Display the ``TaggerProgress`` view
        7. Save the tags to the file, which will lock up the UI ( threading :( )

        This method is supposed to be called by the EncoderProgress view
        after it finishes.
        """
        # This isn't inside the if so that do_tag doesn't fail
        self.mp3_path = self.build_output_file_path("mp3")
        # Join the encoder thread, since tagging can't occur until it is
        # done
        if not self.skip_encoding:
            self.encoder.join()
            os.rename(
                self.build_output_file_path("mp3", parent=self.tmp_path.name),
                self.mp3_path,
            )
            self.tmp_path.cleanup()

    def encoder_finished(self) -> bool:
        """Return true if the encoder is finished."""
        return self.encoder.finished

    def get_encoder_percent(self) -> int:
        return self.encoder.percent

    def complete_metadata(self) -> None:
        """Complete the metadata using the config file.

        Take the information from the config file and the information entered by
        the user and combine them into the complete information for this
        episode.
        """
        self.metadata.title = self.config.get(self.args.profile, "title").format(
            slug=self.config.get(self.args.profile, "slug"),
            epnum=self.metadata.number,
            name=self.metadata.name,
        )
        self.metadata.album = self.config.get(self.args.profile, "album")
        self.metadata.artist = self.config.get(self.args.profile, "artist")
        self.metadata.season = self.config.get(self.args.profile, "season")
        self.metadata.genre = self.config.get(self.args.profile, "genre")
        self.metadata.language = self.config.get(self.args.profile, "language")
        self.metadata.composer = self.config.get(
            self.args.profile, "composer", fallback=None
        )
        self.metadata.accompaniment = self.config.get(
            self.args.profile, "accompaniment", fallback=None
        )
        if self.config.getboolean(self.args.profile, "write_date"):
            self.metadata.date = datetime.datetime.now().strftime("%Y")
        if self.config.getboolean(self.args.profile, "write_trackno"):
            self.metadata.track = self.metadata.number
        if self.config.getboolean(self.args.profile, "lyrics_equals_comment"):
            self.metadata.comment = self.metadata.lyrics


def main():
    config_data = config.check_config()
    controller = Controller()
    app = QApplication([])
    wizard = PostShowWizard()
    wizard.show()
    sys.exit(app.exec())


class PostShowWizard(QWizard):
    def __init__(self):
        super().__init__()
        self.addPage(IOSetupPage.InputOutputPage())
        self.addPage(MetadataPage.MetadataPage())
        self.addPage(EncoderProgressPage.EncoderProgressPage())
        self.addPage(FinalizingPage.FinalizingPage())
        self.setWindowTitle("Encode and Tag Podcast Episode")


if __name__ == "__main__":
    main()
