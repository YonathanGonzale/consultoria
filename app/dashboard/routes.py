from flask import Blueprint, render_template, request
from flask_login import login_required
from ..models import Cliente, Proyecto
from ..extensions import db
from datetime import date
import math
bp = Blueprint('dashboard', __name__)

PAGE_SIZE_OPTIONS = (10, 20, 30, 40, 50, 100)


class ListPagination:
    def __init__(self, page, per_page, total):
        self.per_page = per_page if per_page and per_page > 0 else PAGE_SIZE_OPTIONS[0]
        self.total = max(total, 0)
        self.pages = math.ceil(self.total / self.per_page) if self.total else 0
        if self.pages == 0:
            self.page = 1
        else:
            self.page = max(1, min(page, self.pages))

    @property
    def has_prev(self):
        return self.page > 1

    @property
    def has_next(self):
        return self.pages > 0 and self.page < self.pages

    @property
    def prev_num(self):
        return self.page - 1

    @property
    def next_num(self):
        return self.page + 1

    def iter_pages(self, left_edge=2, left_current=2, right_current=2, right_edge=2):
        last = 0
        for num in range(1, self.pages + 1):
            if (
                num <= left_edge
                or (num > self.page - left_current - 1 and num < self.page + right_current)
                or num > self.pages - right_edge
            ):
                if last + 1 != num:
                    yield None
                yield num
                last = num

@bp.route('/')
@login_required
def index():
    page = request.args.get('page', type=int, default=1)
    per_page = request.args.get('per_page', type=int, default=PAGE_SIZE_OPTIONS[0])
    if per_page not in PAGE_SIZE_OPTIONS:
        per_page = PAGE_SIZE_OPTIONS[0]
    if page < 1:
        page = 1

    total_clientes = db.session.query(Cliente).count()
    hoy = date.today()
    proyectos = (
        db.session.query(Proyecto)
        .filter(Proyecto.fecha_vencimiento_licencia.isnot(None))
        .all()
    )

    def _orden_proximidad(proyecto):
        dias = (proyecto.fecha_vencimiento_licencia - hoy).days
        if dias < 0:
            return (0, dias, proyecto.fecha_vencimiento_licencia)
        return (1, dias, proyecto.fecha_vencimiento_licencia)

    proximos_items = []
    for proyecto in sorted(proyectos, key=_orden_proximidad):
        dias_restantes = (proyecto.fecha_vencimiento_licencia - hoy).days
        if dias_restantes <= 30:
            badge_class = 'bg-danger'
        elif dias_restantes <= 60:
            badge_class = 'bg-warning text-dark'
        elif dias_restantes <= 90:
            badge_class = 'bg-success'
        else:
            badge_class = 'bg-secondary'

        proximos_items.append({
            'proyecto': proyecto,
            'dias_restantes': dias_restantes,
            'badge_class': badge_class,
        })

    pagination = ListPagination(page, per_page, len(proximos_items))
    start = (pagination.page - 1) * pagination.per_page
    end = start + pagination.per_page
    proximos_page_items = proximos_items[start:end]

    return render_template(
        'dashboard/index.html',
        total_clientes=total_clientes,
        proximos_items=proximos_page_items,
        pagination=pagination,
        per_page_options=PAGE_SIZE_OPTIONS,
    )
