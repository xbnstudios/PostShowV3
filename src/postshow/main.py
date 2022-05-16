#!/usr/bin/env python3
# coding: utf-8

# To Future Readers:
# I didn't have sufficient motivation to rewrite this application from scratch. I
# built it out of the carcass of the prior version, which was a console application
# using urwid as the UI library.  This resulted in many sub-optimal software
# architecture decisions, several of which were cargo-culted into this application
# out of expediency.
#
# If you would like to ask questions about what things do (or complain about what I'm
# putting you through), contact awoo@s0ph0s.dog or t.me/s0ph0s.

import sys
import traceback

from PySide6.QtWidgets import (
    QApplication,
    QMessageBox,
    QErrorMessage,
    QWizard,
)
import IOSetupPage
import MetadataPage
import EncoderProgressPage
import FinishPage
import config
import model

import os
import tempfile
import datetime
import argparse


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

    def __init__(self, args, config_data):
        self.encoder = model.MP3Encoder()

        self.args = args
        self.config_data = config_data
        self.skip_encoding = False
        self.metadata = None
        self.mp3_path = None
        self.chapters = None
        self.tmp_path = None
        self.outdir = None
        self.tagger = None
        self.profile = "default"
        self.encoder_progress_signal = EncoderProgressPage.ProgressUpdateEmitter()

    def exit_handler(self):
        self.encoder.request_stop()

    def start_encoder(self, wav_path):
        # Encode the mp3 to a temp file first, then move it later
        self.tmp_path = tempfile.TemporaryDirectory()
        if not self.skip_encoding:
            self.mp3_path = self.build_output_file_path(
                "mp3", parent=self.tmp_path.name
            )
            self.encoder.setup(
                wav_path,
                self.mp3_path,
                self.config_data.get(self.profile, "bitrate"),
                self.encoder_progress_signal,
            )
            # Start the encoder on its own thread
            self.encoder.start()

    def set_metadata(self, metadata: model.EpisodeMetadata):
        self.metadata = metadata
        # Metadata conversion
        self.complete_metadata(self.profile)
        self.build_chapters()

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
                self.outdir,
                self.config_data.get(self.profile, "filename").format(
                    slug=self.config_data.get(self.profile, "slug").lower(),
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
        mcs.load(self.markers_file)
        self.chapters = mcs.get()
        mcs.save(self.build_output_file_path("lrc"), model.MCS.LRC)
        mcs.save(self.build_output_file_path("cue"), model.MCS.CUE)
        mcs.save(self.build_output_file_path("txt"), model.MCS.SIMPLE)
        self.metadata.lyrics = "\n".join([chapter.text for chapter in self.chapters])

    def do_tag(self):
        """Tag the file, and do step 8.

        8. Exit
        """
        t = model.MP3Tagger()
        self.tagger = t
        t.setup(self.mp3_path, self.encoder_progress_signal)
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
        if self.config_data.getboolean(self.profile, "write_date"):
            t.set_date(self.metadata.year)
        if self.config_data.getboolean(self.profile, "write_trackno"):
            t.set_trackno(self.metadata.track)
        if self.chapters is not None:
            t.add_chapters(self.chapters)
        if "cover_art" in self.config_data[self.profile].keys():
            t.set_cover_art(self.config_data.get(self.profile, "cover_art"))
        t.start()

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

    def complete_metadata(self, profile_name: str) -> None:
        """Complete the metadata using the config file.

        Take the information from the config file and the information entered by
        the user and combine them into the complete information for this
        episode.
        """
        self.metadata.title = self.config_data.get(profile_name, "title").format(
            slug=self.config_data.get(profile_name, "slug"),
            epnum=self.metadata.number,
            name=self.metadata.name,
        )
        self.metadata.album = self.config_data.get(profile_name, "album")
        self.metadata.artist = self.config_data.get(profile_name, "artist")
        self.metadata.season = self.config_data.get(profile_name, "season")
        self.metadata.genre = self.config_data.get(profile_name, "genre")
        self.metadata.language = self.config_data.get(profile_name, "language")
        self.metadata.composer = self.config_data.get(
            profile_name, "composer", fallback=None
        )
        self.metadata.accompaniment = self.config_data.get(
            profile_name, "accompaniment", fallback=None
        )
        if self.config_data.getboolean(profile_name, "write_date"):
            self.metadata.year = datetime.datetime.now().strftime("%Y")
        if self.config_data.getboolean(profile_name, "write_trackno"):
            self.metadata.track = self.metadata.number
        if self.config_data.getboolean(profile_name, "lyrics_equals_comment"):
            self.metadata.comment = self.metadata.lyrics


def parse_args() -> argparse.Namespace:
    """Parse arguments to this program."""
    parser = argparse.ArgumentParser(
        description="Convert and tag WAVs and chapter metadata for podcasts."
    )
    parser.add_argument(
        "-c",
        "--config",
        help="configuration file to use, defaults to $HOME/.config/postshow.ini",
        default=os.path.expandvars("$HOME/.config/postshow.ini"),
    )
    args = parser.parse_args()
    errors = []
    if not os.path.exists(args.config):
        errors.append("Configuration file ({}) does not exist".format(args.config))
    if len(errors) > 0:
        raise model.PostShowError(";\n".join(errors))
    return args


def main():
    app = QApplication([])
    try:
        args = parse_args()
        config_data = config.check_config(args.config)
        controller = Controller(args, config_data)
        wizard = PostShowWizard(controller)
        wizard.show()
        sys.exit(app.exec())
    except model.PostShowError as pse:
        error_box = QMessageBox(
            QMessageBox.Critical,
            "PostShow could not continue",
            "An error occurred that could not be automatically resolved.",
        )
        help_button = error_box.addButton("Help", QMessageBox.HelpRole)
        quit_button = error_box.addButton("Quit", QMessageBox.AcceptRole)
        error_box.exec()
        if error_box.clickedButton() == help_button:
            qem = QErrorMessage()
            qem.showMessage(
                "<br>".join(traceback.format_exception(None, pse, pse.__traceback__))
            )
            qem.exec()
        exit(1)


class PostShowWizard(QWizard):
    def __init__(self, controller):
        super().__init__()
        self.setButtonText(QWizard.CommitButton, "Encode")
        self.addPage(IOSetupPage.InputOutputPage(controller))
        self.addPage(MetadataPage.MetadataPage(controller))
        self.addPage(EncoderProgressPage.EncoderProgressPage(controller))
        self.addPage(FinishPage.FinishPage())
        self.setWindowTitle("Encode and Tag Podcast Episode")


if __name__ == "__main__":
    main()
