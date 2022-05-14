import sys

import random
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
    QProgressBar,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QWizardPage,
)


class EncoderProgressPage(QWizardPage):

    MESSAGE_TEMPLATE = "Feel free to {} while LAME does its magic."
    ACTIVITIES = [
        "hum the Jeopardy! theme",
        "scroll through Twitter",
        "mindlessly eject and close your CD tray",
        "take a walk",
        "water your desk plants",
        "notice the bulge",
        "do something else",
        "hang a spoon on your nose",
        "play tiddlywinks",
        "start reading a new book",
        "play with the new shiny",
        "hug someone you love",
        "put on your favorite song",
        "go make sure you turned off the oven",
        "explore rotational inertia with your office chair",
        "tune up your bicycle",
        "answer an email",
        "text them back",
        "study differential calculus",
        "automate a (different) boring task",
        "construct additional pylons",
        "watch your firewall bandwidth graphs",
        "frustrate your friends with bad puns",
        "check the weather",
        "impulse-buy a single-board computer from AliExpress",
        "refill your water glass",
        "request an absentee ballot",
        "sprout more limbs",
        "second-guess your show title choice",
        "call your developers good dogs",
    ]

    def __init__(self):
        super().__init__()

        self.setTitle("Encoding…")
        feel_free_label = QLabel(
            self.MESSAGE_TEMPLATE.format(random.choice(self.ACTIVITIES))
        )
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 101)

        main_layout = QVBoxLayout()
        main_layout.addWidget(feel_free_label)
        main_layout.addWidget(self.progress_bar)
        self.setLayout(main_layout)