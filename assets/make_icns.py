import subprocess
import sys
import os.path
import os


# a class to store icon parameters: its size and scale factor
class IconParameters:
    width = 0
    scale = 1

    def __init__(self, width, scale):
        self.width = width
        self.scale = scale

    def getIconName(self):
        scaleString = "" if self.scale == 1 else "@{}x".format(self.scale)
        return "icon_{width}x{width}{scaleString}.png".format(
            width=self.width, scaleString=scaleString
        )


# create a list of all the sizes (5 actual sizes, but 10 files)
ListOfIconParameters = [
    IconParameters(16, 1),
    IconParameters(16, 2),
    IconParameters(32, 1),
    IconParameters(32, 2),
    IconParameters(128, 1),
    IconParameters(128, 2),
    IconParameters(256, 1),
    IconParameters(256, 2),
    IconParameters(512, 1),
    IconParameters(512, 2),
]

png_file = sys.argv[1]
iconsetDir = os.path.splitext(png_file)[0] + ".iconset"
icns_file = os.path.splitext(png_file)[0] + ".icns"
try:
    os.mkdir(iconsetDir)
except FileExistsError:
    pass

for ip in ListOfIconParameters:
    subprocess.run(
        [
            "convert",
            png_file,
            "-resize",
            "{x}x{x}".format(x=str(ip.width * ip.scale)),
            os.path.join(iconsetDir, ip.getIconName()),
        ],
        capture_output=True,
        text=True,
    )

subprocess.run(
    [
        "iconutil",
        "-c",
        "icns",
        iconsetDir,
        "-o",
        icns_file
    ]
)
