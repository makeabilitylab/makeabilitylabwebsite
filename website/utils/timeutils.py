from datetime import timedelta

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