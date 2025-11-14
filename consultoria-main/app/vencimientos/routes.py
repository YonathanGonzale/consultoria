from datetime import date, timedelta
from flask import Blueprint, render_template, request
from flask_login import login_required
from ..models import Vencimiento, Cliente

bp = Blueprint('vencimientos', __name__)

@bp.route('/')
@login_required
def list_vencimientos():
    mes = request.args.get('mes')
    cliente_id = request.args.get('cliente_id')
    query = Vencimiento.query
    if mes:
        query = query.filter(Vencimiento.fecha_vencimiento.between(f'{mes}-01', f'{mes}-31'))
    if cliente_id:
        query = query.filter_by(id_cliente=cliente_id)
    vencs = query.order_by(Vencimiento.fecha_vencimiento.asc()).all()
    clientes = Cliente.query.order_by(Cliente.nombre_razon_social.asc()).all()
    return render_template('vencimientos/list.html', vencimientos=vencs, clientes=clientes)
