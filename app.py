import csv
import io
import os
import secrets
from datetime import date, datetime

from flask import (
    Flask,
    Response,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)

from destinos_data import DESTINOS_POPULARES
from models import (
    CONCEPTOS,
    ESTADOS,
    ExportConfig,
    Pasajero,
    Usuario,
    Venta,
    db,
    seed_defaults,
    seed_demo_ventas,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SEMILLA_DESTINOS = DESTINOS_POPULARES
SEMILLA_AEROLINEAS = [
    "Avianca", "LATAM", "Wingo", "Viva Air", "Copa Airlines",
    "American Airlines", "Iberia", "Air Europa", "JetBlue", "Delta",
]
SEMILLA_HOTELES = [
    "Decameron", "RIU", "Barceló", "Iberostar", "Sandals", "Hard Rock Hotel",
]
SEMILLA_SEGUROS = [
    "Assist Card", "Universal Assistance", "Assist 365", "Coris Assistance",
]
SEMILLA_SEDES = ["A", "B", "C"]
SEMILLA_ORIGENES = [
    "whatsapp", "referido", "redes sociales", "llamada", "sitio web",
    "valla publicitaria", "feria",
]

def _clave_secreta():
    clave = os.environ.get("SECRET_KEY")
    if clave:
        return clave

    # Desarrollo local únicamente: no hay SECRET_KEY en el entorno, así que
    # generamos una una sola vez y la guardamos fuera de git (ver
    # .gitignore). Nunca es un valor conocido/hardcodeado en el código.
    ruta_dev = os.path.join(BASE_DIR, ".secret_key.dev")
    if os.path.exists(ruta_dev):
        with open(ruta_dev, "r") as f:
            return f.read().strip()
    clave = secrets.token_hex(32)
    with open(ruta_dev, "w") as f:
        f.write(clave)
    return clave


app = Flask(__name__)
app.config["SECRET_KEY"] = _clave_secreta()
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(
    BASE_DIR, "agencia.db"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message = "Debes iniciar sesión para continuar."


@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))


def rol_requerido(*roles):
    def decorator(f):
        from functools import wraps

        @wraps(f)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for("login"))
            if current_user.rol != "admin" and current_user.rol not in roles:
                flash("No tienes permiso para entrar ahí.", "error")
                return redirect(url_for("ventas"))
            return f(*args, **kwargs)

        return wrapped

    return decorator


def _autorizado_para_ver(venta, user):
    """Regla de autorización en backend (no solo ocultar botones en HTML).

    - admin: todas.
    - asesor: solo las que creó (asesor_id).
    - caja: las que están en su bandeja de trabajo (pendiente_caja) o las
      que ya procesó ella misma (cajero_id).
    - facturacion: las que están en su bandeja (pendiente_facturacion) o
      las que ya facturó ella misma (facturador_id).
    """
    if user.rol == "admin":
        return True
    if user.rol == "asesor":
        return venta.asesor_id == user.id
    if user.rol == "caja":
        return venta.estado == "pendiente_caja" or venta.cajero_id == user.id
    if user.rol == "facturacion":
        return venta.estado == "pendiente_facturacion" or venta.facturador_id == user.id
    return False


def _autorizado_para_editar(venta, user):
    """Solo se puede corregir una venta mientras sigue en borrador, y solo
    quien la creó (o admin). Una vez pasa a pendiente_caja, el asesor ya no
    debe poder tocar la información financiera libremente."""
    if venta.estado != "borrador":
        return False
    return user.rol == "admin" or venta.asesor_id == user.id


def _filtro_visibilidad(query, user):
    """Mismo criterio que _autorizado_para_ver, aplicado a un listado."""
    if user.rol == "admin":
        return query
    if user.rol == "asesor":
        return query.filter(Venta.asesor_id == user.id)
    if user.rol == "caja":
        return query.filter(
            db.or_(Venta.estado == "pendiente_caja", Venta.cajero_id == user.id)
        )
    if user.rol == "facturacion":
        return query.filter(
            db.or_(
                Venta.estado == "pendiente_facturacion",
                Venta.facturador_id == user.id,
            )
        )
    return query.filter(db.false())


# --------------------------------------------------------------------------
# Autenticación
# --------------------------------------------------------------------------


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = Usuario.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for("ventas"))
        flash("Usuario o contraseña incorrectos.", "error")
    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


# --------------------------------------------------------------------------
# Listado y detalle de ventas (visible para todos los roles autenticados)
# --------------------------------------------------------------------------


@app.route("/")
@login_required
def ventas():
    query = _filtro_visibilidad(Venta.query, current_user)
    todas = query.order_by(Venta.fecha_creacion.desc()).all()

    hoy = date.today()
    stats = {
        "ventas_hoy": sum(1 for v in todas if v.fecha_venta == hoy),
        "pendientes_caja": sum(1 for v in todas if v.estado == "pendiente_caja"),
        "pendientes_facturacion": sum(
            1 for v in todas if v.estado == "pendiente_facturacion"
        ),
        "facturadas": sum(1 for v in todas if v.estado == "facturado"),
        "valor_vendido": sum(
            float(v.valor_venta_real or 0) for v in todas if v.estado == "facturado"
        ),
    }
    return render_template(
        "ventas.html", ventas=todas, estados=dict(ESTADOS), stats=stats
    )


@app.route("/venta/<int:venta_id>")
@login_required
def venta_detalle(venta_id):
    venta = Venta.query.get_or_404(venta_id)
    if not _autorizado_para_ver(venta, current_user):
        flash("No tienes permiso para ver esa venta.", "error")
        return redirect(url_for("ventas"))
    return render_template("venta_detalle.html", venta=venta, estados=dict(ESTADOS))


# --------------------------------------------------------------------------
# Asesor: diligencia la información por primera vez
# --------------------------------------------------------------------------


def _sugerencias(columna, semilla):
    existentes = [
        v[0]
        for v in db.session.query(columna).distinct().all()
        if v[0] and v[0].strip()
    ]
    return sorted(set(existentes) | set(semilla))


def _sugerencias_contexto():
    return dict(
        destinos=_sugerencias(Venta.destino, SEMILLA_DESTINOS),
        aerolineas=_sugerencias(Venta.proveedor_tiquete, SEMILLA_AEROLINEAS),
        hoteles=_sugerencias(Venta.proveedor_hotel, SEMILLA_HOTELES),
        seguros=_sugerencias(Venta.proveedor_asistencia, SEMILLA_SEGUROS),
        sedes=_sugerencias(Venta.sede, SEMILLA_SEDES),
        origenes=_sugerencias(Venta.origen_venta, SEMILLA_ORIGENES),
        conceptos=CONCEPTOS,
        hoy=date.today().isoformat(),
    )


def _en(lista, i):
    return lista[i].strip() if i < len(lista) else ""


def _a_decimal(valor):
    try:
        return float(str(valor).replace(",", "").strip() or 0)
    except ValueError:
        return 0


def _a_fecha(valor):
    if not valor:
        return None
    try:
        return datetime.strptime(valor, "%Y-%m-%d").date()
    except ValueError:
        return None


def _aplicar_campos_venta(venta, f):
    """Escribe en `venta` los campos del formulario. Se usa tanto para crear
    como para editar (mientras está en borrador) — un solo lugar que sabe
    leer el formulario."""
    venta.fecha_venta = _a_fecha(f.get("fecha_venta")) or date.today()
    venta.sede = f.get("sede", "").strip()
    venta.origen_venta = f.get("origen_venta", "").strip()
    venta.ciudad_cliente = f.get("ciudad_cliente", "").strip()
    venta.destino = f.get("destino", "").strip()
    venta.descripcion_viaje = f.get("descripcion_viaje", "").strip()
    venta.contacto_emergencia = f.get("contacto_emergencia", "").strip()
    venta.concepto = f.get("concepto", "VENTA")
    venta.valor_venta_real = _a_decimal(f.get("valor_venta_real"))
    venta.cuenta = f.get("cuenta", "").strip()
    venta.fecha_maxima_pago = _a_fecha(f.get("fecha_maxima_pago"))
    venta.fecha_venta_inicial_cartera = _a_fecha(f.get("fecha_venta_inicial_cartera"))
    venta.fecha_viaje = _a_fecha(f.get("fecha_viaje"))
    venta.proveedor_tiquete = f.get("proveedor_tiquete", "").strip()
    venta.costo_tiquetes = _a_decimal(f.get("costo_tiquetes"))
    venta.proveedor_conexion = f.get("proveedor_conexion", "").strip()
    venta.costo_conexion = _a_decimal(f.get("costo_conexion"))
    venta.proveedor_asistencia = f.get("proveedor_asistencia", "").strip()
    venta.costo_asistencia = _a_decimal(f.get("costo_asistencia"))
    venta.proveedor_hotel = f.get("proveedor_hotel", "").strip()
    venta.costo_hotel = _a_decimal(f.get("costo_hotel"))
    venta.amadeus = _a_decimal(f.get("amadeus"))
    venta.fi_bancario = _a_decimal(f.get("fi_bancario"))
    venta.descripcion_obsequio = f.get("descripcion_obsequio", "").strip()
    venta.costo_obsequio = _a_decimal(f.get("costo_obsequio"))
    venta.descripcion_receptivos = f.get("descripcion_receptivos", "").strip()
    venta.costo_receptivos = _a_decimal(f.get("costo_receptivos"))
    venta.tiene_contrato = bool(f.get("tiene_contrato"))
    venta.observaciones = f.get("observaciones", "").strip()


def _procesar_pasajeros(f):
    """Arma la lista de Pasajero desde el formulario. El primero con datos
    queda marcado como titular/comprador — no existe un campo de cliente
    aparte."""
    nombres = f.getlist("pasajero_nombres")
    apellidos = f.getlist("pasajero_apellidos")
    tipos_doc = f.getlist("pasajero_tipo_documento")
    numeros_doc = f.getlist("pasajero_numero_documento")
    fechas_nac = f.getlist("pasajero_fecha_nacimiento")
    telefonos = f.getlist("pasajero_telefono")
    emails = f.getlist("pasajero_email")

    creados = []
    for i, nombre in enumerate(nombres):
        if not nombre.strip():
            continue
        creados.append(
            Pasajero(
                nombres=nombre.strip(),
                apellidos=_en(apellidos, i),
                tipo_documento=_en(tipos_doc, i),
                numero_documento=_en(numeros_doc, i),
                fecha_nacimiento=_en(fechas_nac, i),
                telefono=_en(telefonos, i),
                email=_en(emails, i),
            )
        )
    if creados:
        creados[0].es_principal = True
    return creados


def _pasajeros_a_json(lista_pasajeros):
    return [
        {
            "nombres": p.nombres,
            "apellidos": p.apellidos,
            "tipo_documento": p.tipo_documento,
            "numero_documento": p.numero_documento,
            "fecha_nacimiento": p.fecha_nacimiento,
            "telefono": p.telefono,
            "email": p.email,
        }
        for p in lista_pasajeros
    ]


def _pasajeros_json(venta):
    """Para precargar la fila de cada pasajero en el formulario de edición."""
    if not venta:
        return []
    return _pasajeros_a_json(venta.pasajeros)


@app.route("/venta/nueva", methods=["GET", "POST"])
@login_required
@rol_requerido("asesor")
def venta_nueva():
    if request.method == "POST":
        f = request.form
        accion = f.get("accion", "enviar")  # "borrador" o "enviar"

        venta = Venta(asesor_id=current_user.id, estado="borrador")
        _aplicar_campos_venta(venta, f)
        pasajeros_creados = _procesar_pasajeros(f)

        if accion == "enviar":
            if not pasajeros_creados or not pasajeros_creados[0].numero_documento:
                flash(
                    "Debes indicar al menos el pasajero titular (nombre y documento) "
                    "— es el comprador de la venta.",
                    "error",
                )
                return render_template(
                    "nueva_venta.html",
                    venta=None,
                    pasajeros_json=[],
                    **_sugerencias_contexto()
                )
            venta.estado = "pendiente_caja"

        venta.pasajeros.extend(pasajeros_creados)
        db.session.add(venta)
        db.session.commit()

        if accion == "enviar":
            flash("Viaje enviado a caja. Ya lo puede ver en vivo.", "ok")
        else:
            flash("Borrador guardado. Puedes seguir editándolo antes de enviarlo a caja.", "ok")
        return redirect(url_for("venta_detalle", venta_id=venta.id))

    return render_template(
        "nueva_venta.html", venta=None, pasajeros_json=[], **_sugerencias_contexto()
    )


@app.route("/venta/<int:venta_id>/editar", methods=["GET", "POST"])
@login_required
@rol_requerido("asesor")
def venta_editar(venta_id):
    venta = Venta.query.get_or_404(venta_id)
    if not _autorizado_para_editar(venta, current_user):
        flash(
            "Esta venta ya no está en borrador (o no es tuya): ya no se puede editar "
            "— la información financiera queda fija una vez pasa a caja.",
            "error",
        )
        return redirect(url_for("venta_detalle", venta_id=venta.id))

    if request.method == "POST":
        f = request.form
        accion = f.get("accion", "borrador")

        _aplicar_campos_venta(venta, f)
        pasajeros_creados = _procesar_pasajeros(f)

        if accion == "enviar" and (
            not pasajeros_creados or not pasajeros_creados[0].numero_documento
        ):
            flash(
                "Debes indicar al menos el pasajero titular (nombre y documento) "
                "— es el comprador de la venta.",
                "error",
            )
            return render_template(
                "nueva_venta.html",
                venta=venta,
                pasajeros_json=_pasajeros_a_json(pasajeros_creados),
                **_sugerencias_contexto()
            )

        venta.pasajeros.clear()
        venta.pasajeros.extend(pasajeros_creados)

        if accion == "enviar":
            venta.estado = "pendiente_caja"

        db.session.commit()
        flash(
            "Viaje enviado a caja. Ya lo puede ver en vivo." if accion == "enviar"
            else "Borrador actualizado.",
            "ok",
        )
        return redirect(url_for("venta_detalle", venta_id=venta.id))

    return render_template(
        "nueva_venta.html",
        venta=venta,
        pasajeros_json=_pasajeros_json(venta),
        **_sugerencias_contexto()
    )


# --------------------------------------------------------------------------
# Caja: confirma pagos y totales
# --------------------------------------------------------------------------


@app.route("/venta/<int:venta_id>/caja", methods=["POST"])
@login_required
@rol_requerido("caja")
def venta_caja(venta_id):
    venta = Venta.query.get_or_404(venta_id)

    if not _autorizado_para_ver(venta, current_user):
        flash("No tienes permiso sobre esa venta.", "error")
        return redirect(url_for("ventas"))

    if venta.estado == "facturado":
        flash("Esta venta ya está facturada y quedó cerrada: no se puede modificar el pago.", "error")
        return redirect(url_for("venta_detalle", venta_id=venta.id))

    f = request.form

    venta.valor_datafono = _a_decimal(f.get("valor_datafono"))
    venta.valor_banco = _a_decimal(f.get("valor_banco"))
    venta.ultimos4_cuenta = f.get("ultimos4_cuenta", "").strip()
    venta.valor_efectivo = _a_decimal(f.get("valor_efectivo"))
    if f.get("cuenta"):
        venta.cuenta = f.get("cuenta", "").strip()

    venta.cajero_id = current_user.id
    venta.estado = "pendiente_facturacion"
    db.session.commit()
    flash("Pago registrado. Facturación ya puede verlo.", "ok")
    return redirect(url_for("venta_detalle", venta_id=venta.id))


# --------------------------------------------------------------------------
# Facturación electrónica
# --------------------------------------------------------------------------


@app.route("/venta/<int:venta_id>/facturar", methods=["POST"])
@login_required
@rol_requerido("facturacion")
def venta_facturar(venta_id):
    venta = Venta.query.get_or_404(venta_id)

    if not _autorizado_para_ver(venta, current_user):
        flash("No tienes permiso sobre esa venta.", "error")
        return redirect(url_for("ventas"))

    if venta.estado == "facturado":
        flash("Esta venta ya está facturada y quedó cerrada: no se puede volver a facturar.", "error")
        return redirect(url_for("venta_detalle", venta_id=venta.id))

    numero_factura = request.form.get("numero_factura", "").strip()
    if not numero_factura:
        flash("Ingresa el número de factura.", "error")
        return redirect(url_for("venta_detalle", venta_id=venta.id))

    venta.numero_factura = numero_factura
    venta.facturador_id = current_user.id
    venta.fecha_facturacion = datetime.utcnow()
    venta.estado = "facturado"
    db.session.commit()
    flash("Venta facturada.", "ok")
    return redirect(url_for("venta_detalle", venta_id=venta.id))


# --------------------------------------------------------------------------
# Configuración de exportables (qué campos van a contador y a tributario)
# — solo admin. Ambos leen del mismo catálogo CAMPOS_EXPORTABLES / misma
# Venta+Pasajeros: esto NO crea un segundo lugar de captura.
# --------------------------------------------------------------------------


@app.route("/configuracion/exportables", methods=["GET", "POST"])
@login_required
@rol_requerido("admin")
def configuracion_exportables():
    if request.method == "POST":
        seleccion_contador = set(request.form.getlist("campo_contador"))
        seleccion_dian = set(request.form.getlist("campo_dian"))
        for cfg in ExportConfig.query.all():
            cfg.incluir_contador = cfg.campo in seleccion_contador
            cfg.incluir_dian = cfg.campo in seleccion_dian
        db.session.commit()
        flash("Configuración de exportables actualizada.", "ok")
        return redirect(url_for("configuracion_exportables"))

    campos = ExportConfig.query.all()
    return render_template("config_dian.html", campos=campos)


# --------------------------------------------------------------------------
# Exportaciones: contador (todo, como el Excel actual) y DIAN (configurable)
# --------------------------------------------------------------------------


def _moneda(valor):
    return round(float(valor or 0), 2)


def _fila_venta(venta):
    proveedores = ", ".join(
        p
        for p in (
            venta.proveedor_tiquete,
            venta.proveedor_conexion,
            venta.proveedor_asistencia,
            venta.proveedor_hotel,
        )
        if p
    )
    forma_pago = ", ".join(
        f"{etiqueta}: {_moneda(valor)}"
        for etiqueta, valor in (
            ("datafono", venta.valor_datafono),
            ("banco", venta.valor_banco),
            ("efectivo", venta.valor_efectivo),
        )
        if valor
    )
    return {
        "fecha_venta": venta.fecha_venta.strftime("%Y-%m-%d") if venta.fecha_venta else "",
        "numero_factura": venta.numero_factura or "",
        "titular_documento": venta.titular_documento or "",
        "titular_nombre": venta.titular_nombre or "",
        "ciudad_cliente": venta.ciudad_cliente or "",
        "destino": venta.destino or "",
        "concepto": venta.concepto or "",
        "valor_venta_real": _moneda(venta.valor_venta_real),
        "total_costos": _moneda(venta.total_costos),
        "ta_antes_iva": _moneda(venta.ta_antes_iva),
        "iva_ta": _moneda(venta.iva_ta),
        "ta_despues_iva": _moneda(venta.ta_despues_iva),
        "estado": venta.estado_label,
        "asesor": venta.asesor.nombre if venta.asesor else "",
        "sede": venta.sede or "",
        "origen_venta": venta.origen_venta or "",
        "pax": venta.pax or 0,
        "proveedores": proveedores,
        "forma_pago": forma_pago,
        "saldo_pendiente": _moneda(venta.saldo_pendiente),
        "cartera_por_cobrar": _moneda(venta.cartera_por_cobrar),
    }


def _csv_response(filename, headers, rows):
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(headers)
    writer.writerows(rows)
    return Response(
        buffer.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.route("/exportar/contador")
@login_required
@rol_requerido("admin", "facturacion", "caja")
def exportar_contador():
    ventas_list = Venta.query.order_by(Venta.fecha_creacion).all()
    activos = ExportConfig.query.filter_by(incluir_contador=True).all()
    campos = [c.campo for c in activos]
    etiquetas = {c.campo: c.etiqueta for c in activos}

    headers = [etiquetas[c] for c in campos]
    rows = []
    for venta in ventas_list:
        fila = _fila_venta(venta)
        rows.append([fila[c] for c in campos])

    return _csv_response("archivo_contador.csv", headers, rows)


@app.route("/exportar/dian")
@login_required
@rol_requerido("admin", "facturacion")
def exportar_dian():
    ventas_list = Venta.query.filter(Venta.estado == "facturado").order_by(
        Venta.fecha_creacion
    ).all()
    activos = ExportConfig.query.filter_by(incluir_dian=True).all()
    campos = [c.campo for c in activos]
    etiquetas = {c.campo: c.etiqueta for c in activos}

    headers = [etiquetas[c] for c in campos]
    rows = []
    for venta in ventas_list:
        fila = _fila_venta(venta)
        rows.append([fila[c] for c in campos])

    return _csv_response("archivo_dian.csv", headers, rows)


# --------------------------------------------------------------------------

with app.app_context():
    db.create_all()
    seed_defaults()
    if os.environ.get("SEED_DEMO", "1") == "1":
        seed_demo_ventas()


if __name__ == "__main__":
    puerto = int(os.environ.get("PORT", 5050))
    modo_debug = os.environ.get("FLASK_DEBUG", "1" if puerto == 5050 else "0") == "1"
    app.run(host="0.0.0.0", port=puerto, debug=modo_debug)
