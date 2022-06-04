import hashlib


def get_file_extension(filename):
    """Gets the file extension from some filename."""
    
    if filename.endswith(".gz"):
        return ".".join(filename.split(".")[-2:])
    return filename.split(".")[-1] if "." in filename else ""


def get_file_hash(path):
    """Gets the MD5 hash of a file from its path."""
    
    hash_md5 = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def check_if_binary(path):
    """Checks if a file contains data that needs to be opened with 'rb'."""
    
    try:
        with open(path) as f:
            f.read(1024)
        return False
    except UnicodeDecodeError:
        return True