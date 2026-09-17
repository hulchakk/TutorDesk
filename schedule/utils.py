from datetime import datetime


def get_week_str(dt: datetime) -> str:
    return dt.strftime("%G-W%V")
