from flask import Blueprint, render_template
from flask_login import login_required
from ..models import Cliente, Proyecto, Vencimiento
from ..extensions import db

bp = Blueprint('dashboard', __name__)

@bp.route('/')
@login_required
def index():
    total_clientes = db.session.query(Cliente).count()
    total_proyectos = db.session.query(Proyecto).count()
    proximos_venc = db.session.query(Vencimiento).order_by(Vencimiento.fecha_vencimiento.asc()).limit(5).all()
    return render_template('dashboard/index.html', total_clientes=total_clientes, total_proyectos=total_proyectos, proximos_venc=proximos_venc)
