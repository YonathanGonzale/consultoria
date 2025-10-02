from datetime import date
from .extensions import db

class Cliente(db.Model):
    __tablename__ = 'cliente'
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

    def __repr__(self):
        return f'<Propiedad {self.finca or self.id_propiedad}>'
    
    @property
    def display_name(self):
        """Retorna un nombre para mostrar de la propiedad"""
        if self.finca:
            return f"Finca {self.finca}"
        elif self.matricula:
            return f"Matrícula {self.matricula}"
        elif self.padron:
            return f"Padrón {self.padron}"
        else:
            return f"Propiedad #{self.id_propiedad}"
    
    @property
    def ubicacion_completa(self):
        """Retorna la ubicación completa de la propiedad"""
        partes = []
        if self.distrito:
            partes.append(self.distrito)
        if self.departamento:
            partes.append(self.departamento)
        return ", ".join(partes) if partes else None
    
    def to_dict(self):
        """Convierte el objeto a diccionario para APIs"""
        return {
            'id_propiedad': self.id_propiedad,
            'id_cliente': self.id_cliente,
            'finca': self.finca,
            'matricula': self.matricula,
            'padron': self.padron,
            'superficie_ha': float(self.superficie_ha) if self.superficie_ha else None,
            'departamento': self.departamento,
            'distrito': self.distrito,
            'coordenadas': self.coordenadas,
            'mapa_url': self.mapa_url,
            'display_name': self.display_name,
            'ubicacion_completa': self.ubicacion_completa
        }


class Proyecto(db.Model):
    __tablename__ = 'proyecto'
    id_proyecto = db.Column(db.Integer, primary_key=True)
    id_cliente = db.Column(db.Integer, db.ForeignKey('cliente.id_cliente'))
    id_propiedad = db.Column(db.Integer, db.ForeignKey('propiedad.id_propiedad'))
    anho = db.Column(db.Integer)
    institucion = db.Column(db.String(100))
    tipo_tramite = db.Column(db.String(100))
    fecha_firma_contrato = db.Column(db.Date)
    estado = db.Column(db.String(50))
    plazo_limite = db.Column(db.Date)

    documentos = db.relationship('DocumentoProyecto', backref='proyecto', lazy=True)
    pagos = db.relationship('Pago', backref='proyecto', lazy=True)
    facturas = db.relationship('Factura', backref='proyecto', lazy=True)
    def __repr__(self):
        return f'<Proyecto {self.tipo_tramite} - {self.anho}>'
    
    @property
    def dias_restantes(self):
        """Retorna los días restantes hasta el plazo límite"""
        if not self.plazo_limite:
            return None
        from datetime import date
        delta = self.plazo_limite - date.today()
        return delta.days
    
    @property
    def esta_vencido(self):
        """Verifica si el proyecto está vencido"""
        dias = self.dias_restantes
        return dias is not None and dias < 0
    
    @property
    def esta_por_vencer(self):
        """Verifica si el proyecto está por vencer (7 días o menos)"""
        dias = self.dias_restantes
        return dias is not None and 0 <= dias <= 7
    
    @property
    def display_name(self):
        """Retorna un nombre descriptivo del proyecto"""
        return f"{self.tipo_tramite} - {self.anho}"
    
    @property
    def total_facturado(self):
        """Calcula el total facturado del proyecto"""
        return sum(f.monto for f in self.facturas)
    
    @property
    def porcentaje_facturado(self):
        """Calcula el porcentaje facturado respecto al monto total"""
        if not self.pagos or not self.pagos[0].monto_total:
            return 0
        total = self.pagos[0].monto_total
        facturado = self.total_facturado
        return (facturado / total * 100) if total > 0 else 0
    
    def to_dict(self):
        """Convierte el objeto a diccionario para APIs"""
        return {
            'id_proyecto': self.id_proyecto,
            'id_cliente': self.id_cliente,
            'id_propiedad': self.id_propiedad,
            'anho': self.anho,
            'institucion': self.institucion,
            'tipo_tramite': self.tipo_tramite,
            'fecha_firma_contrato': self.fecha_firma_contrato.isoformat() if self.fecha_firma_contrato else None,
            'estado': self.estado,
            'plazo_limite': self.plazo_limite.isoformat() if self.plazo_limite else None,
            'display_name': self.display_name,
            'dias_restantes': self.dias_restantes,
            'esta_vencido': self.esta_vencido,
            'esta_por_vencer': self.esta_por_vencer
        }


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
    id_propiedad = db.Column(db.Integer, db.ForeignKey('propiedad.id_propiedad'))
    tipo_documento = db.Column(db.String(100))
    fecha_emision = db.Column(db.Date)
    fecha_vencimiento = db.Column(db.Date)
    estado = db.Column(db.String(50))

    notificaciones = db.relationship('Notificacion', backref='vencimiento', lazy=True)


class Notificacion(db.Model):
    __tablename__ = 'notificacion'
    id_notificacion = db.Column(db.Integer, primary_key=True)
    id_vencimiento = db.Column(db.Integer, db.ForeignKey('vencimiento.id_vencimiento'))
    tipo = db.Column(db.String(50))
    fecha_envio = db.Column(db.Date, default=date.today)