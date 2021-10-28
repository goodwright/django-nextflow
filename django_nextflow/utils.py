from datetime import datetime

def parse_datetime(dt):
    return datetime.timestamp(datetime.strptime(dt, "%Y-%m-%d %H:%M:%S"))


def parse_duration(duration):
    if duration.endswith("ms"):
        return float(duration[:-2]) / 1000
    else:
        return float(duration[:-1])
    

def get_file_extension(filename):
    return filename.split(".")[-1] if "." in filename else ""