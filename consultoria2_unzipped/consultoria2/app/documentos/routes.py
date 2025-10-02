import os
from uuid import uuid4
from flask import Blueprint, request, redirect, url_for, flash, current_app
from flask_login import login_required
from werkzeug.utils import secure_filename

bp = Blueprint('documentos', __name__)
ALLOWED_EXT = {'pdf', 'png', 'jpg', 'jpeg', 'doc', 'docx', 'xlsx', 'zip', 'rar', 'shp'}

@bp.route('/upload', methods=['POST'])
@login_required
def upload():
    f = request.files.get('file')
    if not f:
        flash('No se envió archivo', 'warning')
        return redirect(request.referrer or url_for('dashboard.index'))
    ext = f.filename.rsplit('.', 1)[-1].lower()
    if ext not in ALLOWED_EXT:
        flash('Tipo de archivo no permitido', 'danger')
        return redirect(request.referrer or url_for('dashboard.index'))
    fname = secure_filename(f"{uuid4().hex}.{ext}")
    save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], fname)
    f.save(save_path)
    flash('Archivo subido', 'success')
    return redirect(request.referrer or url_for('dashboard.index'))
