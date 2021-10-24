from datetime import datetime

def parse_datetime(dt):
    return datetime.timestamp(datetime.strptime(dt, "%Y-%m-%d %H:%M:%S"))


def parse_duration(duration):
    return float(duration[:-1])