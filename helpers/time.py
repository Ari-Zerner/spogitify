from datetime import datetime, timezone

def now() -> datetime:
    """Get current time in UTC."""
    return datetime.now(timezone.utc)

def format_time_since(dt):
    """Format time difference from now as a human readable string."""
    if not dt:
        return None
        
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    diff = now() - dt
    days = diff.days
    hours = diff.seconds // 3600
    minutes = (diff.seconds % 3600) // 60
    
    days_str = f"{days} {'day' if days == 1 else 'days'}"
    hours_str = f"{hours} {'hour' if hours == 1 else 'hours'}"
    minutes_str = f"{minutes} {'minute' if minutes == 1 else 'minutes'}"
    
    if days > 0:
        return f"{days_str}, {hours_str}, {minutes_str} ago"
    elif hours > 0:
        return f"{hours_str}, {minutes_str} ago"
    else:
        return f"{minutes_str} ago"