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
    hoy = date.today()
    proyectos = (
        db.session.query(Proyecto)
        .filter(Proyecto.fecha_vencimiento_licencia.isnot(None))
        .all()
    )

    def _orden_proximidad(proyecto):
        dias = (proyecto.fecha_vencimiento_licencia - hoy).days
        if dias < 0:
            return (0, dias, proyecto.fecha_vencimiento_licencia)
        return (1, dias, proyecto.fecha_vencimiento_licencia)

    proximos_items = []
    for proyecto in sorted(proyectos, key=_orden_proximidad):
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

