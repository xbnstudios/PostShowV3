from PySide6.QtWidgets import (
    QGridLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
    QVBoxLayout,
    QWizardPage,
)


class MetadataPage(QWizardPage):

    BASIC_FIELDS = [
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
        "Lyrics",
    ]

    def __init__(self, controller):
        super().__init__()

        self.controller = controller

        self.setTitle("Confirm Metadata")

        metadata_box = QGridLayout()
        main_label = QLabel(
            "The metadata below will be written to the MP3 file, once encoding is finished."
        )
        main_layout = QVBoxLayout()
        main_layout.addWidget(main_label)
        main_layout.addLayout(metadata_box)
        self.setLayout(main_layout)

        self.editable_fields = {}

        # The QGridLayout must be added to the parent layout before you can put
        # anything into it.
        self.create_metadata_box(metadata_box)
        self.setCommitPage(True)

    def initializePage(self) -> None:
        for field_name in self.BASIC_FIELDS:
            lower_field_name = field_name.lower()
            self.editable_fields[lower_field_name].setText(
                self.controller.metadata[lower_field_name]
            )

    def generate_field_updater(self, field_name):
        lower_field_name = field_name.lower()

        def field_updater():
            if lower_field_name == "lyrics":
                new_value = self.editable_fields[lower_field_name].toPlainText()
            else:
                new_value = self.editable_fields[lower_field_name].text()
            print("Updating value for {} to {}".format(lower_field_name, new_value))
            self.controller.metadata[lower_field_name] = new_value

        return field_updater

    def create_metadata_box(self, layout):
        # Skip lyrics, see below.
        for field_index in range(len(self.BASIC_FIELDS) - 1):
            field_name = self.BASIC_FIELDS[field_index]
            lower_field_name = field_name.lower()
            label = QLabel(field_name + ":")
            line = QLineEdit()
            self.registerField(lower_field_name, line)
            self.editable_fields[lower_field_name] = line
            line.editingFinished.connect(self.generate_field_updater(lower_field_name))
            layout.addWidget(label, field_index, 0, 1, 1)
            layout.addWidget(line, field_index, 1, 1, 1)
        # The Lyrics box supports newlines, so it has to be a different widget
        # type from the rest of the fields.
        lyrics_label = QLabel("Lyrics:")
        lyrics_box = QTextEdit()
        self.registerField("lyrics", lyrics_box)
        self.editable_fields["lyrics"] = lyrics_box
        lyrics_box.textChanged.connect(self.generate_field_updater("lyrics"))
        lyrics_box.setAcceptRichText(False)
        lyrics_position = len(self.BASIC_FIELDS) - 1
        layout.addWidget(lyrics_label, lyrics_position, 0, 1, 1)
        layout.addWidget(lyrics_box, lyrics_position, 1, 1, 1)

    def validatePage(self) -> bool:
        return True
