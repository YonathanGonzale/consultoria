import enum
from datetime import date
from decimal import Decimal
from sqlalchemy.ext.hybrid import hybrid_property
from .extensions import db


class Cliente(db.Model):
    __tablename__ = 'cliente'
    id_cliente = db.Column(db.Integer, primary_key=True)
    nombre_razon_social = db.Column(db.String(255))
    cedula_identidad = db.Column(db.String(100))
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


class ProyectoEstado(enum.Enum):
    en_proceso = 'en_proceso'
    licencia_emitida = 'licencia_emitida'


class Proyecto(db.Model):
    __tablename__ = 'proyecto'
    id_proyecto = db.Column(db.Integer, primary_key=True)
    id_cliente = db.Column(db.Integer, db.ForeignKey('cliente.id_cliente'))
    anho = db.Column(db.Integer)
    institucion = db.Column(db.String(100))
    nombre_proyecto = db.Column(db.String(255))
    subtipo = db.Column(db.String(100))
    anio_inicio = db.Column(db.Integer)
    exp_siam = db.Column(db.String(120))
    fecha_emision_licencia = db.Column(db.Date)
    fecha_vencimiento_licencia = db.Column(db.Date)
    costo_total = db.Column(db.Numeric(12, 2))
    porcentaje_entrega = db.Column(db.Numeric(5, 2))
    monto_entregado = db.Column(db.Numeric(12, 2))
    saldo_restante = db.Column(db.Numeric(12, 2))
    fecha_firma_contrato = db.Column(db.Date)
    estado = db.Column(
        db.Enum(ProyectoEstado, name='estado_proyecto_enum'),
        nullable=False,
        default=ProyectoEstado.en_proceso,
    )
    plazo_limite = db.Column(db.Date)
    id_propiedad = db.Column(db.Integer, db.ForeignKey('propiedad.id_propiedad'))
    lugar = db.Column(db.String(255))
    distrito = db.Column(db.String(150))
    departamento = db.Column(db.String(150))
    finca = db.Column(db.String(120))
    matricula = db.Column(db.String(120))
    padron = db.Column(db.String(120))
    lote = db.Column(db.String(120))
    manzana = db.Column(db.String(120))
    fraccion = db.Column(db.String(120))
    superficie = db.Column(db.Numeric(12, 2))
    mapa_archivo_url = db.Column(db.Text)
    factura_archivo_url = db.Column(db.Text)
    # Campos específicos para SENAVE
    senave_desglose = db.Column(db.Text)
    senave_tipo_concepto = db.Column(db.String(150))
    
    # Campos específicos para Bono de Servicios Ambientales
    de_quien_compro = db.Column(db.String(255))
    hectareas_bono = db.Column(db.Numeric(10, 2))
    anio_bono = db.Column(db.Integer)
    tipo_asociacion = db.Column(db.String(100))  # ALPROEA o APROSEC
    fecha_emision_bono = db.Column(db.Date)
    fecha_vencimiento_bono = db.Column(db.Date)
    pago_total_bono = db.Column(db.Numeric(12, 2))
    hectareas_finanzas = db.Column(db.Numeric(10, 2))
    precio_por_hectarea = db.Column(db.Numeric(12, 2))

    documentos = db.relationship('DocumentoProyecto', backref='proyecto', lazy=True)
    pagos = db.relationship('Pago', backref='proyecto', lazy=True)
    facturas = db.relationship('Factura', backref='proyecto', lazy=True)

    @hybrid_property
    def monto_entregado_calculado(self):
        if self.costo_total is None or self.porcentaje_entrega is None:
            return self.monto_entregado
        base = self.costo_total if self.costo_total is not None else Decimal('0')
        porcentaje = self.porcentaje_entrega if self.porcentaje_entrega is not None else Decimal('0')
        divisor = Decimal('100')
        return (base * porcentaje) / divisor

    @hybrid_property
    def saldo_restante_calculado(self):
        base = self.costo_total if self.costo_total is not None else Decimal('0')
        entregado = self.monto_entregado_calculado if self.monto_entregado_calculado is not None else Decimal('0')
        return base - entregado

    def actualizar_finanzas(self):
        """Recalcula los montos almacenados para mantener consistencia."""
        calculado = self.monto_entregado_calculado
        if calculado is not None:
            self.monto_entregado = calculado
        self.saldo_restante = self.saldo_restante_calculado
    
    def calcular_precio_por_hectarea(self):
        """Calcula automáticamente el precio por hectárea para Bono de Servicios Ambientales."""
        if self.pago_total_bono and self.hectareas_finanzas and self.hectareas_finanzas > 0:
            self.precio_por_hectarea = self.pago_total_bono / self.hectareas_finanzas
        else:
            self.precio_por_hectarea = None


class DocumentoProyecto(db.Model):
    __tablename__ = 'documento_proyecto'
    id_documento = db.Column(db.Integer, primary_key=True)
    id_proyecto = db.Column(db.Integer, db.ForeignKey('proyecto.id_proyecto'))
    tipo = db.Column(db.String(100))
    archivo_url = db.Column(db.Text)
    nombre_original = db.Column(db.String(255))
    categoria = db.Column(db.String(100))
    mime_type = db.Column(db.String(100))
    uploaded_at = db.Column(db.Date, default=date.today)


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
