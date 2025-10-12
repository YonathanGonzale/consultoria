from flask import Blueprint, render_template
from flask_login import login_required
from ..models import Cliente, Proyecto
from ..extensions import db
from datetime import date

bp = Blueprint('dashboard', __name__)

@bp.route('/')
@login_required
def index():
    total_clientes = db.session.query(Cliente).count()
    proximos_proyectos = (
        db.session.query(Proyecto)
        .filter(Proyecto.fecha_vencimiento_licencia.isnot(None))
        .order_by(Proyecto.fecha_vencimiento_licencia.asc())
        .limit(10)
        .all()
    )

    hoy = date.today()
    proximos_items = []
    for proyecto in proximos_proyectos:
        dias_restantes = (proyecto.fecha_vencimiento_licencia - hoy).days
        if dias_restantes <= 30:
            badge_class = 'bg-danger'
        elif dias_restantes <= 60:
            badge_class = 'bg-warning text-dark'
        elif dias_restantes <= 90:
            badge_class = 'bg-success'
        else:
            badge_class = 'bg-secondary'

        proximos_items.append({
            'proyecto': proyecto,
            'dias_restantes': dias_restantes,
            'badge_class': badge_class,
        })

    return render_template(
        'dashboard/index.html',
        total_clientes=total_clientes,
        proximos_items=proximos_items,
    )

