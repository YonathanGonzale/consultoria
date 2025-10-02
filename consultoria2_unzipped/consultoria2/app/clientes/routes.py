from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required
from ..extensions import db
from ..models import Cliente

bp = Blueprint('clientes', __name__)

@bp.route('/')
@login_required
def list_clientes():
    q = request.args.get('q', '')
    query = Cliente.query
    if q:
        query = query.filter(Cliente.nombre_razon_social.ilike(f'%{q}%'))
    clientes = query.order_by(Cliente.nombre_razon_social.asc()).all()
    return render_template('clientes/list.html', clientes=clientes, q=q)

@bp.route('/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_cliente():
    if request.method == 'POST':
        c = Cliente(
            nombre_razon_social=request.form.get('nombre'),
            contacto=request.form.get('contacto'),
            ubicacion_general=request.form.get('ubicacion')
        )
        db.session.add(c)
        db.session.commit()
        return redirect(url_for('clientes.list_clientes'))
    return render_template('clientes/form.html')

@bp.route('/buscar')
@login_required
def buscar():
    q = request.args.get('q', '')
    clientes = []
    if q:
        clientes = Cliente.query.filter(Cliente.nombre_razon_social.ilike(f'%{q}%')).order_by(Cliente.nombre_razon_social.asc()).all()
    return render_template('clientes/search.html', q=q, clientes=clientes)

@bp.route('/<int:id_cliente>/instituciones')
@login_required
def instituciones(id_cliente):
    cliente = Cliente.query.get_or_404(id_cliente)
    instituciones = [
        {
        "key": "MADES",
        "full_name": "Ministerio del Ambiente y Desarrollo Sostenible",
        "logo": url_for('static', filename='img/logo_mades.png')
    },
    {
        "key": "SENAVE",
        "full_name": "Servicio Nacional de Calidad y Sanidad Vegetal y de Semillas",
        "logo": url_for('static', filename='img/logo_senave.png')
    },
    {
        "key": "INFONA",
        "full_name": "Instituto Forestal Nacional",
        "logo": url_for('static', filename='img/logo_infona.png')
    },
    ]
    return render_template('clientes/instituciones.html', cliente=cliente, instituciones=instituciones)

@bp.route('/<int:id_cliente>/institucion/<string:inst>')
@login_required
def institucion_detalle(id_cliente, inst):
    cliente = Cliente.query.get_or_404(id_cliente)
    tipos = [
    {
        "name": "EIA y EDE",
        "desc": "Evaluación de Impacto Ambiental y Estudio de disposición de Efluentes",
        "color": "success",
        "icon": "bi-tree-fill"
    },
    {
        "name": "AUDITORIAS",
        "desc": "Auditorías ambientales",
        "color": "danger",
        "icon": "bi-clipboard-check-fill"
    },
    {
        "name": "PGAG",
        "desc": "Plan de Gestión Ambiental Genérico",
        "color": "warning",
        "icon": "bi-people-fill"
    },
    {
        "name": "NO REQUIERE",
        "desc": "Nota de consulta",
        "color": "primary",
        "icon": "bi-x-circle-fill"
    }
]
    return render_template('clientes/institucion_detalle.html', cliente=cliente, institucion=inst, tipos=tipos)
