from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required
from ..extensions import db
from ..models import Cliente, Propiedad

bp = Blueprint('propiedades', __name__)

@bp.route('/')
@login_required
def list_propiedades():
    q = request.args.get('q', '')
    cliente_id = request.args.get('cliente_id', '')
    
    query = db.session.query(Propiedad, Cliente).join(Cliente)
    
    if q:
        query = query.filter(
            db.or_(
                Propiedad.finca.ilike(f'%{q}%'),
                Propiedad.matricula.ilike(f'%{q}%'),
                Propiedad.padron.ilike(f'%{q}%'),
                Cliente.nombre_razon_social.ilike(f'%{q}%')
            )
        )
    
    if cliente_id:
        query = query.filter(Propiedad.id_cliente == cliente_id)
    
    propiedades = query.order_by(Cliente.nombre_razon_social.asc(), Propiedad.finca.asc()).all()
    clientes = Cliente.query.order_by(Cliente.nombre_razon_social.asc()).all()
    
    return render_template('propiedades/list.html', 
                         propiedades=propiedades, 
                         clientes=clientes,
                         q=q, 
                         cliente_id=cliente_id)

@bp.route('/nueva', methods=['GET', 'POST'])
@login_required
def nueva_propiedad():
    if request.method == 'POST':
        try:
            p = Propiedad(
                id_cliente=request.form.get('id_cliente'),
                finca=request.form.get('finca'),
                matricula=request.form.get('matricula'),
                padron=request.form.get('padron'),
                superficie_ha=float(request.form.get('superficie_ha', 0)),
                departamento=request.form.get('departamento'),
                distrito=request.form.get('distrito'),
                coordenadas=request.form.get('coordenadas'),
                mapa_url=request.form.get('mapa_url')
            )
            db.session.add(p)
            db.session.commit()
            flash('Propiedad creada exitosamente', 'success')
            return redirect(url_for('propiedades.list_propiedades'))
        except Exception as e:
            flash('Error al crear la propiedad', 'error')
            db.session.rollback()
    
    clientes = Cliente.query.order_by(Cliente.nombre_razon_social.asc()).all()
    return render_template('propiedades/form.html', clientes=clientes)

@bp.route('/<int:id_propiedad>/editar', methods=['GET', 'POST'])
@login_required
def editar_propiedad(id_propiedad):
    propiedad = Propiedad.query.get_or_404(id_propiedad)
    
    if request.method == 'POST':
        try:
            # Manejar el mapa - priorizar archivo subido sobre URL
            mapa_url = propiedad.mapa_url  # Mantener el actual por defecto
            
            # Primero verificar si hay archivo subido
            if 'mapa_archivo' in request.files:
                file = request.files['mapa_archivo']
                if file.filename:
                    from flask import current_app
                    upload_folder = os.path.join(current_app.static_folder, 'uploads')
                    os.makedirs(upload_folder, exist_ok=True)
                    nueva_url = save_uploaded_file(file, upload_folder)
                    if nueva_url:
                        mapa_url = nueva_url
            
            # Si no hay archivo, verificar URL
            elif request.form.get('mapa_url', '').strip():
                mapa_url = request.form.get('mapa_url').strip()
            
            propiedad.id_cliente = request.form.get('id_cliente')
            propiedad.finca = request.form.get('finca')
            propiedad.matricula = request.form.get('matricula')
            propiedad.padron = request.form.get('padron')
            propiedad.superficie_ha = float(request.form.get('superficie_ha', 0))
            propiedad.departamento = request.form.get('departamento')
            propiedad.distrito = request.form.get('distrito')
            propiedad.coordenadas = request.form.get('coordenadas')
            propiedad.mapa_url = mapa_url
            
            db.session.commit()
            flash('Propiedad actualizada exitosamente', 'success')
            return redirect(url_for('propiedades.list_propiedades'))
        except Exception as e:
            flash(f'Error al actualizar la propiedad: {str(e)}', 'error')
            db.session.rollback()
    
    clientes = Cliente.query.order_by(Cliente.nombre_razon_social.asc()).all()
    return render_template('propiedades/form.html', propiedad=propiedad, clientes=clientes)

@bp.route('/<int:id_propiedad>/detalle')
@login_required
def detalle_propiedad(id_propiedad):
    propiedad = Propiedad.query.get_or_404(id_propiedad)
    cliente = Cliente.query.get(propiedad.id_cliente)
    
    # Obtener proyectos asociados a esta propiedad
    from ..models import Proyecto
    proyectos = Proyecto.query.filter_by(id_propiedad=id_propiedad).order_by(Proyecto.anho.desc()).all()
    
    return render_template('propiedades/detalle.html', 
                         propiedad=propiedad, 
                         cliente=cliente,
                         proyectos=proyectos)

@bp.route('/<int:id_propiedad>/eliminar', methods=['POST'])
@login_required
def eliminar_propiedad(id_propiedad):
    propiedad = Propiedad.query.get_or_404(id_propiedad)
    
    # Verificar si tiene proyectos asociados
    from ..models import Proyecto
    proyectos_count = Proyecto.query.filter_by(id_propiedad=id_propiedad).count()
    
    if proyectos_count > 0:
        flash(f'No se puede eliminar la propiedad porque tiene {proyectos_count} proyecto(s) asociado(s)', 'error')
        return redirect(url_for('propiedades.list_propiedades'))
    
    try:
        db.session.delete(propiedad)
        db.session.commit()
        flash('Propiedad eliminada exitosamente', 'success')
    except Exception as e:
        flash('Error al eliminar la propiedad', 'error')
        db.session.rollback()
    
    return redirect(url_for('propiedades.list_propiedades'))

@bp.route('/buscar')
@login_required
def buscar():
    q = request.args.get('q', '')
    propiedades = []
    if q:
        propiedades = db.session.query(Propiedad, Cliente).join(Cliente).filter(
            db.or_(
                Propiedad.finca.ilike(f'%{q}%'),
                Propiedad.matricula.ilike(f'%{q}%'),
                Propiedad.padron.ilike(f'%{q}%'),
                Cliente.nombre_razon_social.ilike(f'%{q}%')
            )
        ).order_by(Cliente.nombre_razon_social.asc()).all()
    
    return render_template('propiedades/search.html', q=q, propiedades=propiedades)

# API endpoint para obtener propiedades por cliente (útil para selects dinámicos)
@bp.route('/api/cliente/<int:cliente_id>')
@login_required
def api_propiedades_cliente(cliente_id):
    propiedades = Propiedad.query.filter_by(id_cliente=cliente_id).order_by(Propiedad.finca.asc()).all()
    return jsonify([{
        'id': p.id_propiedad,
        'finca': p.finca,
        'matricula': p.matricula,
        'padron': p.padron,
        'superficie_ha': float(p.superficie_ha) if p.superficie_ha else 0,
        'ubicacion': f"{p.departamento}, {p.distrito}" if p.departamento and p.distrito else ""
    } for p in propiedades])