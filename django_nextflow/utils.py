import hashlib
from datetime import datetime

def parse_datetime(dt):
    """Gets a UNIX timestamp from a Nextflow datetime string."""

    return datetime.timestamp(datetime.strptime(dt[:19], "%Y-%m-%d %H:%M:%S"))


def parse_duration(duration):
    """Gets a duration in seconds from a Nextflow duration string."""

    if duration == "-": return 0
    if " " in duration:
        values = duration.split()
        return sum(parse_duration(v) for v in values)
    elif duration.endswith("ms"):
        return float(duration[:-2]) / 1000
    elif duration.endswith("s"):
        return float(duration[:-1])
    elif duration.endswith("m"):
        return float(duration[:-1]) * 60
    elif duration.endswith("h"):
        return float(duration[:-1]) * 3600
        
    

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