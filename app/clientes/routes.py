import os
from uuid import uuid4
from flask import Blueprint, render_template, request, redirect, url_for, current_app, flash, send_file, abort
from flask_login import login_required
from datetime import date
from ..extensions import db
from ..models import Cliente, Proyecto, DocumentoCliente
from sqlalchemy import or_, func
from werkzeug.utils import secure_filename

bp = Blueprint('clientes', __name__)
PAGE_SIZE_OPTIONS = (10, 20, 30, 40, 50, 100)

@bp.route('/')
@login_required
def list_clientes():
    q = request.args.get('q', '')
    page = request.args.get('page', type=int, default=1)
    if page < 1:
        page = 1
    per_page = request.args.get('per_page', type=int, default=PAGE_SIZE_OPTIONS[0])
    if per_page not in PAGE_SIZE_OPTIONS:
        per_page = PAGE_SIZE_OPTIONS[0]
    sort_field = request.args.get('sort', 'nombre')
    sort_direction = request.args.get('direction', 'asc')
    if sort_direction not in ('asc', 'desc'):
        sort_direction = 'asc'

    query = Cliente.query
    if q:
        like = f'%{q}%'
        query = query.filter(
            or_(
                Cliente.nombre_razon_social.ilike(like),
                Cliente.cedula_identidad.ilike(like),
                Cliente.correo_electronico.ilike(like),
                Cliente.telefono.ilike(like),
            )
        )
    sort_columns = {
        'nombre': Cliente.nombre_razon_social,
        'cedula': Cliente.cedula_identidad,
        'correo': Cliente.correo_electronico,
        'telefono': Cliente.telefono,
        'departamento': Cliente.departamento,
    }
    if sort_field not in sort_columns:
        sort_field = 'nombre'
    order_column = sort_columns[sort_field]
    if sort_direction == 'asc':
        query = query.order_by(order_column.asc().nullslast(), Cliente.nombre_razon_social.asc())
    else:
        query = query.order_by(order_column.desc().nullslast(), Cliente.nombre_razon_social.desc())

    pagination = query.paginate(
        page=page,
        per_page=per_page,
        error_out=False,
    )
    clientes = pagination.items
    common_params = {
        'q': q,
        'per_page': per_page,
        'sort': sort_field,
        'direction': sort_direction,
    }

    def _build_url(**extra):
        params = {k: v for k, v in common_params.items() if v}
        params.update({k: v for k, v in extra.items() if v is not None})
        return url_for('clientes.list_clientes', **params)

    template_kwargs = {
        'clientes': clientes,
        'q': q,
        'pagination': pagination,
        'per_page_options': PAGE_SIZE_OPTIONS,
        'sort_field': sort_field,
        'sort_direction': sort_direction,
        'build_client_url': _build_url,
    }

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('clientes/_results.html', **template_kwargs)

    return render_template('clientes/list.html', **template_kwargs)


ALLOWED_CLIENT_DOCS = {'.pdf', '.png', '.jpg', '.jpeg', '.gif', '.webp'}


MODULE_DEFINITIONS = {
    'MADES': {
        'label': 'MADES',
        'full_name': 'Ministerio del Ambiente y Desarrollo Sostenible',
        'logo': 'img/logo_mades.png',
        'color': 'success',
        'icon': 'bi-building'
    },
    'INFONA': {
        'label': 'INFONA',
        'full_name': 'Instituto Forestal Nacional',
        'logo': 'img/logo_infona.png',
        'color': 'teal',
        'icon': 'bi-tree'
    },
    'SENAVE': {
        'label': 'SENAVE',
        'full_name': 'Servicio Nacional de Calidad y Sanidad Vegetal y de Semillas',
        'logo': 'img/logo_senave.png',
        'color': 'info',
        'icon': 'bi-flower3'
    },
    'Asesoría Jurídica': {
        'label': 'Asesoría Jurídica',
        'full_name': 'Asesoría Jurídica',
        'logo': 'img/logo_cliente.png',
        'color': 'primary',
        'icon': 'bi-briefcase'
    },
    'Certificado de Servicios Ambientales': {
        'label': 'Certificado de Servicios Ambientales',
        'full_name': 'Certificados de Servicios Ambientales',
        'logo': 'img/logo_cliente.png',
        'color': 'warning',
        'icon': 'bi-award'
    },
    'Otros': {
        'label': 'Otros',
        'full_name': 'Otros Módulos',
        'logo': 'img/logo_cliente.png',
        'color': 'secondary',
        'icon': 'bi-grid'
    },
}


def _module_meta(key):
    if not key:
        key = 'Otros'
    data = MODULE_DEFINITIONS.get(key, MODULE_DEFINITIONS['Otros'])
    data = data.copy()
    data['key'] = key
    data['logo_url'] = url_for('static', filename=data['logo'])
    return data


def _optional(form, name):
    value = form.get(name)
    if value is None:
        return None
    value = value.strip()
    return value or None


def _normalize_subtipo(value):
    if value is None:
        return 'Otros'
    normalized = value.strip()
    return normalized or 'Otros'


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
            cedula_identidad=_optional(request.form, 'cedula'),
            telefono=_optional(request.form, 'telefono'),
            correo_electronico=_optional(request.form, 'correo'),
            departamento=_optional(request.form, 'departamento'),
            distrito=_optional(request.form, 'distrito'),
            lugar=_optional(request.form, 'lugar'),
            ubicacion_general=_optional(request.form, 'ubicacion'),
            ubicacion_gps=_optional(request.form, 'ubicacion_gps')
        )
        db.session.add(c)
        db.session.commit()
        archivos = request.files.getlist('documentos')
        _guardar_documentos_cliente(c, archivos)
        db.session.commit()
        flash('Cliente creado correctamente', 'success')
        return redirect(url_for('clientes.list_clientes'))
    return render_template('clientes/form.html')


@bp.route('/<int:id_cliente>/editar', methods=['GET', 'POST'])
@login_required
def editar_cliente(id_cliente):
    cliente = Cliente.query.get_or_404(id_cliente)
    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        if not nombre:
            flash('El nombre/razón social es obligatorio.', 'danger')
            return redirect(url_for('clientes.editar_cliente', id_cliente=id_cliente))

        cliente.nombre_razon_social = nombre
        cliente.cedula_identidad = _optional(request.form, 'cedula')
        cliente.telefono = _optional(request.form, 'telefono')
        cliente.correo_electronico = _optional(request.form, 'correo')
        cliente.departamento = _optional(request.form, 'departamento')
        cliente.distrito = _optional(request.form, 'distrito')
        cliente.lugar = _optional(request.form, 'lugar')
        cliente.ubicacion_general = _optional(request.form, 'ubicacion')
        cliente.ubicacion_gps = _optional(request.form, 'ubicacion_gps')
        db.session.commit()
        flash('Cliente actualizado correctamente', 'success')
        return redirect(url_for('clientes.modulos', id_cliente=id_cliente))
    return render_template('clientes/edit.html', cliente=cliente)

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


@bp.route('/<int:id_cliente>/documento/<int:id_doc>/ver')
@login_required
def ver_documento_cliente(id_cliente, id_doc):
    doc = DocumentoCliente.query.get_or_404(id_doc)
    if doc.id_cliente != id_cliente:
        abort(404)
    if not doc.archivo_url or not os.path.exists(doc.archivo_url):
        flash('Archivo no encontrado', 'danger')
        return redirect(url_for('clientes.detalle_cliente', id_cliente=id_cliente))
    return send_file(doc.archivo_url, as_attachment=False, download_name=doc.nombre_original or 'documento')


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

@bp.route('/<int:id_cliente>/modulos')
@login_required
def modulos(id_cliente):
    cliente = Cliente.query.get_or_404(id_cliente)
    module_rows = (
        db.session.query(Proyecto.institucion, func.count(Proyecto.id_proyecto))
        .filter(Proyecto.id_cliente == id_cliente)
        .group_by(Proyecto.institucion)
        .all()
    )

    project_counts = {inst or 'Otros': count for inst, count in module_rows}

    preferred_order = ['MADES', 'SENAVE', 'INFONA', 'Asesoría Jurídica']
    seen = set()
    modules = []

    def _append_module(key):
        meta = _module_meta(key)
        modules.append({
            'key': meta['key'],
            'label': meta['label'],
            'full_name': meta['full_name'],
            'logo': meta['logo_url'],
            'color': meta['color'],
            'icon': meta['icon'],
            'count': project_counts.get(meta['key'], 0),
            'url': url_for('clientes.modulo_subtipos', id_cliente=id_cliente, inst=meta['key']),
        })
        seen.add(meta['key'])

    for preferred in preferred_order:
        if preferred in MODULE_DEFINITIONS:
            _append_module(preferred)

    for key in MODULE_DEFINITIONS.keys():
        if key not in seen:
            _append_module(key)

    total_proyectos = sum(project_counts.values())
    create_project_url = url_for('proyectos.nuevo') + f'?id_cliente={id_cliente}'

    return render_template(
        'clientes/instituciones.html',
        cliente=cliente,
        modules=modules,
        total_proyectos=total_proyectos,
        no_projects=len(modules) == 0,
        create_project_url=create_project_url,
    )


def _subtipo_filter(query, inst, subtipo):
    inst = inst or 'Otros'
    query = query.filter(Proyecto.institucion == inst)
    normalized = _normalize_subtipo(subtipo)
    if normalized.lower() == 'otros':
        query = query.filter(
            or_(
                Proyecto.subtipo.is_(None),
                Proyecto.subtipo == '',
                Proyecto.subtipo.ilike('otros')
            )
        )
    else:
        query = query.filter(Proyecto.subtipo == normalized)
    return query, normalized


@bp.route('/<int:id_cliente>/modulo/<string:inst>/subtipos')
@login_required
def modulo_subtipos(id_cliente, inst):
    cliente = Cliente.query.get_or_404(id_cliente)
    meta = _module_meta(inst)

    rows = (
        db.session.query(Proyecto.subtipo, func.count(Proyecto.id_proyecto))
        .filter(Proyecto.id_cliente == id_cliente, Proyecto.institucion == meta['key'])
        .group_by(Proyecto.subtipo)
        .all()
    )

    preferred_order = []
    if meta['key'] == 'MADES':
        preferred_order = [
            'EIA',
            'Auditorías',
            'PGAG',
            'Plan de ajuste Ambiental',
            'Certificado de No Requiere',
            'Certificación de Servicios Ambientales',
            'Otros',
        ]

    def _sort_key(item):
        nombre = item['name']
        if preferred_order:
            try:
                index = preferred_order.index(nombre)
                return (0, index)
            except ValueError:
                pass
        return (1, nombre.lower())

    subtipos = []
    total_subtipos = 0
    for raw_subtipo, cantidad in rows:
        nombre = (raw_subtipo or 'Otros').strip() or 'Otros'
        subtipos.append({
            'name': nombre,
            'count': cantidad,
            'url': url_for('clientes.modulo_subtipo_anhos', id_cliente=id_cliente, inst=meta['key'], subtipo=nombre)
        })
        total_subtipos += 1

    subtipos.sort(key=_sort_key)

    create_project_url = url_for('proyectos.nuevo') + f'?id_cliente={id_cliente}&institucion={meta["key"]}'

    return render_template(
        'clientes/institucion_detalle.html',
        cliente=cliente,
        modulo=meta,
        subtipos=subtipos,
        total_subtipos=total_subtipos,
        no_subtipos=len(subtipos) == 0,
        create_project_url=create_project_url
    )


@bp.route('/<int:id_cliente>/modulo/<string:inst>/subtipo/<path:subtipo>/anhos')
@login_required
def modulo_subtipo_anhos(id_cliente, inst, subtipo):
    cliente = Cliente.query.get_or_404(id_cliente)
    meta = _module_meta(inst)
    subtipo_label = _normalize_subtipo(subtipo)

    base_query = db.session.query(Proyecto.anho).filter(Proyecto.id_cliente == id_cliente)
    base_query, normalized_subtipo = _subtipo_filter(base_query, meta['key'], subtipo_label)
    anos_rows = (
        base_query
        .filter(Proyecto.anho.isnot(None))
        .distinct()
        .order_by(Proyecto.anho.desc())
        .all()
    )
    anos = [row[0] for row in anos_rows]

    create_project_url = (
        url_for('proyectos.nuevo')
        + f'?id_cliente={id_cliente}&institucion={meta["key"]}&subtipo={normalized_subtipo}'
    )

    return render_template(
        'clientes/periodos.html',
        cliente=cliente,
        modulo=meta,
        subtipo=normalized_subtipo,
        anos=anos,
        no_anos=len(anos) == 0,
        create_project_url=create_project_url
    )
