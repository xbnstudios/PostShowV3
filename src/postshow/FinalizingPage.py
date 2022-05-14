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
    QWizardPage,
)


class FinalizingPage(QWizardPage):
    def __init__(self):
        super().__init__()

        self.setTitle("Encoding Complete")

        complete_label = QLabel(
            "The podcast episode has been encoded and tagged successfully."
        )

        output_list_model = QStandardItemModel(0, 1)
        output_list_model.appendRow(QStandardItem(QIcon(), "fnt-206.mp3"))
        output_list_model.appendRow(QStandardItem(QIcon(), "fnt-206.cue"))
        output_list_model.appendRow(QStandardItem(QIcon(), "fnt-206.srt"))
        output_list = QListView()
        output_list.setModel(output_list_model)

        main_layout = QVBoxLayout()
        main_layout.addWidget(complete_label)
        main_layout.addWidget(output_list)
        self.setLayout(main_layout)