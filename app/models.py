from datetime import date
from .extensions import db


class Cliente(db.Model):
    __tablename__ = 'CLIENTE'
    id_cliente = db.Column(db.Integer, primary_key=True)
    nombre_razon_social = db.Column(db.String(255))
    contacto = db.Column(db.String(255))
    ubicacion_general = db.Column(db.Text)
    saldo_total_pagado = db.Column(db.Numeric(12, 2), default=0)
    saldo_total_pendiente = db.Column(db.Numeric(12, 2), default=0)

    propiedades = db.relationship('Propiedad', backref='cliente', lazy=True)
    proyectos = db.relationship('Proyecto', backref='cliente', lazy=True)
    vencimientos = db.relationship('Vencimiento', backref='cliente', lazy=True)


class Propiedad(db.Model):
    __tablename__ = 'PROPIEDAD'
    id_propiedad = db.Column(db.Integer, primary_key=True)
    id_cliente = db.Column(db.Integer, db.ForeignKey('CLIENTE.id_cliente'))
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
    __tablename__ = 'PROYECTO'
    id_proyecto = db.Column(db.Integer, primary_key=True)
    id_cliente = db.Column(db.Integer, db.ForeignKey('CLIENTE.id_cliente'))
    anho = db.Column(db.Integer)
    institucion = db.Column(db.String(100))
    tipo_tramite = db.Column(db.String(100))
    fecha_firma_contrato = db.Column(db.Date)
    estado = db.Column(db.String(50))
    plazo_limite = db.Column(db.Date)
    id_propiedad = db.Column(db.Integer, db.ForeignKey('PROPIEDAD.id_propiedad'))

    documentos = db.relationship('DocumentoProyecto', backref='proyecto', lazy=True)
    pagos = db.relationship('Pago', backref='proyecto', lazy=True)
    facturas = db.relationship('Factura', backref='proyecto', lazy=True)


class DocumentoProyecto(db.Model):
    __tablename__ = 'DOCUMENTO_PROYECTO'
    id_documento = db.Column(db.Integer, primary_key=True)
    id_proyecto = db.Column(db.Integer, db.ForeignKey('PROYECTO.id_proyecto'))
    tipo = db.Column(db.String(100))
    archivo_url = db.Column(db.Text)


class Pago(db.Model):
    __tablename__ = 'PAGO'
    id_pago = db.Column(db.Integer, primary_key=True)
    id_proyecto = db.Column(db.Integer, db.ForeignKey('PROYECTO.id_proyecto'))
    monto_total = db.Column(db.Numeric(12, 2))
    porcentaje_pago_inicial = db.Column(db.Numeric(5, 2))
    saldo_restante = db.Column(db.Numeric(12, 2))


class Factura(db.Model):
    __tablename__ = 'FACTURA'
    id_factura = db.Column(db.Integer, primary_key=True)
    id_proyecto = db.Column(db.Integer, db.ForeignKey('PROYECTO.id_proyecto'))
    monto = db.Column(db.Numeric(12, 2))
    fecha_emision = db.Column(db.Date)
    comprobado = db.Column(db.Boolean, default=False)


class Vencimiento(db.Model):
    __tablename__ = 'VENCIMIENTO'
    id_vencimiento = db.Column(db.Integer, primary_key=True)
    id_cliente = db.Column(db.Integer, db.ForeignKey('CLIENTE.id_cliente'))
    tipo_documento = db.Column(db.String(100))
    fecha_emision = db.Column(db.Date)
    fecha_vencimiento = db.Column(db.Date)
    id_propiedad = db.Column(db.Integer, db.ForeignKey('PROPIEDAD.id_propiedad'))
    estado = db.Column(db.String(50))

    notificaciones = db.relationship('Notificacion', backref='vencimiento', lazy=True)


class Notificacion(db.Model):
    __tablename__ = 'NOTIFICACION'
    id_notificacion = db.Column(db.Integer, primary_key=True)
    id_vencimiento = db.Column(db.Integer, db.ForeignKey('VENCIMIENTO.id_vencimiento'))
    tipo = db.Column(db.String(50))
    fecha_envio = db.Column(db.Date, default=date.today)
