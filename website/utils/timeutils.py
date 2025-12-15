from datetime import timedelta
import re

def humanize_duration(duration, sig_figs=1, use_abbreviated_units=False):
    """Convert the duration to fractional years, months, weeks, or days"""
    duration_str = ""
    total_seconds = duration.total_seconds()
    
    if duration >= timedelta(days=365):
        val = total_seconds / (60 * 60 * 24 * 365)
        unit = "yrs" if use_abbreviated_units else "years"
    elif duration >= timedelta(days=30):
        val = total_seconds / (60 * 60 * 24 * 30)
        unit = "mos" if use_abbreviated_units else "months"
    elif duration >= timedelta(days=7):
        val = total_seconds / (60 * 60 * 24 * 7)
        unit = "wks" if use_abbreviated_units else "weeks"
    else:
        # Fallback for durations less than a week
        val = total_seconds / (60 * 60 * 24)
        unit = "days" # You could abbreviate to 'd' if preferred

    # Simple logic to remove ".0" if sig_figs is 0 or if you prefer clean integers
    duration_str = f"{val:.{sig_figs}f} {unit}"
    return duration_str

def ends_with_year(s):
    """Check if the string s ends with a four-digit year"""
    if s is None:
        return False

    # Note: \d{4}$ is greedy. It will match "User1234" as having a year.
    if re.search(r'\d{4}$', s):
        return True
    return False

def remove_trailing_year(s):
    """Check if the string s ends with a four-digit year. If so, remove it."""
    if s is None:
        return "" # or return None, depending on preference

    match = re.search(r'\d{4}$', s)
    if match:
        # Remove the year and any trailing whitespace
        return s[:match.start()].rstrip()
    return s