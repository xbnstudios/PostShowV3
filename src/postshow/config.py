import configparser
from model import PostShowError
import os.path

# These keys must be in the configuration file, with text values
REQUIRED_TEXT_KEYS = [
    "slug",
    "filename",
    "bitrate",
    "title",
    "album",
    "artist",
    "season",
    "language",
    "genre",
]
# These keys must be in the configuration file, with boolean values
REQUIRED_BOOL_KEYS = ["write_date", "write_trackno", "lyrics_equals_comment"]


def check_config(path: str) -> configparser.ConfigParser:
    """Load the config file and check it for correctness."""
    config = configparser.ConfigParser()
    config.read(path)
    errors = []
    # Check every section of the config file, except for DEFAULT (which we
    # don't care about)
    for section in config:
        if section == "DEFAULT":
            continue
        so = config[section]
        # Just verify that the REQUIRED_TEXT_KEYS from above exist in the
        # file.  If they're just empty strings, that's the user's problem.
        for key in REQUIRED_TEXT_KEYS:
            if key not in so.keys():
                errors.append(
                    "[{section}] is missing the required key"
                    ' "{key}"'.format(section=section, key=key)
                )
        # Verify that the REQUIRED_BOOL_KEYS from above exist in the file,
        # and are boolean values.
        for key in REQUIRED_BOOL_KEYS:
            if key not in so.keys():
                errors.append(
                    "[{section}] is missing the required key"
                    ' "{key}"'.format(section=section, key=key)
                )
            else:
                if so[key] not in ["True", "False"]:
                    errors.append(
                        "[{section}] must use Python boolean "
                        'values ("True" or "False") for the key '
                        '"{key}"'.format(section=section, key=key)
                    )
        if "cover_art" in so.keys():
            so["cover_art"] = os.path.expandvars(so["cover_art"])
    if len(errors) > 0:
        raise PostShowError(";\n".join(errors))
    return config
