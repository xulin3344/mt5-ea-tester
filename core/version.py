import os


def get_version():
    version_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "VERSION")
    try:
        with open(version_file, "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        return "0.0.0"
