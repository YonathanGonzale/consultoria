from datetime import date
from .extensions import db


class Cliente(db.Model):
    __tablename__ = 'cliente'
    id_cliente = db.Column(db.Integer, primary_key=True)
    nombre_razon_social = db.Column(db.String(255))
    cedula_identidad = db.Column(db.String(100))
    contacto = db.Column(db.String(255))
    telefono = db.Column(db.String(100))
    correo_electronico = db.Column(db.String(255))
    departamento = db.Column(db.String(150))
    distrito = db.Column(db.String(150))
    lugar = db.Column(db.String(255))
    ubicacion_general = db.Column(db.Text)
    ubicacion_gps = db.Column(db.Text)
    saldo_total_pagado = db.Column(db.Numeric(12, 2), default=0)
    saldo_total_pendiente = db.Column(db.Numeric(12, 2), default=0)

    propiedades = db.relationship('Propiedad', backref='cliente', lazy=True)
    proyectos = db.relationship('Proyecto', backref='cliente', lazy=True)
    vencimientos = db.relationship('Vencimiento', backref='cliente', lazy=True)
    documentos = db.relationship(
        'DocumentoCliente',
        backref='cliente',
        lazy=True,
        cascade='all, delete-orphan',
        order_by='DocumentoCliente.id_documento.desc()'
    )


class Propiedad(db.Model):
    __tablename__ = 'propiedad'
    id_propiedad = db.Column(db.Integer, primary_key=True)
    id_cliente = db.Column(db.Integer, db.ForeignKey('cliente.id_cliente'))
    finca = db.Column(db.String(100))
    matricula = db.Column(db.String(100))
    padron = db.Column(db.String(100))
    superficie_ha = db.Column(db.Numeric(10, 2))
    departamento = db.Column(db.String(100))
    distrito = db.Column(db.String(100))
    coordenadas = db.Column(db.String(255))
    mapa_url = db.Column(db.Text)

    proyectos = db.relationship('Proyecto', backref='propiedad', lazy=True)
    vencimientos = db.relationship('Vencimiento', backref='propiedad', lazy=True)


class Proyecto(db.Model):
    __tablename__ = 'proyecto'
    id_proyecto = db.Column(db.Integer, primary_key=True)
    id_cliente = db.Column(db.Integer, db.ForeignKey('cliente.id_cliente'))
    anho = db.Column(db.Integer)
    institucion = db.Column(db.String(100))
    tipo_tramite = db.Column(db.String(100))
    fecha_firma_contrato = db.Column(db.Date)
    estado = db.Column(db.String(50))
    plazo_limite = db.Column(db.Date)
    id_propiedad = db.Column(db.Integer, db.ForeignKey('propiedad.id_propiedad'))

    documentos = db.relationship('DocumentoProyecto', backref='proyecto', lazy=True)
    pagos = db.relationship('Pago', backref='proyecto', lazy=True)
    facturas = db.relationship('Factura', backref='proyecto', lazy=True)


class DocumentoProyecto(db.Model):
    __tablename__ = 'documento_proyecto'
    id_documento = db.Column(db.Integer, primary_key=True)
    id_proyecto = db.Column(db.Integer, db.ForeignKey('proyecto.id_proyecto'))
    tipo = db.Column(db.String(100))
    archivo_url = db.Column(db.Text)


class Pago(db.Model):
    __tablename__ = 'pago'
    id_pago = db.Column(db.Integer, primary_key=True)
    id_proyecto = db.Column(db.Integer, db.ForeignKey('proyecto.id_proyecto'))
    monto_total = db.Column(db.Numeric(12, 2))
    porcentaje_pago_inicial = db.Column(db.Numeric(5, 2))
    saldo_restante = db.Column(db.Numeric(12, 2))


class Factura(db.Model):
    __tablename__ = 'factura'
    id_factura = db.Column(db.Integer, primary_key=True)
    id_proyecto = db.Column(db.Integer, db.ForeignKey('proyecto.id_proyecto'))
    monto = db.Column(db.Numeric(12, 2))
    fecha_emision = db.Column(db.Date)
    comprobado = db.Column(db.Boolean, default=False)


class Vencimiento(db.Model):
    __tablename__ = 'vencimiento'
    id_vencimiento = db.Column(db.Integer, primary_key=True)
    id_cliente = db.Column(db.Integer, db.ForeignKey('cliente.id_cliente'))
    tipo_documento = db.Column(db.String(100))
    fecha_emision = db.Column(db.Date)
    fecha_vencimiento = db.Column(db.Date)
    id_propiedad = db.Column(db.Integer, db.ForeignKey('propiedad.id_propiedad'))
    estado = db.Column(db.String(50))

    notificaciones = db.relationship('Notificacion', backref='vencimiento', lazy=True)


class Notificacion(db.Model):
    __tablename__ = 'notificacion'
    id_notificacion = db.Column(db.Integer, primary_key=True)
    id_vencimiento = db.Column(db.Integer, db.ForeignKey('vencimiento.id_vencimiento'))
    tipo = db.Column(db.String(50))
    fecha_envio = db.Column(db.Date, default=date.today)


class DocumentoCliente(db.Model):
    __tablename__ = 'documento_cliente'
    id_documento = db.Column(db.Integer, primary_key=True)
    id_cliente = db.Column(db.Integer, db.ForeignKey('cliente.id_cliente'), nullable=False)
    nombre_original = db.Column(db.String(255))
    archivo_url = db.Column(db.Text, nullable=False)
    mime_type = db.Column(db.String(100))
    uploaded_at = db.Column(db.Date, default=date.today)
