from datetime import datetime

from django.utils import timezone


def get_week_str(dt: datetime) -> str:
    # Convert to local time first: a late-evening lesson stored in UTC can fall on the next ISO week.
    return timezone.localtime(dt).strftime("%G-W%V")
