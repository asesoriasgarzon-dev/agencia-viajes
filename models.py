from datetime import datetime

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()

ROLES = ["admin", "asesor", "caja", "facturacion"]

ESTADOS = [
    ("borrador", "En cotización (asesor)"),
    ("pendiente_caja", "Esperando caja"),
    ("pendiente_facturacion", "Esperando facturación"),
    ("facturado", "Facturado"),
]

CONCEPTOS = ["VENTA", "CARTERA", "RC"]


def _num(valor):
    return float(valor) if valor else 0.0


class Usuario(db.Model, UserMixin):
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    nombre = db.Column(db.String(120), nullable=False)
    rol = db.Column(db.String(20), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Venta(db.Model):
    """
    Los campos y las fórmulas de esta tabla replican el archivo de control
    que ya usa la agencia ("Control agencia de viajes.xlsx", hoja mensual),
    para no reinventar cómo calculan la Tarifa de Agencia (T.A.) y el IVA.
    """

    __tablename__ = "ventas"

    id = db.Column(db.Integer, primary_key=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    ultima_actualizacion = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    asesor_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"))
    cajero_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"))
    facturador_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"))

    # --- Datos de la venta (columnas B-I del Excel) ---
    fecha_venta = db.Column(db.Date, default=datetime.utcnow)
    sede = db.Column(db.String(50))
    origen_venta = db.Column(db.String(80))
    ciudad_cliente = db.Column(db.String(80))
    destino = db.Column(db.String(120))
    descripcion_viaje = db.Column(db.String(255))

    # --- Datos del titular/comprador (columnas J-M) ---
    # NO son columnas propias: el titular es el pasajero con es_principal=True
    # (ver propiedades titular_nombre/titular_documento/titular_telefono más
    # abajo). Antes existían como cedula_id/nombre_cliente/telefono1
    # duplicando lo que ya se captura en Pasajero — se eliminaron para que
    # el asesor no tenga que escribir al comprador dos veces.
    contacto_emergencia = db.Column(db.String(150))

    # --- Venta y cartera (columnas N-W) ---
    concepto = db.Column(db.String(20), default="VENTA")  # VENTA / CARTERA / RC
    valor_venta_real = db.Column(db.Numeric(14, 2), default=0)
    cuenta = db.Column(db.String(80))
    valor_datafono = db.Column(db.Numeric(14, 2), default=0)
    valor_banco = db.Column(db.Numeric(14, 2), default=0)
    ultimos4_cuenta = db.Column(db.String(10))
    valor_efectivo = db.Column(db.Numeric(14, 2), default=0)
    fecha_maxima_pago = db.Column(db.Date)
    fecha_venta_inicial_cartera = db.Column(db.Date)
    fecha_viaje = db.Column(db.Date)

    # --- Proveedores y costos (columnas Y-AL) ---
    proveedor_tiquete = db.Column(db.String(120))
    costo_tiquetes = db.Column(db.Numeric(14, 2), default=0)
    proveedor_conexion = db.Column(db.String(120))
    costo_conexion = db.Column(db.Numeric(14, 2), default=0)
    proveedor_asistencia = db.Column(db.String(120))
    costo_asistencia = db.Column(db.Numeric(14, 2), default=0)
    proveedor_hotel = db.Column(db.String(120))
    costo_hotel = db.Column(db.Numeric(14, 2), default=0)
    amadeus = db.Column(db.Numeric(14, 2), default=0)
    fi_bancario = db.Column(db.Numeric(14, 2), default=0)
    descripcion_obsequio = db.Column(db.String(150))
    costo_obsequio = db.Column(db.Numeric(14, 2), default=0)
    descripcion_receptivos = db.Column(db.String(150))
    costo_receptivos = db.Column(db.Numeric(14, 2), default=0)

    tiene_contrato = db.Column(db.Boolean, default=False)
    observaciones = db.Column(db.Text)

    estado = db.Column(db.String(30), default="borrador")
    numero_factura = db.Column(db.String(50))
    fecha_facturacion = db.Column(db.DateTime)

    asesor = db.relationship("Usuario", foreign_keys=[asesor_id])
    cajero = db.relationship("Usuario", foreign_keys=[cajero_id])
    facturador = db.relationship("Usuario", foreign_keys=[facturador_id])

    pasajeros = db.relationship(
        "Pasajero", backref="venta", cascade="all, delete-orphan"
    )

    # ---- Fórmulas (mismas que las columnas AM-AT del Excel) ----

    @property
    def total_costos(self):
        return sum(
            _num(v)
            for v in (
                self.costo_tiquetes,
                self.costo_conexion,
                self.costo_asistencia,
                self.costo_hotel,
                self.amadeus,
                self.fi_bancario,
                self.costo_obsequio,
                self.costo_receptivos,
            )
        )

    @property
    def total_recibido(self):
        # Igual que el Excel: la T.A. se calcula sobre banco + efectivo
        # (el datafono queda fuera de esa cuenta en su plantilla actual).
        return _num(self.valor_banco) + _num(self.valor_efectivo)

    @property
    def saldo_pendiente(self):
        recibido = _num(self.valor_datafono) + _num(self.valor_banco) + _num(self.valor_efectivo)
        return _num(self.valor_venta_real) - recibido

    @property
    def ta_antes_iva(self):
        if self.concepto in ("VENTA", "RC"):
            return self.total_recibido - self.total_costos
        return 0

    @property
    def iva_ta(self):
        return self.ta_antes_iva / 1.19 * 0.19

    @property
    def ta_despues_iva(self):
        return self.ta_antes_iva - self.iva_ta

    @property
    def cartera_antes_iva(self):
        if self.concepto == "CARTERA":
            return self.total_recibido - self.total_costos
        return 0

    @property
    def iva_cartera(self):
        return self.cartera_antes_iva / 1.19 * 0.19

    @property
    def cartera_despues_iva(self):
        return self.cartera_antes_iva - self.iva_cartera

    @property
    def cartera_por_cobrar(self):
        if self.concepto == "CARTERA":
            return self.saldo_pendiente
        return 0

    @property
    def pasajero_principal(self):
        for p in self.pasajeros:
            if p.es_principal:
                return p
        return self.pasajeros[0] if self.pasajeros else None

    @property
    def titular_nombre(self):
        p = self.pasajero_principal
        if not p:
            return ""
        return f"{p.nombres or ''} {p.apellidos or ''}".strip()

    @property
    def titular_documento(self):
        p = self.pasajero_principal
        return p.numero_documento if p else ""

    @property
    def titular_telefono(self):
        p = self.pasajero_principal
        return p.telefono if p else ""

    @property
    def pax(self):
        # Única fuente de verdad: el conteo real de pasajeros. No es una
        # columna aparte para que no pueda quedar desincronizada (ej. pax=6
        # con solo 2 pasajeros cargados).
        return len(self.pasajeros)

    @property
    def estado_label(self):
        return dict(ESTADOS).get(self.estado, self.estado)

    @property
    def pasos_progreso(self):
        """Para el indicador visual Asesor → Caja → Facturación → Exportables."""
        orden = {"borrador": 0, "pendiente_caja": 1, "pendiente_facturacion": 2, "facturado": 3}
        idx = orden.get(self.estado, 0)
        etiquetas = ["Asesor", "Caja", "Facturación", "Exportables"]
        pasos = []
        for i, etiqueta in enumerate(etiquetas):
            if self.estado == "facturado" or i < idx:
                simbolo = "check"
            elif i == idx:
                simbolo = "activo"
            else:
                simbolo = "pendiente"
            pasos.append((etiqueta, simbolo))
        return pasos


class Pasajero(db.Model):
    """Roster opcional con el detalle de cada viajero (además del cliente
    principal que ya queda en la venta), para no repetir el problema de
    las 28 hojas de papel por pasajero."""

    __tablename__ = "pasajeros"

    id = db.Column(db.Integer, primary_key=True)
    venta_id = db.Column(db.Integer, db.ForeignKey("ventas.id"), nullable=False)

    es_principal = db.Column(db.Boolean, default=False)
    nombres = db.Column(db.String(120))
    apellidos = db.Column(db.String(120))
    tipo_documento = db.Column(db.String(20))
    numero_documento = db.Column(db.String(30))
    fecha_nacimiento = db.Column(db.String(20))
    telefono = db.Column(db.String(30))
    email = db.Column(db.String(120))


# Catálogo único de campos exportables. Ambos exportadores (contador y
# tributario) leen de aquí y de las mismas propiedades de Venta/Pasajero —
# esto NO crea un segundo lugar de captura, solo decide qué columnas de la
# MISMA información salen en cada archivo.
# Tupla: (campo, etiqueta, incluir_en_contador_por_defecto, incluir_en_dian_por_defecto)
CAMPOS_EXPORTABLES = [
    ("fecha_venta", "Fecha de venta", True, True),
    ("numero_factura", "Número de factura", True, True),
    ("titular_documento", "Documento del titular", True, True),
    ("titular_nombre", "Nombre del titular", True, True),
    ("ciudad_cliente", "Ciudad del cliente", False, True),
    ("destino", "Destino", True, False),
    ("concepto", "Concepto", True, True),
    ("valor_venta_real", "Valor venta real", True, True),
    ("total_costos", "Total costos", True, False),
    ("ta_antes_iva", "T.A. antes de IVA", True, False),
    ("iva_ta", "IVA 19% (T.A., el impuesto)", True, True),
    ("ta_despues_iva", "T.A. después de IVA", True, False),
    ("estado", "Estado", True, True),
    ("asesor", "Asesora", True, False),
    ("sede", "Sede", False, False),
    ("origen_venta", "Origen de la venta", False, False),
    ("pax", "# PAX", True, False),
    ("proveedores", "Proveedores (tiquete/conexión/asistencia/hotel)", False, False),
    ("forma_pago", "Forma de pago (datafono/banco/efectivo)", True, True),
    ("saldo_pendiente", "Saldo pendiente", True, False),
    ("cartera_por_cobrar", "Cartera por cobrar", True, False),
]


class ExportConfig(db.Model):
    __tablename__ = "export_config"

    id = db.Column(db.Integer, primary_key=True)
    campo = db.Column(db.String(50), unique=True, nullable=False)
    etiqueta = db.Column(db.String(120), nullable=False)
    incluir_contador = db.Column(db.Boolean, default=True)
    incluir_dian = db.Column(db.Boolean, default=False)


def seed_defaults():
    """Crea usuarios de ejemplo y la configuración de exportación si la base está vacía."""
    if Usuario.query.count() == 0:
        defaults = [
            ("admin", "admin123", "Administrador", "admin"),
            ("asesor1", "asesor123", "Asesor Comercial", "asesor"),
            ("caja1", "caja123", "Cajera", "caja"),
            ("facturacion1", "factura123", "Facturación Electrónica", "facturacion"),
        ]
        for username, password, nombre, rol in defaults:
            u = Usuario(username=username, nombre=nombre, rol=rol)
            u.set_password(password)
            db.session.add(u)

    if ExportConfig.query.count() == 0:
        for campo, etiqueta, incluir_contador, incluir_dian in CAMPOS_EXPORTABLES:
            db.session.add(
                ExportConfig(
                    campo=campo,
                    etiqueta=etiqueta,
                    incluir_contador=incluir_contador,
                    incluir_dian=incluir_dian,
                )
            )

    db.session.commit()


def seed_demo_ventas():
    """Deja 5 ventas de ejemplo, una en cada etapa del proceso, para que la
    demo arranque poblada (útil sobre todo en Railway, donde el disco es
    efímero y la base se reinicia en cada despliegue)."""
    if Venta.query.count() > 0:
        return

    from datetime import date as _date

    asesor = Usuario.query.filter_by(username="asesor1").first()
    caja = Usuario.query.filter_by(username="caja1").first()
    facturacion = Usuario.query.filter_by(username="facturacion1").first()
    if not (asesor and caja and facturacion):
        return

    hoy = _date.today()

    def _pasajero(nombres, apellidos, doc, tipo="CC", telefono=None, principal=False):
        return Pasajero(
            nombres=nombres, apellidos=apellidos, tipo_documento=tipo,
            numero_documento=doc, telefono=telefono, es_principal=principal,
        )

    # 1) Borrador — el asesor todavía está diligenciando.
    v1 = Venta(
        asesor_id=asesor.id, estado="borrador", fecha_venta=hoy,
        sede="B", origen_venta="redes sociales", concepto="VENTA",
        destino="Cancún, México",
        descripcion_viaje="Paquete todo incluido - en cotización",
        valor_venta_real=3000000,
    )

    # 2) Pendiente caja — el asesor ya envió, caja aún no cobra.
    v2 = Venta(
        asesor_id=asesor.id, estado="pendiente_caja", fecha_venta=hoy,
        sede="A", origen_venta="whatsapp", concepto="VENTA",
        destino="Nueva York, Estados Unidos", descripcion_viaje="Viaje de compras",
        valor_venta_real=6500000, proveedor_tiquete="American Airlines",
        costo_tiquetes=4200000,
    )
    v2.pasajeros.append(_pasajero("Laura", "Jiménez", "43222111", telefono="3015556677", principal=True))

    # 3) Pendiente facturación — caja ya cobró, falta facturar.
    v3 = Venta(
        asesor_id=asesor.id, cajero_id=caja.id, estado="pendiente_facturacion",
        fecha_venta=hoy, sede="A", origen_venta="referido", concepto="VENTA",
        destino="Punta Cana, República Dominicana",
        descripcion_viaje="Luna de miel todo incluido",
        valor_venta_real=9800000, proveedor_tiquete="Copa Airlines", costo_tiquetes=3800000,
        proveedor_hotel="Iberostar", costo_hotel=2600000,
        valor_banco=6400000, valor_efectivo=3400000,
    )
    v3.pasajeros.append(_pasajero("Camila", "Rojas", "1013456789", telefono="3187778899", principal=True))
    v3.pasajeros.append(_pasajero("David", "Herrera", "1013456790"))

    # 4) Facturada — Cartagena, ciclo corto ya cerrado.
    v4 = Venta(
        asesor_id=asesor.id, cajero_id=caja.id, facturador_id=facturacion.id,
        estado="facturado", fecha_venta=hoy, sede="C", origen_venta="llamada",
        concepto="VENTA", destino="Cartagena, Colombia",
        descripcion_viaje="Fin de semana en pareja",
        valor_venta_real=4200000, proveedor_tiquete="Wingo", costo_tiquetes=1600000,
        proveedor_hotel="Decameron", costo_hotel=900000,
        valor_datafono=4200000, numero_factura="FE-CTG-2026",
        fecha_facturacion=datetime.utcnow(),
    )
    v4.pasajeros.append(_pasajero("Andrés", "Salazar", "71888999", telefono="3009998877", principal=True))
    v4.pasajeros.append(_pasajero("Natalia", "Salazar", "71889000"))

    # 5) Facturada — Familia García a España, el escenario completo de 4 pasajeros.
    v5 = Venta(
        asesor_id=asesor.id, cajero_id=caja.id, facturador_id=facturacion.id,
        estado="facturado", fecha_venta=hoy, sede="A", origen_venta="whatsapp",
        concepto="VENTA", destino="España", descripcion_viaje="Viaje familiar",
        valor_venta_real=12500000, proveedor_tiquete="Iberia", costo_tiquetes=8000000,
        proveedor_asistencia="Assist Card", costo_asistencia=400000,
        valor_banco=8400000, valor_efectivo=4100000,
        numero_factura="FE-GARCIA-001", fecha_facturacion=datetime.utcnow(),
    )
    v5.pasajeros.append(_pasajero("Pedro", "García", "79111222", telefono="3001112233", principal=True))
    v5.pasajeros.append(_pasajero("Marcela", "García", "52111222"))
    v5.pasajeros.append(_pasajero("Juliana", "García", "1010555666", tipo="TI"))
    v5.pasajeros.append(_pasajero("Samuel", "García", "1010555667", tipo="TI"))

    db.session.add_all([v1, v2, v3, v4, v5])
    db.session.commit()
