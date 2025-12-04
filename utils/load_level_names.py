import os


def load_level_names(filename="constants.txt"):
    """
    Reads the level-to-name mappings from a file (constants.txt).
    Each line in the file should have the format: key=value.
    :param filename: The file path to the constants file.
    :return: A dictionary with levels as keys and their mappings as values.
    """
    if not os.path.exists(filename):
        return {}
    level_names = {}
    with open(filename, "r") as file:
        for line in file:
            if "=" in line:
                key, value = [part.strip() for part in line.split("=", 1)]
                level_names[key] = value
    return level_names