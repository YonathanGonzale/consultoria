from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required
from ..models import Cliente, Proyecto, Propiedad
from ..extensions import db
from datetime import date, datetime

bp = Blueprint("mades", __name__, url_prefix="/mades")

# Listado general de proyectos MADES
@bp.route("/")
@login_required
def index():
    proyectos = Proyecto.query.filter_by(institucion="MADES").order_by(
        Proyecto.anho.desc(), Proyecto.id_proyecto.desc()
    ).all()
    return render_template("mades/index.html", proyectos=proyectos)

# Tablero (Kanban) por cliente
@bp.route("/cliente/<int:id_cliente>")
@login_required
def cliente_board(id_cliente):
    # Redirigimos al tablero unificado de proyectos usando inst='MADES'
    return redirect(url_for('proyectos.board', id_cliente=id_cliente, inst='MADES'))

# Crear proyecto rápido MADES
@bp.route("/crear", methods=["POST"])
@login_required
def crear():
    id_cliente = int(request.form["id_cliente"])
    anho = int(request.form.get("anho") or date.today().year)
    tipo_tramite = request.form.get("tipo_tramite")
    estado = request.form.get("estado") or "pendiente"
    id_propiedad_raw = request.form.get("id_propiedad") or None
    id_propiedad = int(id_propiedad_raw) if id_propiedad_raw else None

    # Parseo de fechas (esperado input type=date -> YYYY-MM-DD)
    def _parse_date(val):
        if not val:
            return None
        try:
            return datetime.strptime(val, "%Y-%m-%d").date()
        except ValueError:
            return None

    fecha_firma = _parse_date(request.form.get("fecha_firma_contrato"))
    plazo_limite = _parse_date(request.form.get("plazo_limite"))

    proyecto = Proyecto(
        id_cliente=id_cliente,
        institucion="MADES",
        anho=anho,
        tipo_tramite=tipo_tramite,
        estado=estado,
        id_propiedad=id_propiedad,
        fecha_firma_contrato=fecha_firma,
        plazo_limite=plazo_limite,
    )
    db.session.add(proyecto)
    db.session.commit()

    return redirect(url_for("mades.cliente_board", id_cliente=id_cliente))
