from datetime import date, datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required

from ..extensions import db
from ..models import Cliente, Proyecto, ProyectoEstado

bp = Blueprint("mades", __name__, url_prefix="/mades")

MADES_ESTADOS = {
    'en_proceso': ProyectoEstado.en_proceso,
    'licencia_emitida': ProyectoEstado.licencia_emitida,
}

MADES_SUBTIPOS = [
    'EIA',
    'Auditorías',
    'PGAG',
    'Certificado de No Requiere',
    'Certificación de Servicios Ambientales',
    'Otros',
]


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


@bp.route("/")
@login_required
def index():
    proyectos = Proyecto.query.filter_by(institucion="MADES").order_by(
        Proyecto.anho.desc(), Proyecto.id_proyecto.desc()
    ).all()
    return render_template("mades/index.html", proyectos=proyectos, estados=MADES_ESTADOS)


@bp.route("/cliente/<int:id_cliente>")
@login_required
def cliente_board(id_cliente):
    return redirect(url_for('proyectos.board', id_cliente=id_cliente, inst='MADES'))


@bp.route("/crear", methods=["POST"])
@login_required
def crear():
    form = request.form
    id_cliente = form.get("id_cliente")
    if not id_cliente:
        flash("Seleccioná un cliente válido.", "danger")
        return redirect(request.referrer or url_for("mades.index"))

    anho = int(form.get("anho") or date.today().year)
    subtipo = form.get("subtipo") or form.get("tipo_tramite") or "Otros"
    estado_raw = (form.get("estado") or "en_proceso").strip().lower()

    raw_emision = form.get("fecha_emision_licencia")
    emision = _parse_date(raw_emision)
    if raw_emision and not emision:
        flash("Ingresá una fecha válida de emisión de licencia.", "danger")
        return redirect(request.referrer or url_for("mades.index"))

    proyecto = Proyecto(
        id_cliente=int(id_cliente),
        institucion="MADES",
        anho=anho,
        subtipo=subtipo,
        nombre_proyecto=form.get("nombre_proyecto") or f"{subtipo} {anho}",
    )
    proyecto.estado = MADES_ESTADOS.get(estado_raw, ProyectoEstado.en_proceso)
    proyecto.anio_inicio = anho
    proyecto.exp_siam = form.get("exp_siam") or None
    proyecto.fecha_emision_licencia = emision
    proyecto.fecha_vencimiento_licencia = _parse_date(form.get("fecha_vencimiento_licencia"))
    proyecto.costo_total = None
    proyecto.porcentaje_entrega = None
    proyecto.actualizar_finanzas()

    db.session.add(proyecto)
    db.session.commit()

    return redirect(url_for("mades.cliente_board", id_cliente=proyecto.id_cliente))
