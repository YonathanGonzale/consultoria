import os
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from uuid import uuid4

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
    current_app,
    send_file,
    abort,
)
from flask_login import login_required
from werkzeug.utils import secure_filename

from sqlalchemy import or_

from ..extensions import db
from ..models import (
    Proyecto,
    Cliente,
    Propiedad,
    DocumentoProyecto,
    ProyectoEstado,
)

bp = Blueprint('proyectos', __name__)
PAGE_SIZE_OPTIONS = (10, 20, 30, 40, 50, 100)

MADES_SUBTIPOS = [
    ('EIA', 'Evaluación de Impacto Ambiental Preliminar'),
    ('Auditorías', 'Auditorías'),
    ('PGAG', 'Plan de Gestión Ambiental Genérico'),
    ('Certificado de No Requiere', 'Certificado de No Requiere'),
    ('Certificación de Servicios Ambientales', 'Certificación de Servicios Ambientales'),
    ('Otros', 'Otros'),
]

MODULE_SUBTIPOS = {
    'MADES': MADES_SUBTIPOS,
    'INFONA': [
        ('Parecer Técnico', 'Parecer Técnico'),
        ('Registro de Bosque', 'Registro de Bosque'),
        ('Otros', 'Otros'),
    ],
    'SENAVE': [
        ('Registro de Silo', 'Registro de Silo'),
        ('Registro de Importador Vegetal', 'Registro de Importador Vegetal'),
        ('Registro de Semillas', 'Registro de Semillas'),
        ('Entidades Comerciales', 'Entidades Comerciales'),
        ('Otros', 'Otros'),
    ],
    'Asesoría Jurídica': [
        ('Acta de Inversión', 'Acta de Inversión'),
        ('Cédula de Notificación', 'Cédula de Notificación'),
        ('Conclusión de Sumario', 'Conclusión de Sumario'),
        ('Recibo de Pago de Multa', 'Recibo de Pago de Multa'),
        ('Otros', 'Otros'),
    ],
    'Certificado de Servicios Ambientales': [
        ('Certificación', 'Certificación'),
        ('Renovación', 'Renovación'),
        ('Otros', 'Otros'),
    ],
}

ALLOWED_DOCUMENT_EXT = {'.pdf', '.png', '.jpg', '.jpeg', '.gif', '.webp', '.doc', '.docx', '.xlsx', '.zip', '.rar', '.shp'}
IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.webp'}

ESTADOS_LIST = [
    ProyectoEstado.en_proceso,
    ProyectoEstado.licencia_emitida,
]
ESTADOS_POR_VALOR = {estado.value: estado for estado in ESTADOS_LIST}
ESTADO_LABELS = {
    'en_proceso': 'En proceso',
    'licencia_emitida': 'Licencia emitida',
}


def _parse_int(value, default=None):
    try:
        if value is None or str(value).strip() == '':
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _parse_decimal(value):
    if value is None:
        return None
    text = str(value).strip().replace(',', '.')
    if text == '':
        return None
    try:
        return Decimal(text)
    except (InvalidOperation, ValueError):
        return None


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except ValueError:
        return None


def _resolve_estado(raw_value):
    if not raw_value:
        return ProyectoEstado.en_proceso
    key = raw_value.strip().lower()
    return ESTADOS_POR_VALOR.get(key, ProyectoEstado.en_proceso)


def _upload_root():
    base_upload = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    if not os.path.isabs(base_upload):
        base_upload = os.path.join(current_app.root_path, base_upload)
    os.makedirs(base_upload, exist_ok=True)
    return base_upload


def _project_folder(proyecto, categoria=None):
    parts = [
        str(proyecto.id_cliente or 'sin_cliente'),
        (proyecto.institucion or 'otros').replace(' ', '_').lower(),
        str(proyecto.anho or 'sin_anho'),
        str(proyecto.id_proyecto or 'tmp'),
    ]
    target = os.path.join(_upload_root(), *parts)
    if categoria:
        target = os.path.join(target, categoria)
    os.makedirs(target, exist_ok=True)
    return target


def _relative_path(absolute_path):
    if not absolute_path:
        return None
    root = _upload_root()
    try:
        return os.path.relpath(absolute_path, root)
    except ValueError:
        # Cuando los discos difieren mantenemos absoluta
        return absolute_path


def _absolute_path(stored_path):
    if not stored_path:
        return None
    if os.path.isabs(stored_path) and os.path.exists(stored_path):
        return stored_path
    candidate = os.path.join(_upload_root(), stored_path)
    if os.path.exists(candidate):
        return candidate
    return stored_path if os.path.exists(stored_path) else None


def _remove_file(stored_path):
    abs_path = _absolute_path(stored_path)
    if abs_path and os.path.exists(abs_path):
        try:
            os.remove(abs_path)
        except OSError:
            pass


def _save_project_document(proyecto, file_storage, categoria='documento'):
    if not file_storage or not file_storage.filename:
        return None
    ext = os.path.splitext(file_storage.filename)[1].lower()
    if ext not in ALLOWED_DOCUMENT_EXT:
        raise ValueError(f"Extensión no permitida ({ext})")

    folder = _project_folder(proyecto, categoria)
    original_name = secure_filename(file_storage.filename)
    unique_name = f"{uuid4().hex}{ext}"
    absolute_target = os.path.join(folder, unique_name)
    file_storage.save(absolute_target)

    relative = _relative_path(absolute_target)
    doc = DocumentoProyecto(
        id_proyecto=proyecto.id_proyecto,
        tipo=categoria,
        categoria=categoria,
        archivo_url=relative,
        nombre_original=original_name,
        mime_type=file_storage.mimetype,
    )
    db.session.add(doc)
    return relative


def _clear_documents(proyecto, categoria):
    for doc in list(proyecto.documentos):
        if doc.categoria == categoria:
            _remove_file(doc.archivo_url)
            db.session.delete(doc)


def _fill_project_from_form(proyecto, form_data):
    proyecto.id_cliente = _parse_int(form_data.get('id_cliente'), proyecto.id_cliente)
    proyecto.anho = _parse_int(form_data.get('anho'), proyecto.anho or date.today().year)
    proyecto.institucion = form_data.get('institucion') or proyecto.institucion
    proyecto.nombre_proyecto = form_data.get('nombre_proyecto') or proyecto.nombre_proyecto
    proyecto.subtipo = form_data.get('subtipo') or proyecto.subtipo
    proyecto.anio_inicio = proyecto.anho
    proyecto.exp_siam = form_data.get('exp_siam') or None
    proyecto.fecha_emision_licencia = _parse_date(form_data.get('fecha_emision_licencia'))
    proyecto.fecha_vencimiento_licencia = _parse_date(form_data.get('fecha_vencimiento_licencia'))
    if 'id_propiedad' in form_data:
        proyecto.id_propiedad = _parse_int(form_data.get('id_propiedad'))

    proyecto.costo_total = _parse_decimal(form_data.get('costo_total'))
    proyecto.porcentaje_entrega = _parse_decimal(form_data.get('porcentaje_entrega'))

    monto_entregado_manual = _parse_decimal(form_data.get('monto_entregado'))
    if monto_entregado_manual is not None:
        proyecto.monto_entregado = monto_entregado_manual

    proyecto.lugar = form_data.get('lugar') or None
    proyecto.distrito = form_data.get('distrito') or None
    proyecto.departamento = form_data.get('departamento') or None
    proyecto.finca = form_data.get('finca') or None
    proyecto.matricula = form_data.get('matricula') or None
    proyecto.padron = form_data.get('padron') or None
    proyecto.lote = form_data.get('lote') or None
    proyecto.manzana = form_data.get('manzana') or None
    proyecto.fraccion = form_data.get('fraccion') or None
    proyecto.superficie = _parse_decimal(form_data.get('superficie'))

    proyecto.actualizar_finanzas()
    return proyecto


def _process_project_files(proyecto, files):
    factura = files.get('factura')
    if factura and factura.filename:
        _clear_documents(proyecto, 'factura')
        _remove_file(proyecto.factura_archivo_url)
        try:
            relative = _save_project_document(proyecto, factura, categoria='factura')
            proyecto.factura_archivo_url = relative
        except ValueError as exc:
            flash(str(exc), 'warning')

    mapa = files.get('mapa')
    if mapa and mapa.filename:
        _clear_documents(proyecto, 'mapa')
        _remove_file(proyecto.mapa_archivo_url)
        try:
            relative = _save_project_document(proyecto, mapa, categoria='mapa')
            proyecto.mapa_archivo_url = relative
        except ValueError as exc:
            flash(str(exc), 'warning')

    for doc_file in files.getlist('documentos'):
        if not doc_file or not doc_file.filename:
            continue
        try:
            _save_project_document(proyecto, doc_file, categoria='documento')
        except ValueError as exc:
            flash(str(exc), 'warning')


def _classify_documentos(documentos):
    map_docs = []
    factura_docs = []
    image_docs = []
    pdf_docs = []
    other_docs = []

    for doc in documentos:
        name = doc.nombre_original or ''
        ext = os.path.splitext(name)[1].lower()
        categoria = (doc.categoria or '').lower()

        if categoria == 'mapa':
            map_docs.append(doc)
            continue
        if categoria == 'factura':
            factura_docs.append(doc)
            continue
        if ext in IMAGE_EXTENSIONS:
            image_docs.append(doc)
        elif ext == '.pdf':
            pdf_docs.append(doc)
        else:
            other_docs.append(doc)

    return {
        'mapas': map_docs,
        'facturas': factura_docs,
        'imagenes': image_docs,
        'pdfs': pdf_docs,
        'otros': other_docs,
    }


def _select_hero_doc(classification):
    for doc in classification['mapas']:
        ext = os.path.splitext(doc.nombre_original or '')[1].lower()
        if ext in IMAGE_EXTENSIONS:
            return doc
    if classification['imagenes']:
        return classification['imagenes'][0]
    return None


def _prepare_document_groups(documentos):
    classification = _classify_documentos(documentos)
    hero_doc = _select_hero_doc(classification)

    group_specs = [
        ('Mapa de ubicación/referencia', classification['mapas']),
        ('Mapas del proyecto PNG', classification['imagenes']),
        ('Notas y documentaciones PDF', classification['pdfs']),
        ('Facturas / comprobantes', classification['facturas']),
        ('Otros archivos', classification['otros']),
    ]

    groups = [
        {'title': title, 'docs': docs}
        for title, docs in group_specs if docs
    ]

    return groups, hero_doc, classification


@bp.route('/')
@login_required
def index():
    proyecto_id = request.args.get('proyecto_id', type=int)
    page = request.args.get('page', type=int, default=1)
    if page < 1:
        page = 1
    per_page = request.args.get('per_page', type=int, default=PAGE_SIZE_OPTIONS[0])
    if per_page not in PAGE_SIZE_OPTIONS:
        per_page = PAGE_SIZE_OPTIONS[0]

    query = Proyecto.query.order_by(Proyecto.id_proyecto.desc())
    if proyecto_id:
        query = query.filter(Proyecto.id_proyecto == proyecto_id)

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    proyectos = pagination.items
    return render_template(
        'proyectos/list.html',
        proyectos=proyectos,
        estado_labels=ESTADO_LABELS,
        pagination=pagination,
        per_page_options=PAGE_SIZE_OPTIONS,
        proyecto_id=proyecto_id,
    )


@bp.route('/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo():
    clientes = Cliente.query.order_by(Cliente.nombre_razon_social.asc()).all()
    pre_id_cliente = request.args.get('id_cliente', type=int)

    if request.method == 'POST':
        id_cliente = _parse_int(request.form.get('id_cliente'))
        institucion = request.form.get('institucion')
        if not id_cliente or not institucion:
            flash('Seleccioná un cliente e institución válidos.', 'danger')
            return redirect(url_for('proyectos.nuevo'))

        proyecto = Proyecto(
            id_cliente=id_cliente,
            institucion=institucion,
            anho=_parse_int(request.form.get('anho'), date.today().year),
        )
        db.session.add(proyecto)

        _fill_project_from_form(proyecto, request.form)
        proyecto.estado = _resolve_estado(request.form.get('estado'))
        if not proyecto.nombre_proyecto:
            proyecto.nombre_proyecto = f"{proyecto.subtipo or proyecto.institucion} {proyecto.anho}"

        db.session.flush()
        _process_project_files(proyecto, request.files)
        db.session.commit()

        flash('Proyecto creado exitosamente', 'success')
        return redirect(
            url_for(
                'proyectos.board',
                id_cliente=proyecto.id_cliente,
                ano=proyecto.anho,
                inst=proyecto.institucion,
            )
        )

    back_instituciones_url = None
    if pre_id_cliente:
        back_instituciones_url = url_for('clientes.modulos', id_cliente=pre_id_cliente)

    return render_template(
        'proyectos/new.html',
        clientes=clientes,
        anho_actual=date.today().year,
        module_subtipos=MODULE_SUBTIPOS,
        estados=ESTADOS_LIST,
        back_instituciones_url=back_instituciones_url,
    )


def _build_timeline(proyecto):
    emission = proyecto.fecha_emision_licencia
    due = proyecto.fecha_vencimiento_licencia
    today = date.today()
    percent = None
    status = 'neutral'
    due_text = 'Sin vencimiento'
    emission_text = emission.strftime('%d/%m/%Y') if emission else '—'

    if emission and due and due > emission:
        total_days = (due - emission).days
        elapsed_days = (today - emission).days
        percent = max(0, min(100, (elapsed_days / total_days) * 100))

    if due:
        days_to_due = (due - today).days
        if days_to_due < 0:
            status = 'danger'
            due_text = f"Vencido hace {abs(days_to_due)} días"
        elif days_to_due <= 30:
            status = 'danger'
            due_text = f"Vence en {days_to_due} días"
        elif days_to_due <= 90:
            status = 'warning'
            due_text = f"Vence en {days_to_due} días"
        else:
            status = 'success'
            due_text = due.strftime('%d/%m/%Y')
    else:
        days_to_due = None

    return {
        'emission': emission,
        'emission_text': emission_text,
        'due': due,
        'due_text': due_text,
        'percent': percent,
        'status': status,
    }


def _project_card_data(proyecto):
    classification = _classify_documentos(proyecto.documentos)
    hero_doc = _select_hero_doc(classification)
    flags = [
        {'label': 'Mapa', 'icon': 'bi-geo-alt', 'available': bool(classification['mapas'])},
        {'label': 'PDF', 'icon': 'bi-file-earmark-pdf', 'available': bool(classification['pdfs'])},
        {'label': 'Imagen', 'icon': 'bi-card-image', 'available': bool(classification['imagenes'])},
        {'label': 'Factura', 'icon': 'bi-receipt', 'available': bool(classification['facturas'])},
        {'label': 'Otros', 'icon': 'bi-folder', 'available': bool(classification['otros'])},
    ]
    timeline = _build_timeline(proyecto)
    return {
        'project': proyecto,
        'hero_doc': hero_doc,
        'doc_flags': flags,
        'timeline': timeline,
    }


@bp.route('/clientes/<int:id_cliente>/institucion/<string:inst>/proyectos')
@login_required
def board_legacy(id_cliente, inst):
    return redirect(url_for('clientes.modulos', id_cliente=id_cliente))


@bp.route('/clientes/<int:id_cliente>/ano/<int:ano>/institucion/<string:inst>/proyectos')
@login_required
def board(id_cliente, ano, inst):
    tipo_prefill = request.args.get('tipo')
    cliente = Cliente.query.get_or_404(id_cliente)

    query = Proyecto.query.filter_by(id_cliente=id_cliente, anho=ano, institucion=inst)
    if tipo_prefill:
        normalized_tipo = tipo_prefill.strip()
        if not normalized_tipo:
            normalized_tipo = 'Otros'
        if normalized_tipo.lower() == 'otros':
            query = query.filter(
                or_(
                    Proyecto.subtipo.is_(None),
                    Proyecto.subtipo == '',
                    Proyecto.subtipo.ilike('otros')
                )
            )
            tipo_prefill = 'Otros'
        else:
            query = query.filter(Proyecto.subtipo == normalized_tipo)
            tipo_prefill = normalized_tipo
    proyectos = query.order_by(Proyecto.id_proyecto.desc()).all()

    if not proyectos and tipo_prefill:
        proyectos = Proyecto.query.filter_by(id_cliente=id_cliente, anho=ano, institucion=inst).order_by(Proyecto.id_proyecto.desc()).all()

    cols = {estado.value: [] for estado in ESTADOS_LIST}
    for proyecto in proyectos:
        estado_key = proyecto.estado.value if isinstance(proyecto.estado, ProyectoEstado) else (proyecto.estado or 'en_proceso')
        estado_key = estado_key.lower()
        if estado_key == 'entregado':
            estado_key = ProyectoEstado.licencia_emitida.value
        cols.setdefault(estado_key, []).append(_project_card_data(proyecto))

    total_estados = len(cols) or 1
    lg_span = 12 // total_estados
    if lg_span < 3:
        lg_span = 3

    back_periods_url = None
    if tipo_prefill:
        back_periods_url = url_for(
            'clientes.modulo_subtipo_anhos',
            id_cliente=id_cliente,
            inst=inst,
            subtipo=tipo_prefill,
        )

    cliente_url = url_for('clientes.modulos', id_cliente=id_cliente)
    institucion_url = url_for('clientes.modulo_subtipos', id_cliente=id_cliente, inst=inst)
    subtipo_url = None
    if tipo_prefill:
        subtipo_url = url_for(
            'clientes.modulo_subtipo_anhos',
            id_cliente=id_cliente,
            inst=inst,
            subtipo=tipo_prefill,
        )
    ano_url = subtipo_url or institucion_url

    return render_template(
        'proyectos/board.html',
        cliente=cliente,
        institucion=inst,
        ano=ano,
        cols=cols,
        estado_labels=ESTADO_LABELS,
        tipo_prefill=tipo_prefill,
        module_subtipos=MODULE_SUBTIPOS,
        estados=ESTADOS_LIST,
        estado_column_span=lg_span,
        back_periods_url=back_periods_url,
        cliente_url=cliente_url,
        institucion_url=institucion_url,
        subtipo_url=subtipo_url,
        ano_url=ano_url,
    )


@bp.route('/<int:id_proyecto>/detalle')
@login_required
def vista(id_proyecto):
    proyecto = Proyecto.query.get_or_404(id_proyecto)
    documentos = DocumentoProyecto.query.filter_by(id_proyecto=id_proyecto).order_by(DocumentoProyecto.uploaded_at.desc()).all()
    doc_groups, hero_doc, classification = _prepare_document_groups(documentos)
    image_docs = list(classification['imagenes'])
    if hero_doc and hero_doc not in image_docs:
        ext = os.path.splitext(hero_doc.nombre_original or '')[1].lower()
        if ext in IMAGE_EXTENSIONS:
            image_docs.insert(0, hero_doc)

    back_inst = request.args.get('inst')
    back_ano = request.args.get('ano', type=int)
    back_tipo = request.args.get('tipo')
    back_url = None
    if back_inst and back_ano is not None:
        params = {
            'id_cliente': proyecto.id_cliente,
            'ano': back_ano,
            'inst': back_inst,
        }
        if back_tipo:
            params['tipo'] = back_tipo
        back_url = url_for('proyectos.board', **params)

    return render_template(
        'proyectos/detail.html',
        proyecto=proyecto,
        hero_doc=hero_doc,
        doc_groups=doc_groups,
        image_docs=image_docs,
        financial=_financial_summary(proyecto),
        back_url=back_url,
        estado_labels=ESTADO_LABELS,
    )


@bp.route('/crear_quick', methods=['POST'])
@login_required
def crear_quick():
    form = request.form
    id_cliente = _parse_int(form.get('id_cliente'))
    institucion = form.get('institucion')
    if not id_cliente or not institucion:
        flash('Datos insuficientes para crear el proyecto.', 'danger')
        return redirect(request.referrer or url_for('proyectos.index'))

    proyecto = Proyecto(
        id_cliente=id_cliente,
        institucion=institucion,
        anho=_parse_int(form.get('anho'), date.today().year),
    )
    db.session.add(proyecto)

    _fill_project_from_form(proyecto, form)
    if not proyecto.subtipo:
        proyecto.subtipo = form.get('tipo') or 'Otros'
    proyecto.estado = _resolve_estado(form.get('estado'))
    if not proyecto.nombre_proyecto:
        proyecto.nombre_proyecto = f"{proyecto.subtipo} {proyecto.anho}"

    db.session.flush()
    _process_project_files(proyecto, request.files)
    db.session.commit()
    flash('Proyecto creado correctamente', 'success')
    return redirect(
        url_for(
            'proyectos.board',
            id_cliente=proyecto.id_cliente,
            ano=proyecto.anho,
            inst=proyecto.institucion,
        )
    )


@bp.route('/<int:id_proyecto>/documentos', methods=['POST'])
@login_required
def agregar_documentos(id_proyecto):
    proyecto = Proyecto.query.get_or_404(id_proyecto)
    archivos = request.files.getlist('documentos')
    if not archivos or all(not archivo.filename for archivo in archivos):
        flash('Seleccioná al menos un archivo para subir.', 'warning')
        return redirect(url_for('proyectos.vista', id_proyecto=id_proyecto))

    for archivo in archivos:
        if not archivo or not archivo.filename:
            continue
        try:
            ext = os.path.splitext(archivo.filename)[1].lower()
            if ext in IMAGE_EXTENSIONS:
                categoria = 'imagen'
            elif ext == '.pdf':
                categoria = 'pdf'
            else:
                categoria = 'documento'
            _save_project_document(proyecto, archivo, categoria=categoria)
        except ValueError as exc:
            flash(str(exc), 'warning')

    db.session.commit()
    flash('Documentos cargados correctamente.', 'success')
    return redirect(url_for('proyectos.vista', id_proyecto=id_proyecto))


def _financial_summary(proyecto):
    costo = proyecto.costo_total
    entregado = proyecto.monto_entregado_calculado if proyecto.monto_entregado_calculado is not None else None
    saldo = proyecto.saldo_restante if proyecto.saldo_restante is not None else None
    porcentaje = proyecto.porcentaje_entrega

    percent = None
    if costo is not None and entregado is not None and costo > 0:
        percent = float(max(0, min(100, (entregado / costo) * 100)))
    elif porcentaje is not None:
        percent = float(porcentaje)

    return {
        'costo_total': costo,
        'entregado': entregado,
        'saldo': saldo,
        'porcentaje': porcentaje,
        'percent': percent,
    }


@bp.route('/<int:id_proyecto>/estado', methods=['POST'])
@login_required
def update_estado(id_proyecto):
    proyecto = Proyecto.query.get_or_404(id_proyecto)
    data = request.get_json(silent=True) or {}
    nuevo_estado = (data.get('estado') or '').strip().lower()
    if nuevo_estado not in ESTADOS_POR_VALOR:
        return jsonify({"ok": False, "error": "Estado inválido"}), 400
    proyecto.estado = ESTADOS_POR_VALOR[nuevo_estado]
    db.session.commit()
    return jsonify({"ok": True, "estado": proyecto.estado.value})


@bp.route('/<int:id_proyecto>/editar', methods=['GET', 'POST'])
@login_required
def editar(id_proyecto):
    proyecto = Proyecto.query.get_or_404(id_proyecto)
    clientes = Cliente.query.order_by(Cliente.nombre_razon_social.asc()).all()

    raw_back_inst = request.args.get('inst')
    raw_back_ano = request.args.get('ano', type=int)
    back_tipo = request.args.get('tipo')

    back_inst = raw_back_inst or proyecto.institucion
    back_ano = raw_back_ano if raw_back_ano is not None else proyecto.anho

    board_params = {
        'id_cliente': proyecto.id_cliente,
        'inst': back_inst,
        'ano': back_ano,
    }
    if back_tipo:
        board_params['tipo'] = back_tipo
    back_board_url = url_for('proyectos.board', **board_params)

    if request.method == 'POST':
        _fill_project_from_form(proyecto, request.form)
        proyecto.estado = _resolve_estado(request.form.get('estado'))
        if not proyecto.nombre_proyecto:
            proyecto.nombre_proyecto = f"{proyecto.subtipo or proyecto.institucion} {proyecto.anho}"

        db.session.flush()
        _process_project_files(proyecto, request.files)
        db.session.commit()

        flash('Proyecto actualizado', 'success')
        return redirect(back_board_url)

    documentos = DocumentoProyecto.query.filter_by(id_proyecto=id_proyecto).order_by(DocumentoProyecto.uploaded_at.desc()).all()
    subtipos = MODULE_SUBTIPOS.get(proyecto.institucion, MADES_SUBTIPOS)

    return render_template(
        'proyectos/edit.html',
        p=proyecto,
        clientes=clientes,
        documentos=documentos,
        estados=ESTADOS_LIST,
        estado_labels=ESTADO_LABELS,
        subtipos=subtipos,
        module_subtipos=MODULE_SUBTIPOS,
        back_board_url=back_board_url,
    )


@bp.route('/api/cliente/<int:id_cliente>/propiedades')
@login_required
def get_propiedades_cliente(id_cliente):
    propiedades = Propiedad.query.filter_by(id_cliente=id_cliente).order_by(Propiedad.finca.asc()).all()
    return jsonify(
        [
            {
                'id_propiedad': p.id_propiedad,
                'finca': p.finca,
                'padron': p.padron,
                'matricula': p.matricula,
            }
            for p in propiedades
        ]
    )


@bp.route('/doc/<int:id_doc>/eliminar', methods=['POST'])
@login_required
def eliminar_doc(id_doc):
    doc = DocumentoProyecto.query.get_or_404(id_doc)
    proyecto = Proyecto.query.get_or_404(doc.id_proyecto)
    _remove_file(doc.archivo_url)
    db.session.delete(doc)
    db.session.commit()
    flash('Documento eliminado correctamente', 'success')
    return redirect(url_for('proyectos.editar', id_proyecto=proyecto.id_proyecto))


@bp.route('/<int:id_proyecto>/eliminar', methods=['POST'])
@login_required
def eliminar_proyecto(id_proyecto):
    proyecto = Proyecto.query.get_or_404(id_proyecto)
    try:
        for doc in list(proyecto.documentos):
            _remove_file(doc.archivo_url)
            db.session.delete(doc)

        _remove_file(proyecto.factura_archivo_url)
        _remove_file(proyecto.mapa_archivo_url)

        for pago in proyecto.pagos:
            db.session.delete(pago)
        for factura in proyecto.facturas:
            db.session.delete(factura)

        db.session.delete(proyecto)
        db.session.commit()
        flash('Proyecto eliminado exitosamente', 'success')
    except Exception as exc:
        db.session.rollback()
        flash(f'Error al eliminar el proyecto: {exc}', 'danger')

    return redirect(url_for('proyectos.index'))


def _send_document(doc, as_attachment):
    resolved = _absolute_path(doc.archivo_url)
    if not resolved or not os.path.exists(resolved):
        flash(f'Archivo no encontrado: {doc.archivo_url}', 'error')
        abort(404)
    download_name = doc.nombre_original or os.path.basename(resolved)
    return send_file(resolved, as_attachment=as_attachment, download_name=download_name)


@bp.route('/doc/<int:id_doc>/ver', methods=['GET'])
@login_required
def ver_doc(id_doc):
    doc = DocumentoProyecto.query.get_or_404(id_doc)
    return _send_document(doc, as_attachment=False)


@bp.route('/doc/<int:id_doc>/descargar', methods=['GET'])
@login_required
def descargar_doc(id_doc):
    doc = DocumentoProyecto.query.get_or_404(id_doc)
    return _send_document(doc, as_attachment=True)
