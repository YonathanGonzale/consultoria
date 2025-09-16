from flask import Blueprint, render_template, request
from flask_login import login_required
from datetime import datetime, date, timedelta
from sqlalchemy import func, extract, and_, or_
from ..models import Cliente, Proyecto, Vencimiento, Pago, Factura, Propiedad
from ..extensions import db

bp = Blueprint('dashboard', __name__)

@bp.route('/')
@login_required
def index():
    # Filtros opcionales
    cliente_id = request.args.get('cliente_id', type=int)
    año_filtro = request.args.get('año', type=int, default=datetime.now().year)
    
    # Métricas básicas
    total_clientes = db.session.query(Cliente).count()
    total_proyectos = db.session.query(Proyecto).count()
    total_propiedades = db.session.query(Propiedad).count()
    
    # Métricas por año y cliente (si se especifica)
    query_proyectos = db.session.query(Proyecto)
    if cliente_id:
        query_proyectos = query_proyectos.filter(Proyecto.id_cliente == cliente_id)
    if año_filtro:
        query_proyectos = query_proyectos.filter(Proyecto.anho == año_filtro)
    
    proyectos_año = query_proyectos.all()
    
    # Estadísticas de proyectos por estado
    stats_estados = {
        'en_proceso': len([p for p in proyectos_año if p.estado and p.estado.lower() == 'en proceso']),
        'entregado': len([p for p in proyectos_año if p.estado and p.estado.lower() == 'entregado']),
        'finalizado': len([p for p in proyectos_año if p.estado and p.estado.lower() == 'finalizado']),
        'pendiente': len([p for p in proyectos_año if not p.estado or p.estado.lower() == 'pendiente'])
    }
    
    # Estadísticas por institución
    stats_instituciones = {}
    for proyecto in proyectos_año:
        inst = proyecto.institucion or 'Sin institución'
        stats_instituciones[inst] = stats_instituciones.get(inst, 0) + 1
    
    # Cálculos financieros
    total_facturado = 0
    total_pendiente = 0
    
    for proyecto in proyectos_año:
        # Obtener pagos del proyecto
        pagos = db.session.query(Pago).filter_by(id_proyecto=proyecto.id_proyecto).all()
        facturas = db.session.query(Factura).filter_by(id_proyecto=proyecto.id_proyecto).all()
        
        if pagos:
            monto_total = float(pagos[0].monto_total or 0)
            facturado = sum(float(f.monto or 0) for f in facturas)
            total_facturado += facturado
            total_pendiente += max(0, monto_total - facturado)
    
    # Vencimientos próximos (30 días)
    fecha_limite = date.today() + timedelta(days=30)
    query_vencimientos = db.session.query(Vencimiento, Cliente).join(Cliente).filter(
        Vencimiento.fecha_vencimiento >= date.today(),
        Vencimiento.fecha_vencimiento <= fecha_limite
    )
    if cliente_id:
        query_vencimientos = query_vencimientos.filter(Vencimiento.id_cliente == cliente_id)
    
    proximos_venc = query_vencimientos.order_by(Vencimiento.fecha_vencimiento.asc()).limit(10).all()
    
    # Vencimientos críticos (7 días)
    fecha_critica = date.today() + timedelta(days=7)
    vencimientos_criticos = db.session.query(Vencimiento).filter(
        Vencimiento.fecha_vencimiento >= date.today(),
        Vencimiento.fecha_vencimiento <= fecha_critica
    ).count()
    
    # Vencimientos vencidos
    vencimientos_vencidos = db.session.query(Vencimiento).filter(
        Vencimiento.fecha_vencimiento < date.today()
    ).count()
    
    # Proyectos por mes (últimos 6 meses)
    stats_meses = []
    for i in range(6):
        mes_fecha = date.today() - timedelta(days=30*i)
        cantidad = db.session.query(Proyecto).filter(
            extract('month', Proyecto.fecha_firma_contrato) == mes_fecha.month,
            extract('year', Proyecto.fecha_firma_contrato) == mes_fecha.year
        ).count()
        stats_meses.append({
            'mes': mes_fecha.strftime('%B'),
            'año': mes_fecha.year,
            'cantidad': cantidad
        })
    stats_meses.reverse()
    
    # Lista de clientes para el filtro
    clientes = db.session.query(Cliente).order_by(Cliente.nombre_razon_social.asc()).all()
    
    # Años disponibles
    años_disponibles = db.session.query(Proyecto.anho).distinct().filter(
        Proyecto.anho.isnot(None)
    ).order_by(Proyecto.anho.desc()).all()
    años_disponibles = [a[0] for a in años_disponibles if a[0]]
    
    # Cliente seleccionado
    cliente_seleccionado = None
    if cliente_id:
        cliente_seleccionado = db.session.query(Cliente).get(cliente_id)
    
    return render_template('dashboard/index.html',
                         # Métricas básicas
                         total_clientes=total_clientes,
                         total_proyectos=total_proyectos,
                         total_propiedades=total_propiedades,
                         
                         # Métricas filtradas
                         proyectos_año=len(proyectos_año),
                         stats_estados=stats_estados,
                         stats_instituciones=stats_instituciones,
                         
                         # Financiero
                         total_facturado=total_facturado,
                         total_pendiente=total_pendiente,
                         
                         # Vencimientos
                         proximos_venc=proximos_venc,
                         vencimientos_criticos=vencimientos_criticos,
                         vencimientos_vencidos=vencimientos_vencidos,
                         
                         # Gráficos
                         stats_meses=stats_meses,
                         
                         # Filtros
                         clientes=clientes,
                         años_disponibles=años_disponibles,
                         cliente_id=cliente_id,
                         año_filtro=año_filtro,
                         cliente_seleccionado=cliente_seleccionado)