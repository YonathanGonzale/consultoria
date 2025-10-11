import os
from uuid import uuid4
from flask import Blueprint, render_template, request, redirect, url_for, current_app, flash, send_file, abort
from flask_login import login_required
from datetime import date
from ..extensions import db
from ..models import Cliente, Proyecto, DocumentoCliente
from sqlalchemy import or_
from werkzeug.utils import secure_filename

bp = Blueprint('clientes', __name__)

@bp.route('/')
@login_required
def list_clientes():
    q = request.args.get('q', '')
    query = Cliente.query
    if q:
        like = f'%{q}%'
        query = query.filter(
            or_(
                Cliente.nombre_razon_social.ilike(like),
                Cliente.cedula_identidad.ilike(like)
            )
        )
    clientes = query.order_by(Cliente.nombre_razon_social.asc()).all()
    return render_template('clientes/list.html', clientes=clientes, q=q)


ALLOWED_CLIENT_DOCS = {'.pdf', '.png', '.jpg', '.jpeg', '.gif', '.webp'}


def _cliente_upload_dir(cliente_id):
    base_upload = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    if not os.path.isabs(base_upload):
        base_upload = os.path.join(current_app.root_path, base_upload)
    target_dir = os.path.join(base_upload, 'clientes', str(cliente_id))
    os.makedirs(target_dir, exist_ok=True)
    return target_dir


def _guardar_documentos_cliente(cliente, archivos):
    if not archivos:
        return
    target_dir = _cliente_upload_dir(cliente.id_cliente)
    for archivo in archivos:
        if not archivo or not archivo.filename:
            continue
        ext = os.path.splitext(archivo.filename)[1].lower()
        if ext not in ALLOWED_CLIENT_DOCS:
            flash(f'Archivo no permitido: {archivo.filename}', 'warning')
            continue
        filename = secure_filename(archivo.filename)
        unique_name = f"{uuid4().hex}_{filename}"
        save_path = os.path.join(target_dir, unique_name)
        archivo.save(save_path)

        doc = DocumentoCliente(
            id_cliente=cliente.id_cliente,
            nombre_original=filename,
            archivo_url=save_path,
            mime_type=archivo.mimetype or ''
        )
        db.session.add(doc)


@bp.route('/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_cliente():
    if request.method == 'POST':
        c = Cliente(
            nombre_razon_social=request.form.get('nombre'),
            cedula_identidad=request.form.get('cedula'),
            contacto=request.form.get('contacto'),
            telefono=request.form.get('telefono'),
            correo_electronico=request.form.get('correo'),
            departamento=request.form.get('departamento'),
            distrito=request.form.get('distrito'),
            lugar=request.form.get('lugar'),
            ubicacion_general=request.form.get('ubicacion'),
            ubicacion_gps=request.form.get('ubicacion_gps')
        )
        db.session.add(c)
        db.session.commit()
        archivos = request.files.getlist('documentos')
        _guardar_documentos_cliente(c, archivos)
        db.session.commit()
        flash('Cliente creado correctamente', 'success')
        return redirect(url_for('clientes.list_clientes'))
    return render_template('clientes/form.html')

@bp.route('/buscar')
@login_required
def buscar():
    q = request.args.get('q', '')
    clientes = []
    if q:
        like = f'%{q}%'
        clientes = Cliente.query.filter(
            or_(
                Cliente.nombre_razon_social.ilike(like),
                Cliente.cedula_identidad.ilike(like)
            )
        ).order_by(Cliente.nombre_razon_social.asc()).all()
    return render_template('clientes/search.html', q=q, clientes=clientes)


@bp.route('/<int:id_cliente>/detalle', methods=['GET', 'POST'])
@login_required
def detalle_cliente(id_cliente):
    cliente = Cliente.query.get_or_404(id_cliente)
    if request.method == 'POST':
        archivos = request.files.getlist('documentos')
        _guardar_documentos_cliente(cliente, archivos)
        db.session.commit()
        flash('Documentos actualizados', 'success')
        return redirect(url_for('clientes.detalle_cliente', id_cliente=id_cliente))
    return render_template('clientes/detalle.html', cliente=cliente)


@bp.route('/<int:id_cliente>/documento/<int:id_doc>/descargar')
@login_required
def descargar_documento_cliente(id_cliente, id_doc):
    doc = DocumentoCliente.query.get_or_404(id_doc)
    if doc.id_cliente != id_cliente:
        abort(404)
    if not doc.archivo_url or not os.path.exists(doc.archivo_url):
        flash('Archivo no encontrado', 'danger')
        return redirect(url_for('clientes.detalle_cliente', id_cliente=id_cliente))
    return send_file(doc.archivo_url, as_attachment=True, download_name=doc.nombre_original or 'documento')


@bp.route('/<int:id_cliente>/documento/<int:id_doc>/eliminar', methods=['POST'])
@login_required
def eliminar_documento_cliente(id_cliente, id_doc):
    doc = DocumentoCliente.query.get_or_404(id_doc)
    if doc.id_cliente != id_cliente:
        abort(404)
    try:
        if doc.archivo_url and os.path.exists(doc.archivo_url):
            os.remove(doc.archivo_url)
    except Exception:
        pass
    db.session.delete(doc)
    db.session.commit()
    flash('Documento eliminado', 'success')
    return redirect(url_for('clientes.detalle_cliente', id_cliente=id_cliente))

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
