from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import login_required
from datetime import date, datetime, timedelta
import io
import csv
import os
from ..extensions import db
from ..models import Cliente, Propiedad, Vencimiento, Notificacion

bp = Blueprint('vencimientos', __name__)

@bp.route('/')
@login_required
def list_vencimientos():
    """Lista todos los vencimientos con filtros"""
    # Filtros
    cliente_id = request.args.get('cliente_id', '')
    tipo_documento = request.args.get('tipo_documento', '')
    estado = request.args.get('estado', '')
    mes = request.args.get('mes', '')
    año = request.args.get('año', '')
    
    # Query corregido con joins explícitos
    query = db.session.query(Vencimiento, Cliente, Propiedad).select_from(Vencimiento).join(
        Cliente, Vencimiento.id_cliente == Cliente.id_cliente
    ).outerjoin(
        Propiedad, Vencimiento.id_propiedad == Propiedad.id_propiedad
    )
    
    if cliente_id:
        query = query.filter(Vencimiento.id_cliente == cliente_id)
    
    if tipo_documento:
        query = query.filter(Vencimiento.tipo_documento == tipo_documento)
    
    if estado:
        if estado == 'vencido':
            query = query.filter(Vencimiento.fecha_vencimiento < date.today())
        elif estado == 'proximo_vencer':
            query = query.filter(
                Vencimiento.fecha_vencimiento >= date.today(),
                Vencimiento.fecha_vencimiento <= date.today() + timedelta(days=30)
            )
        elif estado == 'vigente':
            query = query.filter(Vencimiento.fecha_vencimiento > date.today() + timedelta(days=30))
    
    if mes and año:
        try:
            mes_int = int(mes)
            año_int = int(año)
            query = query.filter(
                db.extract('month', Vencimiento.fecha_vencimiento) == mes_int,
                db.extract('year', Vencimiento.fecha_vencimiento) == año_int
            )
        except ValueError:
            pass
    elif año:
        try:
            año_int = int(año)
            query = query.filter(db.extract('year', Vencimiento.fecha_vencimiento) == año_int)
        except ValueError:
            pass
    
    vencimientos = query.order_by(Vencimiento.fecha_vencimiento.asc()).all()
    
    # Obtener datos para los filtros
    clientes = Cliente.query.order_by(Cliente.nombre_razon_social.asc()).all()
    tipos_documento = db.session.query(Vencimiento.tipo_documento).distinct().all()
    tipos_documento = [t[0] for t in tipos_documento if t[0]]
    
    # Calcular estadísticas
    total_vencimientos = len(vencimientos)
    vencidos = sum(1 for v, c, p in vencimientos if v.esta_vencido())
    proximos_vencer = sum(1 for v, c, p in vencimientos if not v.esta_vencido() and v.dias_hasta_vencimiento() is not None and v.dias_hasta_vencimiento() <= 30)
    
    return render_template('vencimientos/list.html',
                         vencimientos=vencimientos,
                         clientes=clientes,
                         tipos_documento=tipos_documento,
                         cliente_id=cliente_id,
                         tipo_documento=tipo_documento,
                         estado=estado,
                         mes=mes,
                         año=año,
                         estadisticas={
                             'total': total_vencimientos,
                             'vencidos': vencidos,
                             'proximos_vencer': proximos_vencer,
                             'vigentes': total_vencimientos - vencidos - proximos_vencer
                         })

@bp.route('/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_vencimiento():
    """Crear un nuevo vencimiento"""
    if request.method == 'POST':
        try:
            vencimiento = Vencimiento(
                id_cliente=int(request.form.get('id_cliente')),
                tipo_documento=request.form.get('tipo_documento'),
                fecha_emision=datetime.strptime(request.form.get('fecha_emision'), '%Y-%m-%d').date(),
                fecha_vencimiento=datetime.strptime(request.form.get('fecha_vencimiento'), '%Y-%m-%d').date(),
                id_propiedad=int(request.form.get('id_propiedad')) if request.form.get('id_propiedad') else None,
                estado='vigente'
            )
            
            db.session.add(vencimiento)
            db.session.commit()
            flash('Vencimiento registrado exitosamente', 'success')
            return redirect(url_for('vencimientos.list_vencimientos'))
        except Exception as e:
            flash(f'Error al crear el vencimiento: {str(e)}', 'error')
            db.session.rollback()
    
    clientes = Cliente.query.order_by(Cliente.nombre_razon_social.asc()).all()
    tipos_documento = ['Licencia Ambiental', 'Auditoría Ambiental', 'Plan Genérico', 'Licencia Forestal', 'Permiso de Tala', 'Certificado Fitosanitario']
    
    return render_template('vencimientos/form.html', 
                         clientes=clientes, 
                         tipos_documento=tipos_documento)

@bp.route('/<int:id_vencimiento>/editar', methods=['GET', 'POST'])
@login_required
def editar_vencimiento(id_vencimiento):
    """Editar un vencimiento existente"""
    vencimiento = Vencimiento.query.get_or_404(id_vencimiento)
    
    if request.method == 'POST':
        try:
            vencimiento.id_cliente = int(request.form.get('id_cliente'))
            vencimiento.tipo_documento = request.form.get('tipo_documento')
            vencimiento.fecha_emision = datetime.strptime(request.form.get('fecha_emision'), '%Y-%m-%d').date()
            vencimiento.fecha_vencimiento = datetime.strptime(request.form.get('fecha_vencimiento'), '%Y-%m-%d').date()
            vencimiento.id_propiedad = int(request.form.get('id_propiedad')) if request.form.get('id_propiedad') else None
            vencimiento.estado = request.form.get('estado')
            
            db.session.commit()
            flash('Vencimiento actualizado exitosamente', 'success')
            return redirect(url_for('vencimientos.list_vencimientos'))
        except Exception as e:
            flash(f'Error al actualizar el vencimiento: {str(e)}', 'error')
            db.session.rollback()
    
    clientes = Cliente.query.order_by(Cliente.nombre_razon_social.asc()).all()
    propiedades = Propiedad.query.filter_by(id_cliente=vencimiento.id_cliente).all() if vencimiento.id_cliente else []
    tipos_documento = ['Licencia Ambiental', 'Auditoría Ambiental', 'Plan Genérico', 'Licencia Forestal', 'Permiso de Tala', 'Certificado Fitosanitario']
    
    return render_template('vencimientos/form.html', 
                         vencimiento=vencimiento,
                         clientes=clientes, 
                         propiedades=propiedades,
                         tipos_documento=tipos_documento)

@bp.route('/<int:id_vencimiento>/detalle')
@login_required
def detalle_vencimiento(id_vencimiento):
    """Ver detalle de un vencimiento"""
    vencimiento = Vencimiento.query.get_or_404(id_vencimiento)
    cliente = Cliente.query.get(vencimiento.id_cliente)
    propiedad = Propiedad.query.get(vencimiento.id_propiedad) if vencimiento.id_propiedad else None
    
    return render_template('vencimientos/detalle.html',
                         vencimiento=vencimiento,
                         cliente=cliente,
                         propiedad=propiedad)

@bp.route('/<int:id_vencimiento>/eliminar', methods=['POST'])
@login_required
def eliminar_vencimiento(id_vencimiento):
    """Eliminar un vencimiento"""
    vencimiento = Vencimiento.query.get_or_404(id_vencimiento)
    
    try:
        db.session.delete(vencimiento)
        db.session.commit()
        flash('Vencimiento eliminado exitosamente', 'success')
    except Exception as e:
        flash('Error al eliminar el vencimiento', 'error')
        db.session.rollback()
    
    return redirect(url_for('vencimientos.list_vencimientos'))

@bp.route('/dashboard')
@login_required
def dashboard():
    """Dashboard de vencimientos con resumen y alertas"""
    hoy = date.today()
    
    # Vencimientos próximos (30 días) - Query corregido
    proximos = db.session.query(Vencimiento, Cliente, Propiedad).select_from(Vencimiento).join(
        Cliente, Vencimiento.id_cliente == Cliente.id_cliente
    ).outerjoin(
        Propiedad, Vencimiento.id_propiedad == Propiedad.id_propiedad
    ).filter(
        Vencimiento.fecha_vencimiento >= hoy,
        Vencimiento.fecha_vencimiento <= hoy + timedelta(days=30)
    ).order_by(Vencimiento.fecha_vencimiento.asc()).all()
    
    # Vencimientos de hoy - Query corregido
    vencen_hoy = db.session.query(Vencimiento, Cliente, Propiedad).select_from(Vencimiento).join(
        Cliente, Vencimiento.id_cliente == Cliente.id_cliente
    ).outerjoin(
        Propiedad, Vencimiento.id_propiedad == Propiedad.id_propiedad
    ).filter(
        Vencimiento.fecha_vencimiento == hoy
    ).all()
    
    # Vencidos - Query corregido
    vencidos = db.session.query(Vencimiento, Cliente, Propiedad).select_from(Vencimiento).join(
        Cliente, Vencimiento.id_cliente == Cliente.id_cliente
    ).outerjoin(
        Propiedad, Vencimiento.id_propiedad == Propiedad.id_propiedad
    ).filter(
        Vencimiento.fecha_vencimiento < hoy
    ).order_by(Vencimiento.fecha_vencimiento.desc()).limit(10).all()
    
    # Estadísticas por tipo de documento
    stats_tipo = db.session.query(
        Vencimiento.tipo_documento,
        db.func.count(Vencimiento.id_vencimiento).label('cantidad')
    ).group_by(Vencimiento.tipo_documento).all()
    
    # Estadísticas por mes (próximos 6 meses)
    stats_mes = []
    for i in range(6):
        mes_fecha = hoy + timedelta(days=30*i)
        cantidad = Vencimiento.query.filter(
            db.extract('month', Vencimiento.fecha_vencimiento) == mes_fecha.month,
            db.extract('year', Vencimiento.fecha_vencimiento) == mes_fecha.year
        ).count()
        stats_mes.append({
            'mes': mes_fecha.strftime('%B %Y'),
            'cantidad': cantidad
        })
    
    return render_template('vencimientos/dashboard.html',
                         proximos=proximos,
                         vencen_hoy=vencen_hoy,
                         vencidos=vencidos,
                         stats_tipo=stats_tipo,
                         stats_mes=stats_mes)

@bp.route('/notificar/<int:id_vencimiento>')
@login_required
def marcar_notificado(id_vencimiento):
    """Marcar un vencimiento como notificado"""
    vencimiento = Vencimiento.query.get_or_404(id_vencimiento)
    tipo_notificacion = vencimiento.necesita_notificacion()
    
    if tipo_notificacion:
        notificacion = Notificacion(
            id_vencimiento=id_vencimiento,
            tipo=tipo_notificacion,
            fecha_envio=date.today()
        )
        db.session.add(notificacion)
        db.session.commit()
        flash(f'Notificación {tipo_notificacion.replace("_", " ")} registrada', 'success')
    else:
        flash('No se requiere notificación para este vencimiento', 'info')
    
    return redirect(url_for('vencimientos.list_vencimientos'))

@bp.route('/exportar')
@login_required
def exportar_excel():
    """Exportar vencimientos a Excel/CSV"""
    # Aplicar los mismos filtros que en list_vencimientos
    cliente_id = request.args.get('cliente_id', '')
    tipo_documento = request.args.get('tipo_documento', '')
    estado = request.args.get('estado', '')
    mes = request.args.get('mes', '')
    año = request.args.get('año', '')
    
    # Query corregido
    query = db.session.query(Vencimiento, Cliente, Propiedad).select_from(Vencimiento).join(
        Cliente, Vencimiento.id_cliente == Cliente.id_cliente
    ).outerjoin(
        Propiedad, Vencimiento.id_propiedad == Propiedad.id_propiedad
    )
    
    if cliente_id:
        query = query.filter(Vencimiento.id_cliente == cliente_id)
    
    if tipo_documento:
        query = query.filter(Vencimiento.tipo_documento == tipo_documento)
    
    if estado:
        if estado == 'vencido':
            query = query.filter(Vencimiento.fecha_vencimiento < date.today())
        elif estado == 'proximo_vencer':
            query = query.filter(
                Vencimiento.fecha_vencimiento >= date.today(),
                Vencimiento.fecha_vencimiento <= date.today() + timedelta(days=30)
            )
        elif estado == 'vigente':
            query = query.filter(Vencimiento.fecha_vencimiento > date.today() + timedelta(days=30))
    
    if mes and año:
        try:
            mes_int = int(mes)
            año_int = int(año)
            query = query.filter(
                db.extract('month', Vencimiento.fecha_vencimiento) == mes_int,
                db.extract('year', Vencimiento.fecha_vencimiento) == año_int
            )
        except ValueError:
            pass
    elif año:
        try:
            año_int = int(año)
            query = query.filter(db.extract('year', Vencimiento.fecha_vencimiento) == año_int)
        except ValueError:
            pass
    
    vencimientos = query.order_by(Vencimiento.fecha_vencimiento.asc()).all()
    
    # Crear CSV en memoria
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Headers
    writer.writerow([
        'Cliente', 'Tipo de Documento', 'Fecha Emisión', 'Fecha Vencimiento',
        'Días hasta Vencimiento', 'Propiedad (Finca)', 'Ubicación', 'Estado'
    ])
    
    # Datos
    for vencimiento, cliente, propiedad in vencimientos:
        dias = vencimiento.dias_hasta_vencimiento()
        estado_calc = 'Vencido' if vencimiento.esta_vencido() else ('Próximo a vencer' if dias is not None and dias <= 30 else 'Vigente')
        
        writer.writerow([
            cliente.nombre_razon_social,
            vencimiento.tipo_documento,
            vencimiento.fecha_emision.strftime('%d/%m/%Y'),
            vencimiento.fecha_vencimiento.strftime('%d/%m/%Y'),
            dias if dias is not None else 'N/A',
            propiedad.finca if propiedad else 'Sin propiedad',
            f"{propiedad.departamento}, {propiedad.distrito}" if propiedad and propiedad.departamento else 'N/A',
            estado_calc
        ])
    
    output.seek(0)
    
    # Crear respuesta con archivo
    mem = io.BytesIO()
    mem.write(output.getvalue().encode('utf-8-sig'))  # BOM para Excel
    mem.seek(0)
    
    fecha_actual = date.today().strftime('%Y%m%d')
    filename = f'vencimientos_{fecha_actual}.csv'
    
    return send_file(
        mem,
        as_attachment=True,
        download_name=filename,
        mimetype='text/csv'
    )

# API endpoints
@bp.route('/api/propiedades-cliente/<int:cliente_id>')
@login_required
def api_propiedades_cliente(cliente_id):
    """API para obtener propiedades de un cliente específico"""
    propiedades = Propiedad.query.filter_by(id_cliente=cliente_id).order_by(Propiedad.finca.asc()).all()
    return jsonify([{
        'id': p.id_propiedad,
        'finca': p.finca or 'Sin finca',
        'ubicacion': f"{p.departamento}, {p.distrito}" if p.departamento and p.distrito else p.departamento or 'Sin ubicación'
    } for p in propiedades])

@bp.route('/api/procesar-notificaciones')
@login_required
def procesar_notificaciones():
    """API para procesar notificaciones automáticas (puede ser llamada por cron job)"""
    vencimientos = Vencimiento.query.all()
    notificaciones_enviadas = 0
    
    for vencimiento in vencimientos:
        tipo_notificacion = vencimiento.necesita_notificacion()
        if tipo_notificacion:
            # Verificar si ya existe la notificación
            existe = Notificacion.query.filter_by(
                id_vencimiento=vencimiento.id_vencimiento,
                tipo=tipo_notificacion
            ).first()
            
            if not existe:
                notificacion = Notificacion(
                    id_vencimiento=vencimiento.id_vencimiento,
                    tipo=tipo_notificacion,
                    fecha_envio=date.today()
                )
                db.session.add(notificacion)
                notificaciones_enviadas += 1
    
    if notificaciones_enviadas > 0:
        db.session.commit()
    
    return jsonify({
        'status': 'success',
        'notificaciones_enviadas': notificaciones_enviadas
    })