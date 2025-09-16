from flask import Blueprint

bp = Blueprint('vencimientos', __name__, url_prefix='/vencimientos')

from . import routes