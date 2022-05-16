import sys

import os.path
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QGroupBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QMenuBar,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QWizardPage,
)
import model


class InputOutputPage(QWizardPage):
    def __init__(self, controller):
        super().__init__()

        self.controller = controller

        self.setTitle("Choose Input and Output Files")
        self.create_input_box()
        self.create_metadata_box()
        self.create_output_box()

        main_layout = QVBoxLayout()
        main_layout.addWidget(self._input_group_box)
        main_layout.addSpacing(5)
        main_layout.addWidget(self._metadata_group_box)
        main_layout.addSpacing(5)
        main_layout.addWidget(self._output_group_box)
        self.setLayout(main_layout)

    def show_file_chooser_for_field(self, field, title: str, filters: str):
        # TODO: save last file location for a particular field and open there next time
        file_name = QFileDialog.getOpenFileName(
            self, title, os.path.expanduser("~"), filters
        )
        print("show_file_chooser_for_field:", file_name)
        field.setText(file_name[0])

    def show_folder_chooser_for_field(self, field, title: str):
        # TODO: default to last location, warn if expected names exist
        folder_name = QFileDialog.getExistingDirectory(
            self, title, os.path.expanduser("~")
        )
        print("show_folder_chooser_for_field:", folder_name)
        field.setText(folder_name)

    def create_input_box(self):
        self._input_group_box = QGroupBox("Input Files")
        layout = QVBoxLayout()
        layout.setSpacing(0)

        # WAV File Entry
        wav_label = QLabel("Final episode recording (WAV or MP3):")
        wav_chooser_layout = QHBoxLayout()
        # 9 is the default spacing for child layouts, but because of the parent
        # layout's spacing being set to 0, we have to override the inherited
        # value.
        wav_chooser_layout.setSpacing(9)
        self.recording_file_line = QLineEdit()
        self.recording_choose_button = QPushButton("Choose File")
        self.recording_choose_button.clicked.connect(
            lambda: self.show_file_chooser_for_field(
                self.recording_file_line,
                "Final episode recording (WAV or MP3)",
                "Audio file (*.wav *.mp3)",
            )
        )
        wav_chooser_layout.addWidget(self.recording_file_line)
        wav_chooser_layout.addWidget(self.recording_choose_button)
        self.registerField("recording_file*", self.recording_file_line)

        layout.addWidget(wav_label)
        layout.addLayout(wav_chooser_layout)

        layout.addSpacing(5)

        # Chapter Metadata Entry
        chap_label = QLabel("Audacity chapter labels file:")
        chap_chooser_layout = QHBoxLayout()
        chap_chooser_layout.setSpacing(9)
        self.chap_file_line = QLineEdit()
        self.chap_choose_button = QPushButton("Choose File")
        self.chap_choose_button.clicked.connect(
            lambda: self.show_file_chooser_for_field(
                self.chap_file_line,
                "Audacity chapter labels file",
                "Audacity labels (*.csv *.tsv *.txt",
            )
        )
        chap_chooser_layout.addWidget(self.chap_file_line)
        chap_chooser_layout.addWidget(self.chap_choose_button)
        self.registerField("chap_file*", self.chap_file_line)

        layout.addWidget(chap_label)
        layout.addLayout(chap_chooser_layout)

        self._input_group_box.setLayout(layout)

    def create_metadata_box(self):
        self._metadata_group_box = QGroupBox("Basic Podcast Metadata")
        layout = QVBoxLayout()
        layout.setSpacing(0)

        # Show Template
        template_label = QLabel("Show metadata template:")
        self.template_box = QComboBox()
        for section_name in self.controller.config_data:
            # ConfigParser adds this section, and we don't use it.
            if section_name == "DEFAULT":
                continue
            show_slug = self.controller.config_data[section_name]["slug"]
            self.template_box.addItem(QIcon(), show_slug, section_name)
        layout.addWidget(template_label)
        layout.addWidget(self.template_box)
        self.registerField("template", self.template_box)

        # Episode Number
        number_label = QLabel("Episode number:")
        self.number_line = QLineEdit()
        layout.addWidget(number_label)
        layout.addWidget(self.number_line)
        self.registerField("episode_number*", self.number_line)

        # Episode Title
        title_label = QLabel("Episode title:")
        self.title_line = QLineEdit()
        layout.addWidget(title_label)
        layout.addWidget(self.title_line)
        self.registerField("episode_title*", self.title_line)

        self._metadata_group_box.setLayout(layout)

    def create_output_box(self):
        self._output_group_box = QGroupBox("Output Folder")
        layout = QVBoxLayout()
        layout.setSpacing(0)

        outfolder_label = QLabel("Output folder:")
        outfolder_chooser_layout = QHBoxLayout()
        outfolder_chooser_layout.setSpacing(9)
        self.outfolder_folder_line = QLineEdit()
        self.outfolder_choose_button = QPushButton("Choose Folder")
        self.outfolder_choose_button.clicked.connect(
            lambda: self.show_folder_chooser_for_field(
                self.outfolder_folder_line, "Output folder"
            )
        )
        outfolder_chooser_layout.addWidget(self.outfolder_folder_line)
        outfolder_chooser_layout.addWidget(self.outfolder_choose_button)
        self.registerField("outfolder*", self.outfolder_folder_line)

        layout.addWidget(outfolder_label)
        layout.addLayout(outfolder_chooser_layout)

        self._output_group_box.setLayout(layout)

    def validatePage(self) -> bool:
        self.controller.profile = self.template_box.currentData()
        recording_file_path = self.recording_file_line.text()
        if recording_file_path.endswith(".wav"):
            self.controller.start_encoder(recording_file_path)
        else:
            self.controller.skip_encoding = True
        metadata = model.EpisodeMetadata(
            self.number_line.text(), self.title_line.text()
        )
        self.controller.outdir = self.outfolder_folder_line.text()
        self.controller.markers_file = self.chap_file_line.text()
        self.controller.set_metadata(metadata)
        return True
