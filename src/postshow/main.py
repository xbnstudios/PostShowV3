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
from typing import List

from PySide6.QtCore import QStandardPaths, QUrl, Slot, QSysInfo, QProcess
from PySide6.QtGui import QDesktopServices
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
import shutil

DEFAULT_CONFIG_PATH = os.path.join(
    QStandardPaths.writableLocation(QStandardPaths.GenericConfigLocation),
    "PostShow",
    "config.ini",
)


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

    def __init__(self, config_data):
        self.encoder: model.MP3Encoder | None = None
        self.config_data = config_data
        self.skip_encoding = False
        self.metadata = None
        self.mp3_path = None
        self.chapters = None
        self.tmp_path = tempfile.TemporaryDirectory()
        self.outdir = None
        self.tagger: model.MP3Tagger | None = None
        self.profile = "default"
        self.encoder_progress_signal = EncoderProgressPage.ProgressUpdateEmitter()
        self.output_files = []
        self.markers_file = None

    def exit_handler(self):
        if self.encoder:
            self.encoder.request_stop()

    def reset_encoder(self):
        if self.encoder:
            self.encoder.request_stop()
            try:
                self.encoder.join()
            except RuntimeError:
                print(
                    "I tried to stop the encoder, but it wasn't running. This is fine."
                )
            self.encoder = None
            self.output_files = []
            print("Encoder reset")

    def start_encoder(self, wav_path):
        # Encode the mp3 to a temp file first, then move it later
        if not self.skip_encoding:
            self.mp3_path = self.build_output_file_path(
                "mp3", parent=self.tmp_path.name
            )
            self.encoder = model.MP3Encoder(
                wav_path,
                self.mp3_path,
                self.config_data.get(self.profile, "bitrate"),
                self.encoder_progress_signal,
            )
            # Start the encoder on its own thread
            self.encoder.start()

    def check_before_wreck(self) -> List[str]:
        outfiles = [
            self.build_output_file_path("mp3"),
            self.build_output_file_path("lrc"),
            self.build_output_file_path("cue"),
            self.build_output_file_path("txt"),
        ]
        files_that_exist = []
        for file in outfiles:
            if file and os.path.exists(file):
                files_that_exist.append(file)
        return files_that_exist

    def set_metadata(self, metadata: model.EpisodeMetadata):
        self.metadata = metadata
        # Metadata conversion
        self.complete_metadata(self.profile)

    def exit(self):
        if self.encoder is not None and self.encoder.started:
            print("Waiting for the encoder to stop...")
            self.encoder.request_stop()
            self.encoder.join()

    def build_output_file_path(self, ext: str, parent=None) -> str:
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
        if self.markers_file:
            mcs.load(self.markers_file)
            self.chapters = mcs.get()
            lrc_path = self.build_output_file_path("lrc")
            cue_path = self.build_output_file_path("cue")
            txt_path = self.build_output_file_path("txt")
            mcs.save(lrc_path, model.MCS.LRC)
            mcs.save(cue_path, model.MCS.CUE)
            mcs.save(txt_path, model.MCS.SIMPLE)
            self.output_files.append(lrc_path)
            self.output_files.append(cue_path)
            self.output_files.append(txt_path)
            if self.metadata:
                self.metadata.lyrics = "\n".join(
                    [chapter.text for chapter in self.chapters]
                )
        else:
            print("markers_file was None")

    def do_tag(self):
        """Tag the file, and do step 8.

        8. Exit
        """
        if not self.metadata:
            return
        t = model.MP3Tagger(self.mp3_path, self.encoder_progress_signal)
        self.tagger = t
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
        if not self.skip_encoding and self.encoder:
            self.encoder.join()
            output_mp3 = self.build_output_file_path("mp3", parent=self.tmp_path.name)
            if output_mp3 and self.mp3_path:
                shutil.move(
                    output_mp3,
                    self.mp3_path,
                )
                self.output_files.append(self.mp3_path)
                self.tmp_path.cleanup()

    def complete_metadata(self, profile_name: str) -> None:
        """Complete the metadata using the config file.

        Take the information from the config file and the information entered by
        the user and combine them into the complete information for this
        episode.
        """
        if not self.metadata:
            return
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

    def get_mp3_length_ms(self) -> int:
        if self.tagger:
            return self.tagger.length_ms
        else:
            return 0


def config_wizard(default_config_path) -> bool:
    wizard_box = QMessageBox(
        QMessageBox.Warning,
        "No configuration file",
        "There is no configuration file for PostShow yet. Create one now?",
    )
    quit_button = wizard_box.addButton("Quit", QMessageBox.RejectRole)
    wizard_box.addButton("Create", QMessageBox.AcceptRole)
    wizard_box.exec()
    if wizard_box.clickedButton() == quit_button:
        return False
    config_basedir = os.path.dirname(default_config_path)
    try:
        os.mkdir(config_basedir)
    except FileExistsError:
        # We don't care, that's fine.
        pass
    basedir = os.path.dirname(__file__)
    if "DEBUG" in os.environ.keys():
        shutil.copyfile(
            os.path.join(basedir, "..", "..", "data", "template_config.ini"),
            default_config_path,
        )
    else:
        shutil.copyfile(
            os.path.join(basedir, "data", "template_config.ini"),
            default_config_path,
        )
    show_config()
    return True


def main():
    app = QApplication([])
    if not os.path.exists(DEFAULT_CONFIG_PATH):
        if not config_wizard(DEFAULT_CONFIG_PATH):
            return
    try:
        config_data = config.check_config(DEFAULT_CONFIG_PATH)
        controller = Controller(config_data)
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
        error_box.addButton("Quit", QMessageBox.AcceptRole)
        error_box.exec()
        if error_box.clickedButton() == help_button:
            qem = QErrorMessage()
            qem.showMessage(
                "<br>".join(traceback.format_exception(None, pse, pse.__traceback__))
            )
            qem.exec()


@Slot()
def show_config():
    QMessageBox.information(
        None,
        "Opening Config",
        "PostShow will open the config file and then quit; relaunch it when "
        "you're done making config changes.",
        QMessageBox.StandardButton.Ok,
    )
    product_type = QSysInfo.productType()
    if product_type == "macos":
        p = QProcess()
        p.startDetached("open", ["-e", DEFAULT_CONFIG_PATH])
    else:
        default_config_url = QUrl.fromLocalFile(DEFAULT_CONFIG_PATH)
        QDesktopServices.openUrl(default_config_url)
    sys.exit(0)


class PostShowWizard(QWizard):
    def __init__(self, controller):
        super().__init__()
        self.setButtonText(QWizard.CommitButton, "Encode")
        self.setButtonText(QWizard.HelpButton, "Open Config")
        self.addPage(IOSetupPage.InputOutputPage(controller))
        self.addPage(MetadataPage.MetadataPage(controller))
        self.addPage(EncoderProgressPage.EncoderProgressPage(controller))
        self.addPage(FinishPage.FinishPage(controller))
        self.setWindowTitle("Encode and Tag Podcast Episode")
        self.setOption(QWizard.HaveHelpButton, True)
        self.helpRequested.connect(show_config)


if __name__ == "__main__":
    main()
