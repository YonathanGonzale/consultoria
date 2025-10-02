from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required
from ..models import Cliente, Proyecto, Propiedad
from ..extensions import db
from datetime import date

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
    cliente = Cliente.query.get_or_404(id_cliente)
    proyectos = Proyecto.query.filter_by(
        id_cliente=id_cliente, institucion="MADES"
    ).order_by(Proyecto.anho.desc(), Proyecto.id_proyecto.desc()).all()
    props = Propiedad.query.filter_by(id_cliente=id_cliente).all()

    estados = ["en proceso", "entregado", "finalizado", "pendiente"]
    cols = {e: [] for e in estados}
    for p in proyectos:
        e = (p.estado or "pendiente").lower()
        cols[e if e in cols else "pendiente"].append(p)

    return render_template(
        "mades/board.html",
        cliente=cliente,
        institucion="MADES",
        cols=cols,
        propiedades=props,
    )

# Crear proyecto rápido MADES
@bp.route("/crear", methods=["POST"])
@login_required
def crear():
    id_cliente = int(request.form["id_cliente"])
    anho = int(request.form.get("anho") or date.today().year)
    tipo_tramite = request.form.get("tipo_tramite")
    estado = request.form.get("estado") or "pendiente"
    id_propiedad = request.form.get("id_propiedad") or None
    fecha_firma = request.form.get("fecha_firma_contrato") or None
    plazo_limite = request.form.get("plazo_limite") or None

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
