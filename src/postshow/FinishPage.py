import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QGroupBox,
    QFileSystemModel,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListView,
    QMenu,
    QMenuBar,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QWizard,
    QWizardPage,
)


class FinishPage(QWizardPage):
    def __init__(self):
        super().__init__()

        self.setTitle("Encoding Complete")
        self.file_list_model = None

        complete_label = QLabel(
            "The podcast episode has been encoded and tagged successfully."
        )

        rss_metadata_view = QGridLayout()
        outputs_label = QLabel("Output files:")
        output_list = self.generate_file_list()

        main_layout = QVBoxLayout()
        main_layout.addWidget(complete_label)
        main_layout.addLayout(rss_metadata_view)
        self.generate_rss_metadata_view(rss_metadata_view)
        main_layout.addWidget(outputs_label)
        main_layout.addWidget(output_list)
        self.setLayout(main_layout)

    def generate_file_list(self):
        # output_list_model = QStandardItemModel(0, 1)
        # output_list_model.appendRow(QStandardItem(QIcon(), "fnt-206.mp3"))
        # output_list_model.appendRow(QStandardItem(QIcon(), "fnt-206.cue"))
        # output_list_model.appendRow(QStandardItem(QIcon(), "fnt-206.srt"))
        output_list_model = QFileSystemModel()
        output_list_model.setRootPath("/Users/s0ph0s/Desktop/test_folder")
        self.file_list_model = output_list_model
        output_list = QListView()
        output_list.setModel(output_list_model)
        return output_list

    def generate_rss_metadata_view(self, grid_layout):
        size_label = QLabel("MP3 File Size (B):")
        size_field = QLineEdit("dummy")
        size_field.setEnabled(False)
        size_copy_button = QPushButton("Copy")
        grid_layout.addWidget(size_label, 0, 0, 1, 1)
        grid_layout.addWidget(size_field, 0, 1, 1, 1)
        grid_layout.addWidget(size_copy_button, 0, 2, 1, 1)

        duration_label = QLabel("Episode Duration:")
        duration_field = QLineEdit("thicc")
        duration_field.setEnabled(False)
        duration_copy_button = QPushButton("Copy")
        grid_layout.addWidget(duration_label, 1, 0, 1, 1)
        grid_layout.addWidget(duration_field, 1, 1, 1, 1)
        grid_layout.addWidget(duration_copy_button, 1, 2, 1, 1)

    def initializePage(self) -> None:
        self.file_list_model.setRootPath("/Users/s0ph0s/Desktop/test_folder")


if __name__ == "__main__":
    app = QApplication([])
    wizard = QWizard()
    wizard.addPage(FinishPage())
    wizard.show()
    app.exec()
