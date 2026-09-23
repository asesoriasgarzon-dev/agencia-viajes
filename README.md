# Agencia de Viajes — captura única + tiempo real

Prototipo para eliminar el reproceso: el asesor diligencia la información
**una sola vez**, y caja y facturación electrónica la ven en vivo desde su
propia pantalla (se refresca sola cada 5-6 segundos), en vez de volver a
escribir todo en papel.

Del mismo dato capturado salen dos archivos:

- **Archivo del contador**: todos los campos, sin filtrar.
- **Archivo DIAN**: solo los campos que la agencia decida incluir
  (se configura en "Config. DIAN", solo lo ve el usuario admin).

## Cómo correrlo

```bash
pip install -r requirements.txt
python app.py
```

Abre http://localhost:5050

La primera vez que corre crea automáticamente 4 usuarios de prueba
(usuario / contraseña):

- `admin` / `admin123` — ve todo, configura qué va a la DIAN
- `asesor1` / `asesor123` — diligencia cotizaciones nuevas
- `caja1` / `caja123` — confirma pagos y totales
- `facturacion1` / `factura123` — genera el número de factura

Cambia esas contraseñas antes de usarlo con datos reales (ver
`models.py`, función `seed_defaults`).

## Flujo

1. El **asesor** llena destino, costo real, precio de venta, vuelo,
   seguro hotelero y los datos de cada pasajero (una sola vez).
2. La venta pasa a **caja**, que ve todo en vivo, registra cómo pagó el
   cliente (Nequi, efectivo, débito, crédito) y confirma el total.
3. La venta pasa a **facturación electrónica**, que ve todo (incluyendo
   los pagos) y solo debe poner el número de factura.
4. Desde el menú, admin/facturación/caja pueden exportar el **archivo
   del contador** (CSV, todos los campos) y admin/facturación pueden
   exportar el **archivo DIAN** (CSV, solo lo facturado y solo los
   campos marcados en Config. DIAN).

## Pendiente si esto pasa a producción

- Los datos de cada pasajero se escriben a mano en el formulario; no hay
  integración con la Registraduría porque no existe una API pública
  gratuita para eso en Colombia — requeriría contratar un proveedor de
  validación de identidad autorizado.
- Cambiar las contraseñas de ejemplo y mover `SECRET_KEY` a una variable
  de entorno real antes de exponerlo fuera de la máquina local.
- El "tiempo real" hoy es con recarga automática cada 5-6s (simple y
  robusto). Si hace falta que sea instantáneo, se puede subir a
  WebSockets (Flask-SocketIO) más adelante sin rehacer el modelo de
  datos.
