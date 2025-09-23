def format_change(value):
    """Format a numerical change with + or - sign and one decimal place."""
    if value is None:
        return "0.0%"
    if value > 0:
        return f"+{value:.1f}%"
    elif value < 0:
        return f"{value:.1f}%"
    return "0.0%"

def register_filters(app):
    """Register custom Jinja2 filters."""
    app.jinja_env.filters['format_change'] = format_change