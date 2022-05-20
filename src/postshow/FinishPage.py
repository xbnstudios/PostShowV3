import sys

from PySide6.QtCore import Qt, QSysInfo, QProcess, Slot, QModelIndex
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
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QWizard,
    QWizardPage,
)
import os.path
import datetime

MICROSECONDS_PER_SECOND = 1000000


class FinishPage(QWizardPage):
    def __init__(self, controller):
        super().__init__()

        self.setTitle("Encoding Complete")
        self.file_list_model = None
        self.controller = controller
        self.size_field = None
        self.duration_field = None

        complete_label = QLabel(
            "The podcast episode has been encoded and tagged successfully."
        )

        rss_metadata_view = QGridLayout()
        outputs_label = QLabel("Output files:")
        output_list = self.generate_file_list_view()

        main_layout = QVBoxLayout()
        main_layout.addWidget(complete_label)
        main_layout.addLayout(rss_metadata_view)
        self.generate_rss_metadata_view(rss_metadata_view)
        main_layout.addWidget(outputs_label)
        main_layout.addWidget(output_list)
        self.setLayout(main_layout)

    def generate_file_list_view(self):
        # We're using a QStandardItemModel instead of the QFileSystemModel because
        # then we can show just the files that this run created, in case there's
        # other stuff in the output folder.
        output_list_model = QStandardItemModel(0, 1)
        # output_list_model = QFileSystemModel()
        # output_list_model.setRootPath("/Users/s0ph0s/Desktop/test_folder")
        self.file_list_model = output_list_model
        output_list = QListView()
        output_list.setModel(output_list_model)
        output_list.doubleClicked.connect(self.handle_row_double_click)
        return output_list

    def generate_copy_to_clipboard_handler(self, field):
        clipboard = QApplication.clipboard()

        def helper():
            clipboard.setText(field.text())

        return helper

    def generate_rss_metadata_view(self, grid_layout):
        size_label = QLabel("MP3 File Size (B):")
        size_field = QLineEdit("dummy")
        size_field.setEnabled(False)
        self.size_field = size_field
        size_copy_button = QPushButton("Copy")
        size_copy_button.clicked.connect(
            self.generate_copy_to_clipboard_handler(size_field)
        )
        grid_layout.addWidget(size_label, 0, 0, 1, 1)
        grid_layout.addWidget(size_field, 0, 1, 1, 1)
        grid_layout.addWidget(size_copy_button, 0, 2, 1, 1)

        duration_label = QLabel("Episode Duration:")
        duration_field = QLineEdit("thicc")
        duration_field.setEnabled(False)
        self.duration_field = duration_field
        duration_copy_button = QPushButton("Copy")
        duration_copy_button.clicked.connect(
            self.generate_copy_to_clipboard_handler(duration_field)
        )
        grid_layout.addWidget(duration_label, 1, 0, 1, 1)
        grid_layout.addWidget(duration_field, 1, 1, 1, 1)
        grid_layout.addWidget(duration_copy_button, 1, 2, 1, 1)

    def initializePage(self) -> None:
        # self.file_list_model.setRootPath("/Users/s0ph0s/Desktop/test_folder")
        mp3_size = os.path.getsize(self.controller.mp3_path)
        self.size_field.setText(str(mp3_size))
        mp3_duration_ms = self.controller.get_mp3_length_ms()
        mp3_duration = datetime.timedelta(milliseconds=mp3_duration_ms)
        # Round up to the nearest whole second, because the RSS duration format does
        # not accept microseconds.
        if mp3_duration.microseconds != 0:
            mp3_duration = mp3_duration + datetime.timedelta(
                microseconds=(MICROSECONDS_PER_SECOND - mp3_duration.microseconds)
            )
        # Use the default timedelta format: HH:MM:ss.
        self.duration_field.setText(str(mp3_duration))
        for file in self.controller.output_files:
            filename = os.path.basename(file)
            item = QStandardItem(QIcon(), file)
            item.setEditable(False)
            # Set the data to be the full file path, in case the display string gets
            # changed in the future.
            item.setData(file)
            self.file_list_model.appendRow(item)

    @Slot(QModelIndex)
    def handle_row_double_click(self, model_idx):
        item = self.file_list_model.itemFromIndex(model_idx)
        self.show_file_in_graphical_shell(item.data())

    def show_file_in_graphical_shell(self, path):
        product_type = QSysInfo.productType()
        p = QProcess()
        if product_type == "windows":
            p.startDetached("explorer.exe", ["/select,", path])
        elif product_type == "macos":
            p.startDetached("/usr/bin/open", ["-R", path])
        else:
            error = QMessageBox.critical(
                "Operation Not Supported",
                "Revealing the selected file in the file browser is not supported on "
                "{} because there is no standard way to accomplish the task. "
                "PRs welcome!".format(product_type),
            )
            error.show()
