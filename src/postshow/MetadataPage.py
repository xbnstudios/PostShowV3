import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QGroupBox,
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


class MetadataPage(QWizardPage):
    def __init__(self):
        super().__init__()

        self.setTitle("Confirm Metadata")

        metadata_box = QGridLayout()

        main_label = QLabel(
            "The metadata below will be written to the MP3 file, once encoding is finished."
        )

        main_layout = QVBoxLayout()
        main_layout.addWidget(main_label)
        main_layout.addLayout(metadata_box)
        self.setLayout(main_layout)

        # The QGridLayout must be added to the parent layout before you can put
        # anything into it.
        self.create_metadata_box(metadata_box)

    def create_metadata_box(self, layout):
        basic_fields = [
            "Title",
            "Album",
            "Artist",
            "Season",
            "Genre",
            "Language",
            "Composer",
            "Accompaniment",
            "Year",
            "Number",
        ]

        for field_index in range(len(basic_fields)):
            label = QLabel(basic_fields[field_index] + ":")
            line = QLineEdit()
            layout.addWidget(label, field_index, 0, 1, 1)
            layout.addWidget(line, field_index, 1, 1, 1)
        # The Lyrics box supports newlines, so it has to be a different widget
        # type from the rest of the fields.
        lyrics_label = QLabel("Lyrics:")
        lyrics_box = QTextEdit()
        lyrics_box.setAcceptRichText(False)
        layout.addWidget(lyrics_label, len(basic_fields), 0, 1, 1)
        layout.addWidget(lyrics_box, len(basic_fields), 1, 1, 1)