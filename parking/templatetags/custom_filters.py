from django import template
from django.utils.timesince import timesince
from django.utils.timezone import now

register = template.Library()

@register.filter
def custom_timesince(value, current_time=None):
    if current_time is None:
        current_time = now()

    time_difference = timesince(value, current_time)

    segments = time_difference.split(', ')

    if "minute" in segments[0]:
        minutes = int(segments[0].split()[0])
        if minutes <= 0:
            return "Just now"
        elif minutes == 1:
            return "1 minute ago"
        else:
            return f"{minutes} minutes ago"
    elif "hour" in segments[0]:
        hours = int(segments[0].split()[0])
        if hours == 1:
            return "1 hour ago"
        else:
            return f"{hours} hours ago"
    elif "day" in segments[0]:
        days = int(segments[0].split()[0])
        if days == 1:
            return "1 day ago"
        else:
            return f"{days} days ago"
    elif "week" in segments[0]:
        weeks = int(segments[0].split()[0])
        if weeks == 1:
            return "1 week ago"
        else:
            return f"{weeks} weeks ago"
    elif "month" in segments[0]:
        months = int(segments[0].split()[0])
        if months == 1:
            return "1 month ago"
        else:
            return f"{months} months ago"
    elif "year" in segments[0]:
        years = int(segments[0].split()[0])
        if years == 1:
            return "1 year ago"
        else:
            return f"{years} years ago"
    else:
        return "Just now"