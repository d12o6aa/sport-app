from flask import Blueprint

coach_bp = Blueprint('coach', __name__)

from . import coach, views,manage_athlete