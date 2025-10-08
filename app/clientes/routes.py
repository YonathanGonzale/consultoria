from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required
from datetime import date
from ..extensions import db
from ..models import Cliente, Proyecto

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
        "key": "INFONA",
        "full_name": "Instituto Forestal Nacional",
        "logo": url_for('static', filename='img/logo_infona.png')
    },
    {
        "key": "SENAVE",
        "full_name": "Servicio Nacional de Calidad y Sanidad Vegetal y de Semillas",
        "logo": url_for('static', filename='img/logo_senave.png')
    },
    {
        "key": "Otros",
        "full_name": "Otras Instituciones",
        "logo": url_for('static', filename='img/logo_cliente.png')
    },
    ]
    return render_template('clientes/instituciones.html', cliente=cliente, instituciones=instituciones)

@bp.route('/<int:id_cliente>/institucion/<string:inst>')
@login_required
def institucion_detalle(id_cliente, inst):
    cliente = Cliente.query.get_or_404(id_cliente)
    tipos = [
    {
        "name": "EIA",
        "desc": "Evaluación de Impacto Ambiental",
        "color": "success",
        "icon": "bi-tree-fill"
    },
    {
        "name": "Auditoría",
        "desc": "Auditorías ambientales",
        "color": "danger",
        "icon": "bi-clipboard-check-fill"
    },
    {
        "name": "Informe técnico",
        "desc": "Informes técnicos especializados",
        "color": "warning",
        "icon": "bi-file-text-fill"
    },
    {
        "name": "Registro de silo",
        "desc": "Registro y habilitación de silos",
        "color": "info",
        "icon": "bi-building-fill"
    },
    {
        "name": "Otros",
        "desc": "Otros tipos de trámites",
        "color": "secondary",
        "icon": "bi-three-dots"
    }
]
    return render_template('clientes/institucion_detalle.html', cliente=cliente, institucion=inst, tipos=tipos)

# Nuevas rutas basadas en consultoria-main
@bp.route('/<int:id_cliente>/periodos')
@login_required
def seleccionar_periodo(id_cliente):
    cliente = Cliente.query.get_or_404(id_cliente)

    anos_disponibles = db.session.query(Proyecto.anho).filter_by(id_cliente=id_cliente).distinct().order_by(Proyecto.anho.desc()).all()
    anos = [ano[0] for ano in anos_disponibles if ano[0]]
    if not anos:
        ano_actual = date.today().year
        anos = [ano_actual, ano_actual - 1, ano_actual - 2]

    return render_template('clientes/periodos.html', cliente=cliente, anos=anos)


@bp.route('/<int:id_cliente>/ano/<int:ano>/instituciones')
@login_required
def instituciones_por_ano(id_cliente, ano):
    cliente = Cliente.query.get_or_404(id_cliente)

    instituciones_con_proyectos = db.session.query(Proyecto.institucion).filter_by(
        id_cliente=id_cliente, anho=ano
    ).distinct().all()
    instituciones_activas = [inst[0] for inst in instituciones_con_proyectos if inst[0]]

    todas_instituciones = [
        {
            "key": "MADES",
            "full_name": "Ministerio del Ambiente y Desarrollo Sostenible",
            "logo": url_for('static', filename='img/logo_mades.png')
        },
        {
            "key": "INFONA",
            "full_name": "Instituto Forestal Nacional",
            "logo": url_for('static', filename='img/logo_infona.png')
        },
        {
            "key": "SENAVE",
            "full_name": "Servicio Nacional de Calidad y Sanidad Vegetal y de Semillas",
            "logo": url_for('static', filename='img/logo_senave.png')
        },
        {
            "key": "Otros",
            "full_name": "Otras Instituciones",
            "logo": url_for('static', filename='img/logo_cliente.png')
        },
    ]

    for inst in todas_instituciones:
        inst['tiene_proyectos'] = inst['key'] in instituciones_activas

    return render_template('clientes/instituciones.html', cliente=cliente, instituciones=todas_instituciones, ano=ano)


@bp.route('/<int:id_cliente>/ano/<int:ano>/institucion/<string:inst>')
@login_required
def institucion_detalle_por_ano(id_cliente, ano, inst):
    cliente = Cliente.query.get_or_404(id_cliente)

    tipos_con_proyectos = db.session.query(Proyecto.tipo_tramite).filter_by(
        id_cliente=id_cliente, anho=ano, institucion=inst
    ).distinct().all()
    tipos_activos = [tipo[0] for tipo in tipos_con_proyectos if tipo[0]]

    todos_tipos = [
        {
            "name": "EIA",
            "desc": "Evaluación de Impacto Ambiental",
            "color": "success",
            "icon": "bi-tree-fill"
        },
        {
            "name": "Auditoría",
            "desc": "Auditorías ambientales",
            "color": "danger",
            "icon": "bi-clipboard-check-fill"
        },
        {
            "name": "Informe técnico",
            "desc": "Informes técnicos especializados",
            "color": "warning",
            "icon": "bi-file-text-fill"
        },
        {
            "name": "Registro de silo",
            "desc": "Registro y habilitación de silos",
            "color": "info",
            "icon": "bi-building-fill"
        },
        {
            "name": "Otros",
            "desc": "Otros tipos de trámites",
            "color": "secondary",
            "icon": "bi-three-dots"
        }
    ]

    for tipo in todos_tipos:
        tipo['tiene_proyectos'] = tipo['name'] in tipos_activos

    return render_template('clientes/institucion_detalle.html', cliente=cliente, institucion=inst, tipos=todos_tipos, ano=ano)
