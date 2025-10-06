# app/utils/decorators.py
from functools import wraps
from flask import redirect, url_for
from flask_jwt_extended import get_jwt_identity, jwt_required
from app.models.user import User

def inject_user_to_template(view_func):
    """
    A decorator to get the current user and inject it into the template context.
    Requires a valid JWT token.
    """
    @wraps(view_func)
    @jwt_required()
    def wrapper(*args, **kwargs):
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user:
            # Handle case where user is not found
            return redirect(url_for('auth.login')) 
        
        # Pass the user object as a keyword argument to the view function
        kwargs['current_user'] = user
        return view_func(*args, **kwargs)
    return wrapper