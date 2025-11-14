import os
from datetime import date, timedelta
from ..extensions import scheduler
from ..models import Vencimiento, Notificacion
from ..extensions import db


def notify(kind, venc):
    # Placeholder: aquí se podría enviar email/WhatsApp/Telegram
    n = Notificacion(id_vencimiento=venc.id_vencimiento, tipo=kind)
    db.session.add(n)
    db.session.commit()


def job_check_vencimientos():
    today = date.today()
    in_30 = today + timedelta(days=30)
    in_7 = today + timedelta(days=7)

    vencs_30 = Vencimiento.query.filter(Vencimiento.fecha_vencimiento == in_30).all()
    for v in vencs_30:
        notify('30_dias', v)

    vencs_7 = Vencimiento.query.filter(Vencimiento.fecha_vencimiento == in_7).all()
    for v in vencs_7:
        notify('7_dias', v)


def register_jobs(app):
    if not scheduler.running:
        scheduler.configure(timezone=os.getenv('SCHEDULER_TIMEZONE', 'UTC'))
        scheduler.add_job(job_check_vencimientos, 'cron', hour=7, minute=0, id='check_vencimientos', replace_existing=True)
        scheduler.start()

        # detener ordenado al cerrar
        @app.teardown_appcontext
        def shutdown(exception=None):
            if scheduler.running:
                scheduler.shutdown(wait=False)
