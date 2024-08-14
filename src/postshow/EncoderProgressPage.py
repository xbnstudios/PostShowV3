import platform

import random
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import (
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWizardPage,
)


class ProgressUpdateEmitter(QObject):
    progressed = Signal(int)
    encoder_finished = Signal()

    def set_progress(self, value):
        self.progressed.emit(value)

    def set_finished(self):
        self.encoder_finished.emit()


class EncoderProgressPage(QWizardPage):

    MESSAGE_TEMPLATE = "Feel free to {} while LAME does its magic."
    ACTIVITIES = [
        "hum the Jeopardy! theme",
        "scroll through Bluesky",
        "scroll through Mastodon",
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

    def __init__(self, controller):
        super().__init__()

        self.controller = controller

        self.setTitle("Encoding…")
        feel_free_label = QLabel(
            self.MESSAGE_TEMPLATE.format(random.choice(self.ACTIVITIES))
        )
        feel_free_label.setWordWrap(True)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 101)
        self.controller.encoder_progress_signal.progressed.connect(
            self.progress_bar.setValue
        )
        self.controller.encoder_progress_signal.progressed.connect(
            self.emit_complete_when_finished
        )
        self.controller.encoder_progress_signal.encoder_finished.connect(
            self.finish_encoder
        )

        main_layout = QVBoxLayout()
        main_layout.addWidget(feel_free_label)
        if platform.system() == "Darwin":
            mac_label = QLabel(
                "Because of a macOS-related bug, LAME may falsely report its progress "
                "as 100% for the duration of the encoding."
            )
            mac_label.setWordWrap(True)
            main_layout.addWidget(mac_label)
        main_layout.addWidget(self.progress_bar)
        self.setLayout(main_layout)

    def finish_encoder(self):
        self.controller.progress_view_finished()
        self.controller.do_tag()

    def isComplete(self) -> bool:
        return self.progress_bar.value() == 101

    def emit_complete_when_finished(self, value):
        if value == 101:
            self.wizard().next()
