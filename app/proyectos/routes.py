from datetime import date
import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app, send_file, abort
from werkzeug.utils import secure_filename
from flask_login import login_required
from ..extensions import db
from ..models import Proyecto, Cliente, Propiedad, DocumentoProyecto

bp = Blueprint('proyectos', __name__)

@bp.route('/')
@login_required
def index():
    proyecto_id = request.args.get('proyecto_id', type=int)

    query = Proyecto.query.order_by(Proyecto.id_proyecto.desc())
    if proyecto_id:
        query = query.filter(Proyecto.id_proyecto == proyecto_id)
    else:
        query = query.limit(50)

    proyectos = query.all()
    return render_template('proyectos/list.html', proyectos=proyectos)

@bp.route('/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo():
    if request.method == 'POST':
        # Procesar creación del proyecto (similar a crear_quick)
        id_cliente = int(request.form['id_cliente'])
        institucion = request.form['institucion']
        anho = int(request.form.get('anho') or date.today().year)
        tipo_tramite = request.form.get('tipo_tramite')
        estado = request.form.get('estado') or 'pendiente'
        id_propiedad = request.form.get('id_propiedad') or None
        fecha_firma = request.form.get('fecha_firma_contrato') or None
        plazo_limite = request.form.get('plazo_limite') or None

        p = Proyecto(
            id_cliente=id_cliente,
            institucion=institucion,
            anho=anho,
            tipo_tramite=tipo_tramite,
            estado=estado,
            id_propiedad=id_propiedad,
            fecha_firma_contrato=fecha_firma,
            plazo_limite=plazo_limite,
        )
        db.session.add(p)
        db.session.commit()

        # Manejo de archivo anexo opcional
        file = request.files.get('anexo')
        if file and file.filename:
            allowed = {'.jpg', '.jpeg', '.png', '.gif', '.pdf', '.webp'}
            ext = os.path.splitext(file.filename)[1].lower()
            if ext in allowed:
                filename = secure_filename(f"proyecto_{p.id_proyecto}_{file.filename}")
                base_upload = current_app.config.get('UPLOAD_FOLDER', 'uploads')
                # Asegurar ruta absoluta
                if not os.path.isabs(base_upload):
                    base_upload = os.path.join(current_app.root_path, base_upload)
                target_dir = os.path.join(base_upload, 'proyectos')
                os.makedirs(target_dir, exist_ok=True)
                save_path = os.path.join(target_dir, filename)
                file.save(save_path)

                doc = DocumentoProyecto(
                    id_proyecto=p.id_proyecto,
                    tipo='anexo',
                    archivo_url=save_path
                )
                db.session.add(doc)
                db.session.commit()

        flash('Proyecto creado exitosamente', 'success')
        return redirect(url_for('proyectos.index'))

    # GET - Mostrar formulario
    clientes = Cliente.query.order_by(Cliente.nombre_razon_social.asc()).all()
    return render_template('proyectos/new.html', clientes=clientes, anho_actual=date.today().year)

@bp.route('/clientes/<int:id_cliente>/institucion/<string:inst>/proyectos')
@login_required
def board_legacy(id_cliente, inst):
    # Redirige a la selección de período (compatibilidad con enlaces antiguos)
    return redirect(url_for('clientes.seleccionar_periodo', id_cliente=id_cliente))


# Nuevo board con año en la URL
@bp.route('/clientes/<int:id_cliente>/ano/<int:ano>/institucion/<string:inst>/proyectos')
@login_required
def board(id_cliente, ano, inst):
    tipo_prefill = request.args.get('tipo')
    cliente = Cliente.query.get_or_404(id_cliente)
    props = Propiedad.query.filter_by(id_cliente=id_cliente).order_by(Propiedad.finca.asc()).all()

    query = Proyecto.query.filter_by(id_cliente=id_cliente, anho=ano, institucion=inst)
    if tipo_prefill:
        query = query.filter(Proyecto.tipo_tramite.ilike(f'%{tipo_prefill}%'))
    proyectos = query.order_by(Proyecto.id_proyecto.desc()).all()

    if not proyectos and tipo_prefill:
        query = Proyecto.query.filter_by(id_cliente=id_cliente, anho=ano, institucion=inst)
        proyectos = query.order_by(Proyecto.id_proyecto.desc()).all()

    estados = ['en proceso', 'entregado', 'finalizado', 'pendiente']
    cols = {e: [] for e in estados}
    for p in proyectos:
        e = (p.estado or 'pendiente').lower()
        cols[e if e in cols else 'pendiente'].append(p)

    return render_template('proyectos/board.html', 
                         cliente=cliente, 
                         institucion=inst, 
                         ano=ano,
                         cols=cols, 
                         propiedades=props, 
                         tipo_prefill=tipo_prefill)

@bp.route('/crear_quick', methods=['POST'])
@login_required
def crear_quick():
    id_cliente = int(request.form['id_cliente'])
    institucion = request.form['institucion']
    anho = int(request.form.get('anho') or date.today().year)
    tipo_tramite = request.form.get('tipo_tramite')
    estado = request.form.get('estado') or 'pendiente'
    id_propiedad = request.form.get('id_propiedad') or None
    fecha_firma = request.form.get('fecha_firma_contrato') or None
    plazo_limite = request.form.get('plazo_limite') or None

    p = Proyecto(
        id_cliente=id_cliente,
        institucion=institucion,
        anho=anho,
        tipo_tramite=tipo_tramite,
        estado=estado,
        id_propiedad=id_propiedad,
        fecha_firma_contrato=fecha_firma,
        plazo_limite=plazo_limite,
    )
    db.session.add(p)
    db.session.commit()

    # Manejo de archivo anexo opcional
    file = request.files.get('anexo')
    if file and file.filename:
        # Validación básica de extensión
        allowed = {'.jpg', '.jpeg', '.png', '.gif', '.pdf', '.webp'}
        ext = os.path.splitext(file.filename)[1].lower()
        if ext in allowed:
            filename = secure_filename(f"proyecto_{p.id_proyecto}_{file.filename}")
            base_upload = current_app.config.get('UPLOAD_FOLDER', 'uploads')
            target_dir = os.path.join(base_upload, 'proyectos')
            os.makedirs(target_dir, exist_ok=True)
            save_path = os.path.join(target_dir, filename)
            file.save(save_path)

            doc = DocumentoProyecto(
                id_proyecto=p.id_proyecto,
                tipo='anexo',
                archivo_url=save_path
            )
            db.session.add(doc)
            db.session.commit()
    flash('Proyecto creado', 'success')
    return redirect(url_for('proyectos.board', id_cliente=id_cliente, ano=anho, inst=institucion))

@bp.route('/<int:id_proyecto>/estado', methods=['POST'])
@login_required
def update_estado(id_proyecto):
    p = Proyecto.query.get_or_404(id_proyecto)
    data = request.get_json(silent=True) or {}
    nuevo_estado = (data.get('estado') or '').strip().lower()
    if nuevo_estado not in ['pendiente', 'en proceso', 'entregado', 'finalizado']:
        return jsonify({"ok": False, "error": "Estado inválido"}), 400
    p.estado = nuevo_estado
    db.session.commit()
    return jsonify({"ok": True})

@bp.route('/<int:id_proyecto>/editar', methods=['GET', 'POST'])
@login_required
def editar(id_proyecto):
    p = Proyecto.query.get_or_404(id_proyecto)
    props = Propiedad.query.filter_by(id_cliente=p.id_cliente).order_by(Propiedad.finca.asc()).all()
    clientes = Cliente.query.order_by(Cliente.nombre_razon_social.asc()).all()
    if request.method == 'POST':
        p.id_cliente = int(request.form.get('id_cliente') or p.id_cliente)
        p.institucion = request.form.get('institucion') or p.institucion
        p.anho = int(request.form.get('anho') or p.anho or date.today().year)
        p.tipo_tramite = request.form.get('tipo_tramite')
        p.estado = request.form.get('estado') or p.estado
        p.id_propiedad = request.form.get('id_propiedad') or None
        p.fecha_firma_contrato = request.form.get('fecha_firma_contrato') or None
        p.plazo_limite = request.form.get('plazo_limite') or None
        db.session.commit()

        # Manejo de archivo anexo opcional en edición
        file = request.files.get('anexo')
        if file and file.filename:
            allowed = {'.jpg', '.jpeg', '.png', '.gif', '.pdf', '.webp'}
            ext = os.path.splitext(file.filename)[1].lower()
            if ext in allowed:
                filename = secure_filename(f"proyecto_{p.id_proyecto}_{file.filename}")
                base_upload = current_app.config.get('UPLOAD_FOLDER', 'uploads')
                # Asegurar ruta absoluta
                if not os.path.isabs(base_upload):
                    base_upload = os.path.join(current_app.root_path, base_upload)
                target_dir = os.path.join(base_upload, 'proyectos')
                os.makedirs(target_dir, exist_ok=True)
                save_path = os.path.join(target_dir, filename)
                file.save(save_path)

                doc = DocumentoProyecto(
                    id_proyecto=p.id_proyecto,
                    tipo='anexo',
                    archivo_url=save_path
                )
                db.session.add(doc)
                db.session.commit()
        flash('Proyecto actualizado', 'success')
        return redirect(url_for('proyectos.editar', id_proyecto=p.id_proyecto))
    documentos = DocumentoProyecto.query.filter_by(id_proyecto=id_proyecto).all()
    return render_template('proyectos/edit.html', p=p, propiedades=props, clientes=clientes, documentos=documentos)

# API: propiedades por cliente
@bp.route('/api/cliente/<int:id_cliente>/propiedades')
@login_required
def get_propiedades_cliente(id_cliente):
    propiedades = Propiedad.query.filter_by(id_cliente=id_cliente).order_by(Propiedad.finca.asc()).all()
    return jsonify([
        {
            'id_propiedad': p.id_propiedad,
            'finca': p.finca,
            'padron': p.padron,
            'matricula': p.matricula,
        } for p in propiedades
    ])

@bp.route('/doc/<int:id_doc>/eliminar', methods=['POST'])
@login_required
def eliminar_doc(id_doc):
    doc = DocumentoProyecto.query.get_or_404(id_doc)
    proyecto = Proyecto.query.get_or_404(doc.id_proyecto)
    # Intentar borrar el archivo físico
    try:
        if doc.archivo_url and os.path.exists(doc.archivo_url):
            os.remove(doc.archivo_url)
    except Exception:
        pass
    db.session.delete(doc)
    db.session.commit()
    flash('Documento eliminado correctamente', 'success')
    return redirect(url_for('proyectos.editar', id_proyecto=proyecto.id_proyecto))

# Eliminar proyecto con borrado en cascada y archivos
@bp.route('/<int:id_proyecto>/eliminar', methods=['POST'])
@login_required
def eliminar_proyecto(id_proyecto):
    proyecto = Proyecto.query.get_or_404(id_proyecto)
    try:
        # Eliminar documentos asociados (y archivos físicos si existen)
        documentos = DocumentoProyecto.query.filter_by(id_proyecto=id_proyecto).all()
        for doc in documentos:
            try:
                if doc.archivo_url and os.path.exists(doc.archivo_url):
                    os.remove(doc.archivo_url)
            except Exception:
                pass
            db.session.delete(doc)

        # Eliminar pagos asociados
        for pago in proyecto.pagos:
            db.session.delete(pago)

        # Eliminar facturas asociadas
        for factura in proyecto.facturas:
            db.session.delete(factura)

        # Eliminar el proyecto
        db.session.delete(proyecto)
        db.session.commit()
        flash('Proyecto eliminado exitosamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar el proyecto: {str(e)}', 'error')

    return redirect(url_for('proyectos.index'))

@bp.route('/doc/<int:id_doc>/ver', methods=['GET'])
@login_required
def ver_doc(id_doc):
    doc = DocumentoProyecto.query.get_or_404(id_doc)
    if not doc.archivo_url:
        flash('No se encontró la URL del archivo', 'error')
        abort(404)
    
    # Intentar corregir la ruta si es relativa o incorrecta
    archivo_path = doc.archivo_url
    if not os.path.exists(archivo_path):
        # Intentar con ruta absoluta desde root_path
        base_upload = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        if not os.path.isabs(base_upload):
            base_upload = os.path.join(current_app.root_path, base_upload)
        
        # Extraer solo el nombre del archivo
        filename = os.path.basename(archivo_path)
        archivo_path = os.path.join(base_upload, 'proyectos', filename)
        
        if not os.path.exists(archivo_path):
            flash(f'Archivo no encontrado: {doc.archivo_url}', 'error')
            abort(404)
    
    # as_attachment=False para mostrar en navegador
    return send_file(archivo_path, as_attachment=False)

@bp.route('/doc/<int:id_doc>/descargar', methods=['GET'])
@login_required
def descargar_doc(id_doc):
    doc = DocumentoProyecto.query.get_or_404(id_doc)
    if not doc.archivo_url:
        flash('No se encontró la URL del archivo', 'error')
        abort(404)
    
    # Intentar corregir la ruta si es relativa o incorrecta
    archivo_path = doc.archivo_url
    if not os.path.exists(archivo_path):
        # Intentar con ruta absoluta desde root_path
        base_upload = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        if not os.path.isabs(base_upload):
            base_upload = os.path.join(current_app.root_path, base_upload)
        
        # Extraer solo el nombre del archivo
        filename = os.path.basename(archivo_path)
        archivo_path = os.path.join(base_upload, 'proyectos', filename)
        
        if not os.path.exists(archivo_path):
            flash(f'Archivo no encontrado: {doc.archivo_url}', 'error')
            abort(404)
    
    # as_attachment=True para forzar descarga
    return send_file(archivo_path, as_attachment=True)

