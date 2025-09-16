from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required
from datetime import datetime, date
from ..extensions import db
from ..models import Cliente, Propiedad, Proyecto, Pago, Factura, DocumentoProyecto

bp = Blueprint('proyectos', __name__)

@bp.route('/')
@login_required
def index():
    q = request.args.get('q', '')
    cliente_id = request.args.get('cliente_id', '')
    institucion = request.args.get('institucion', '')
    estado = request.args.get('estado', '')
    anho = request.args.get('anho', '')
    
    query = db.session.query(Proyecto, Cliente, Propiedad)\
        .join(Cliente, Proyecto.id_cliente == Cliente.id_cliente)\
        .join(Propiedad, Proyecto.id_propiedad == Propiedad.id_propiedad)
    
    if q:
        query = query.filter(
            db.or_(
                Cliente.nombre_razon_social.ilike(f'%{q}%'),
                Proyecto.tipo_tramite.ilike(f'%{q}%'),
                Proyecto.institucion.ilike(f'%{q}%')
            )
        )
    
    if cliente_id:
        query = query.filter(Proyecto.id_cliente == cliente_id)
    
    if institucion:
        query = query.filter(Proyecto.institucion == institucion)
    
    if estado:
        query = query.filter(Proyecto.estado == estado)
    
    if anho:
        query = query.filter(Proyecto.anho == anho)
    
    proyectos = query.order_by(Proyecto.anho.desc(), Proyecto.fecha_firma_contrato.desc()).all()
    
    # Para los filtros
    clientes = Cliente.query.order_by(Cliente.nombre_razon_social.asc()).all()
    instituciones = ['MADES', 'INFONA', 'SENAVE']
    estados = ['pendiente', 'en proceso', 'entregado', 'finalizado']
    anhos = list(range(2020, datetime.now().year + 2))
    
    return render_template('proyectos/index.html', 
                         proyectos=proyectos,
                         clientes=clientes,
                         instituciones=instituciones,
                         estados=estados,
                         anhos=anhos,
                         filtros={
                             'q': q,
                             'cliente_id': cliente_id,
                             'institucion': institucion,
                             'estado': estado,
                             'anho': anho
                         })

@bp.route('/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_proyecto():
    if request.method == 'POST':
        try:
            # Crear el proyecto
            p = Proyecto(
                id_cliente=request.form.get('id_cliente'),
                id_propiedad=request.form.get('id_propiedad'),
                anho=int(request.form.get('anho')),
                institucion=request.form.get('institucion'),
                tipo_tramite=request.form.get('tipo_tramite'),
                fecha_firma_contrato=datetime.strptime(request.form.get('fecha_firma_contrato'), '%Y-%m-%d').date() if request.form.get('fecha_firma_contrato') else None,
                estado=request.form.get('estado', 'pendiente'),
                plazo_limite=datetime.strptime(request.form.get('plazo_limite'), '%Y-%m-%d').date() if request.form.get('plazo_limite') else None
            )
            db.session.add(p)
            db.session.flush()  # Para obtener el ID
            
            # Crear información de pago si se proporciona
            if request.form.get('monto_total'):
                monto_total = float(request.form.get('monto_total'))
                porcentaje_inicial = float(request.form.get('porcentaje_pago_inicial', 0))
                pago_inicial = monto_total * (porcentaje_inicial / 100)
                saldo_restante = monto_total - pago_inicial
                
                pago = Pago(
                    id_proyecto=p.id_proyecto,
                    monto_total=monto_total,
                    porcentaje_pago_inicial=porcentaje_inicial,
                    saldo_restante=saldo_restante
                )
                db.session.add(pago)
            
            db.session.commit()
            flash('Proyecto creado exitosamente', 'success')
            return redirect(url_for('proyectos.detalle', id_proyecto=p.id_proyecto))
            
        except Exception as e:
            flash('Error al crear el proyecto', 'error')
            db.session.rollback()
    
    # Para GET request
    cliente_id = request.args.get('cliente_id')
    propiedad_id = request.args.get('id_propiedad')
    
    clientes = Cliente.query.order_by(Cliente.nombre_razon_social.asc()).all()
    propiedades = []
    
    if cliente_id:
        propiedades = Propiedad.query.filter_by(id_cliente=cliente_id).order_by(Propiedad.finca.asc()).all()
    elif propiedad_id:
        propiedad = Propiedad.query.get(propiedad_id)
        if propiedad:
            propiedades = [propiedad]
            cliente_id = propiedad.id_cliente
    
    instituciones = [
        {'key': 'MADES', 'name': 'Ministerio del Ambiente y Desarrollo Sostenible'},
        {'key': 'INFONA', 'name': 'Instituto Forestal Nacional'},
        {'key': 'SENAVE', 'name': 'Servicio Nacional de Calidad y Sanidad Vegetal y de Semillas'}
    ]
    
    tipos_tramite = {
        'MADES': ['EIA', 'EDE', 'Auditoría Ambiental', 'PGAS', 'Consulta Previa'],
        'INFONA': ['Plan de Manejo Forestal', 'Autorización de Desmonte', 'Reforestación'],
        'SENAVE': ['Registro de Silo', 'Certificación Fitosanitaria', 'Registro de Establecimiento']
    }
    
    return render_template('proyectos/form.html', 
                         clientes=clientes,
                         propiedades=propiedades,
                         instituciones=instituciones,
                         tipos_tramite=tipos_tramite,
                         selected_cliente=cliente_id,
                         selected_propiedad=propiedad_id)

@bp.route('/<int:id_proyecto>')
@login_required
def detalle(id_proyecto):
    proyecto = Proyecto.query.get_or_404(id_proyecto)
    cliente = Cliente.query.get(proyecto.id_cliente)
    propiedad = Propiedad.query.get(proyecto.id_propiedad)
    
    # Obtener información de pagos y facturas
    pagos = Pago.query.filter_by(id_proyecto=id_proyecto).all()
    facturas = Factura.query.filter_by(id_proyecto=id_proyecto).order_by(Factura.fecha_emision.desc()).all()
    documentos = DocumentoProyecto.query.filter_by(id_proyecto=id_proyecto).all()
    
    # Calcular resumen de pagos
    total_facturado = sum(f.monto for f in facturas)
    pago_info = pagos[0] if pagos else None
    
    return render_template('proyectos/detalle.html',
                         proyecto=proyecto,
                         cliente=cliente,
                         propiedad=propiedad,
                         pagos=pagos,
                         facturas=facturas,
                         documentos=documentos,
                         total_facturado=total_facturado,
                         pago_info=pago_info)

@bp.route('/<int:id_proyecto>/editar', methods=['GET', 'POST'])
@login_required
def editar_proyecto(id_proyecto):
    proyecto = Proyecto.query.get_or_404(id_proyecto)
    
    if request.method == 'POST':
        try:
            proyecto.id_cliente = request.form.get('id_cliente')
            proyecto.id_propiedad = request.form.get('id_propiedad')
            proyecto.anho = int(request.form.get('anho'))
            proyecto.institucion = request.form.get('institucion')
            proyecto.tipo_tramite = request.form.get('tipo_tramite')
            proyecto.fecha_firma_contrato = datetime.strptime(request.form.get('fecha_firma_contrato'), '%Y-%m-%d').date() if request.form.get('fecha_firma_contrato') else None
            proyecto.estado = request.form.get('estado')
            proyecto.plazo_limite = datetime.strptime(request.form.get('plazo_limite'), '%Y-%m-%d').date() if request.form.get('plazo_limite') else None
            
            # Actualizar información de pago
            pago = Pago.query.filter_by(id_proyecto=id_proyecto).first()
            if request.form.get('monto_total'):
                monto_total = float(request.form.get('monto_total'))
                porcentaje_inicial = float(request.form.get('porcentaje_pago_inicial', 0))
                pago_inicial = monto_total * (porcentaje_inicial / 100)
                saldo_restante = monto_total - pago_inicial
                
                if pago:
                    pago.monto_total = monto_total
                    pago.porcentaje_pago_inicial = porcentaje_inicial
                    pago.saldo_restante = saldo_restante
                else:
                    pago = Pago(
                        id_proyecto=id_proyecto,
                        monto_total=monto_total,
                        porcentaje_pago_inicial=porcentaje_inicial,
                        saldo_restante=saldo_restante
                    )
                    db.session.add(pago)
            
            db.session.commit()
            flash('Proyecto actualizado exitosamente', 'success')
            return redirect(url_for('proyectos.detalle', id_proyecto=id_proyecto))
            
        except Exception as e:
            flash('Error al actualizar el proyecto', 'error')
            db.session.rollback()
    
    # Para GET request
    clientes = Cliente.query.order_by(Cliente.nombre_razon_social.asc()).all()
    propiedades = Propiedad.query.filter_by(id_cliente=proyecto.id_cliente).order_by(Propiedad.finca.asc()).all()
    
    instituciones = [
        {'key': 'MADES', 'name': 'Ministerio del Ambiente y Desarrollo Sostenible'},
        {'key': 'INFONA', 'name': 'Instituto Forestal Nacional'},
        {'key': 'SENAVE', 'name': 'Servicio Nacional de Calidad y Sanidad Vegetal y de Semillas'}
    ]
    
    tipos_tramite = {
        'MADES': ['EIA', 'EDE', 'Auditoría Ambiental', 'PGAS', 'Consulta Previa'],
        'INFONA': ['Plan de Manejo Forestal', 'Autorización de Desmonte', 'Reforestación'],
        'SENAVE': ['Registro de Silo', 'Certificación Fitosanitaria', 'Registro de Establecimiento']
    }
    
    # Obtener información de pago existente
    pago_info = Pago.query.filter_by(id_proyecto=id_proyecto).first()
    
    return render_template('proyectos/form.html',
                         proyecto=proyecto,
                         clientes=clientes,
                         propiedades=propiedades,
                         instituciones=instituciones,
                         tipos_tramite=tipos_tramite,
                         pago_info=pago_info,
                         selected_cliente=proyecto.id_cliente,
                         selected_propiedad=proyecto.id_propiedad)

@bp.route('/<int:id_proyecto>/eliminar', methods=['POST'])
@login_required
def eliminar_proyecto(id_proyecto):
    proyecto = Proyecto.query.get_or_404(id_proyecto)
    
    try:
        # Eliminar registros relacionados
        DocumentoProyecto.query.filter_by(id_proyecto=id_proyecto).delete()
        Factura.query.filter_by(id_proyecto=id_proyecto).delete()
        Pago.query.filter_by(id_proyecto=id_proyecto).delete()
        
        # Eliminar el proyecto
        db.session.delete(proyecto)
        db.session.commit()
        flash('Proyecto eliminado exitosamente', 'success')
        
    except Exception as e:
        flash('Error al eliminar el proyecto', 'error')
        db.session.rollback()
    
    return redirect(url_for('proyectos.index'))

# API endpoints para cargar datos dinámicamente
@bp.route('/api/propiedades/<int:cliente_id>')
@login_required
def api_propiedades(cliente_id):
    propiedades = Propiedad.query.filter_by(id_cliente=cliente_id).order_by(Propiedad.finca.asc()).all()
    return jsonify([{
        'id_propiedad': p.id_propiedad,
        'display_name': p.display_name,
        'ubicacion': p.ubicacion_completa
    } for p in propiedades])

@bp.route('/api/tipos_tramite/<institucion>')
@login_required
def api_tipos_tramite(institucion):
    tipos = {
        'MADES': ['EIA', 'EDE', 'Auditoría Ambiental', 'PGAS', 'Consulta Previa'],
        'INFONA': ['Plan de Manejo Forestal', 'Autorización de Desmonte', 'Reforestación'],
        'SENAVE': ['Registro de Silo', 'Certificación Fitosanitaria', 'Registro de Establecimiento']
    }
    return jsonify(tipos.get(institucion, []))