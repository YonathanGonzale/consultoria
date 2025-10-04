from datetime import date, timedelta
from flask import Blueprint, render_template, request
from flask_login import login_required
from ..models import Vencimiento, Cliente, Proyecto

bp = Blueprint('vencimientos', __name__)

@bp.route('/')
@login_required
def list_vencimientos():
    mes = request.args.get('mes')
    cliente_id = request.args.get('cliente_id')
    
    # Consultar PROYECTOS en lugar de vencimientos
    query = Proyecto.query.join(Cliente)
    
    if mes:
        # Filtrar por mes del plazo_limite
        query = query.filter(Proyecto.plazo_limite.between(f'{mes}-01', f'{mes}-31'))
    if cliente_id:
        query = query.filter_by(id_cliente=cliente_id)
    
    # Solo proyectos que tengan plazo_limite definido
    # Ordenar por plazo_limite ascendente (los más vencidos primero)
    proyectos = query.filter(Proyecto.plazo_limite.isnot(None)).order_by(Proyecto.plazo_limite.asc()).all()

    # Calcular color y días restantes para cada proyecto
    hoy = date.today()
    for proyecto in proyectos:
        dias = (proyecto.plazo_limite - hoy).days
        proyecto.dias_restantes = dias
        
        if dias < 0:
            proyecto.row_class = 'table-danger-custom'  # rojo intenso - vencido
        else:
            proyecto.row_class = ''  # sin resaltado para los demás

    clientes = Cliente.query.order_by(Cliente.nombre_razon_social.asc()).all()
    return render_template('vencimientos/list.html', proyectos=proyectos, clientes=clientes)
