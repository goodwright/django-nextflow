from datetime import datetime

def parse_datetime(dt):
    """Gets a UNIX timestamp from a Nextflow datetime string."""

    return datetime.timestamp(datetime.strptime(dt, "%Y-%m-%d %H:%M:%S"))


def parse_duration(duration):
    """Gets a duration in seconds from a Nextflow duration string."""

    if duration == "-": return 0
    if duration.endswith("ms"):
        return float(duration[:-2]) / 1000
    else:
        return float(duration[:-1])
    

def get_file_extension(filename):
    """Gets the file extension from some filename."""
    
    return filename.split(".")[-1] if "." in filename else ""