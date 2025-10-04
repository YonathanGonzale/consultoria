from flask import Blueprint
from flask_login import login_required

bp = Blueprint('propiedades', __name__)

@bp.route('/')
@login_required
def index():
    return 'Propiedades (en construcción)'
