from datetime import timedelta
import re

def humanize_duration(duration, sig_figs=1, use_abbreviated_units=False):
    # Convert the duration to fractional years, months, or weeks
    duration_str = ""
    if duration >= timedelta(days=365):
        # If the duration is more than or equal to 1 year, convert it to fractional years
        total_time_in_years = duration.total_seconds() / (60 * 60 * 24 * 365)
        duration_str = f"{total_time_in_years:.{sig_figs}f}"
        duration_str += " years" if not use_abbreviated_units else " yrs" 
    elif duration >= timedelta(days=30):
        # If the duration is more than or equal to 1 month but less than 1 year, convert it to fractional months
        total_time_in_months = duration.total_seconds() / (60 * 60 * 24 * 30)
        duration_str = f"{total_time_in_months:.{sig_figs}f}"
        duration_str += " months" if not use_abbreviated_units else " mos"
    else:
        # If the duration is less than 1 month, convert it to fractional weeks
        total_time_in_weeks = duration.total_seconds() / (60 * 60 * 24 * 7)
        duration_str = f"{total_time_in_weeks:.{sig_figs}f}"

        duration_str += " weeks" if not use_abbreviated_units else " wks"
    
    return duration_str

def ends_with_year(s):
    """Check if the string s ends with a four-digit year"""

    # The following regex included a `\b` word boundary anchor. So, it ensures that the
    # four-digit number is a separate word. We don't want that. 
    # Old: if re.search(r'\b\d{4}\b$', s):
    # This regex is simpler, it simply has `\d{4}$` which matches exactly four digits
    # and '$', which asserts that the match position be at the end of the string
    if re.search(r'\d{4}$', s):
        return True
    return False

def remove_trailing_year(s):
    """Check if the string s ends with a four-digit year. If so, remove it."""

    # Check if the string ends with a four-digit year
    match = re.search(r'\d{4}$', s)
    if match:
        # Remove the year and any trailing whitespace
        return s[:match.start()].rstrip()
    return s