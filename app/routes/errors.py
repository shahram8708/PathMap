from flask import render_template
from werkzeug.exceptions import HTTPException

# Template and title mapping for the common error codes we want to show.
ERROR_TEMPLATES = {
    403: ('errors/403.html', 'Access Denied'),
    404: ('errors/404.html', 'Page Not Found'),
    429: ('errors/429.html', 'Too Many Requests'),
    500: ('errors/500.html', 'Server Error'),
}


def register_error_handlers(app):
    def render_error(error):
        # HTTPException carries .code; any other exception is treated as 500.
        code = getattr(error, 'code', 500) or 500
        template, title = ERROR_TEMPLATES.get(code, ERROR_TEMPLATES[500])
        return render_template(template, title=title), code

    # Handle specific HTTP codes.
    for code in ERROR_TEMPLATES:
        app.register_error_handler(code, render_error)

    # Catch any other HTTPException (e.g., 400) and any uncaught Exception as 500.
    app.register_error_handler(HTTPException, render_error)
    app.register_error_handler(Exception, render_error)
