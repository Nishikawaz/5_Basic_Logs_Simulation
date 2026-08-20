# API de ingesta de logs

API REST que centraliza logs de múltiples servicios: recibe eventos por lotes con autenticación por token, los persiste en SQLite y los expone con filtrado por rango temporal y severidad. Incluye un simulador que genera tráfico de tres servicios.

**Stack:** Python 3 · Flask · SQLite · Requests

---

## Cómo correrlo

```bash
pip install flask requests

# Terminal 1 — la API
python server.py

# Terminal 2 — el simulador (envía 999 logs)
python cliente.py
```

La API queda en `http://localhost:6869`. La base `logs.db` se crea sola al arrancar.

---

## La API

### `POST /logs` — ingesta

Acepta un objeto único o un array de objetos. El servidor normaliza el caso individual a lista, así que ambos formatos funcionan igual.

```bash
curl -X POST http://localhost:6869/logs \
  -H "Authorization: Token TOKEN_servicio_A" \
  -H "Content-Type: application/json" \
  -d '[{"timestamp":"2026-08-20T14:30:00","service":"Registro","severity":"ERROR","message":"Fallo al enviar correo"}]'
```

| Código | Situación |
|---|---|
| `201` | Logs guardados |
| `400` | Cuerpo no-JSON, vacío, con un elemento que no es objeto, o a un log le falta algún campo requerido |
| `401` | Token ausente o desconocido |
| `403` | Token de solo lectura intentando escribir, o un servicio escribiendo logs a nombre de otro |

Los cuatro campos —`timestamp`, `service`, `severity`, `message`— son obligatorios. El lote se valida **entero antes de escribir nada**: si un log falla, no se inserta ninguno.

### `GET /logs` — consulta

Tres parámetros de query, todos opcionales y combinables:

| Parámetro | Efecto |
|---|---|
| `timestamp_start` | Desde (inclusive) |
| `timestamp_end` | Hasta (inclusive) |
| `severity` | Filtra por nivel — se normaliza a mayúsculas |

```bash
curl -H "Authorization: Token Consultas" \
  "http://localhost:6869/logs?severity=error&timestamp_start=2026-08-20T00:00:00"
```

Devuelve un array JSON ordenado por `id` descendente (lo más reciente primero).

### Autenticación

Header `Authorization: Token <valor>`. Hay cuatro tokens, y cada uno tiene un alcance distinto:

| Token | Puede escribir | Puede leer |
|---|---|---|
| `TOKEN_servicio_A` | solo logs con `service: "Registro"` | sí |
| `TOKEN_servicio_B` | solo logs con `service: "Autenticacion"` | sí |
| `TOKEN_servicio_C` | solo logs con `service: "Pagos"` | sí |
| `Consultas` | **no** — es de solo lectura | sí |

El token no solo autentica: queda **atado** al servicio que tiene permitido escribir. Un servicio no puede publicar logs a nombre de otro, y el token de consulta no puede escribir en absoluto.

---

## El simulador

`cliente.py` genera tráfico realista de tres servicios —Registro, Autenticación y Pagos— con 333 logs cada uno. Cada servicio tiene su propio catálogo de mensajes plausibles y su propio token; la severidad se sortea entre `INFO`, `WARNING`, `ERROR`, `DEBUG` y `CRITICAL`.

Los 999 logs se envían en **tres peticiones**, una por servicio, no en 999 pedidos sueltos.

---

## Estructura

```
server.py      API Flask: dos endpoints, auth por token, esquema SQLite
cliente.py     Simulador de tres servicios emisores
```

`logs.db` está en `.gitignore` — se genera al correr.

---

## Decisiones de diseño

**Ingesta por lotes.** El endpoint acepta un array completo en una sola petición. Enviar 333 logs de a uno serían 333 handshakes TCP y 333 transacciones SQLite; en batch es un pedido y un `commit`. Es la diferencia entre un simulador que tarda segundos y uno que tarda minutos.

**Doble timestamp: `timestamp` y `received_at`.** El primero lo declara el servicio emisor (cuándo ocurrió el evento); el segundo lo pone el servidor al recibirlo. Separarlos permite detectar desfasajes de reloj entre servicios y demoras de ingesta — si `received_at` se aleja consistentemente de `timestamp`, hay un problema de red o de encolamiento. Un solo campo escondería esa información.

**Query dinámica con `WHERE 1=1`.** Los filtros son opcionales y combinables, así que la cláusula se arma concatenando condiciones. El `1=1` inicial —siempre verdadero, sin costo real— hace que cada filtro se agregue con `AND` sin tener que preguntar si es el primero. Evita una cadena de condicionales para decidir cuándo poner `WHERE` y cuándo `AND`.

**Consultas parametrizadas, siempre.** Los valores nunca se interpolan en el string: van como placeholders `?` con sus valores en una tupla aparte. Es lo que cierra la puerta a la inyección SQL. La query se concatena, los **valores** no.

**`sqlite3.Row` como row factory.** Permite acceder por nombre de columna (`row['severity']`) en vez de por índice numérico (`row[3]`). Un cambio en el orden de columnas del `SELECT` no rompe nada, y el código de serialización a JSON es una línea.

**El esquema no restringe la severidad.** `severity` es `TEXT` libre, no un dominio cerrado. Es a propósito: un agregador de logs que rechaza un evento por un nivel desconocido pierde justo la información que podría importar. La normalización se hace en la lectura (`.upper()` en el filtro), no en la escritura.

**El token está atado a un servicio, no solo a "es válido".** Validar que un token exista alcanza para saber que quien llama es alguien conocido, pero no para saber que es *quien dice ser*. Con solo esa validación, el token de Pagos podía escribir logs firmados como Autenticación — y un log de auditoría en el que cualquiera puede escribir a nombre de otro no sirve como evidencia de nada. El diccionario mapea cada token al nombre de servicio que habilita, y el `POST` compara ese nombre contra el campo `service` de cada log.

**El lote se valida completo antes de escribir.** La verificación de campos y de permisos recorre todos los logs primero y recién después abre la conexión a la base. Validar sobre la marcha dejaría media tanda insertada y la otra media rechazada ante el primer log defectuoso, y el cliente no tendría forma de saber cuántos entraron.

**`debug` sale de una variable de entorno.** Con `debug=True` fijo, el servidor de desarrollo de Flask expone una consola interactiva que ejecuta código arbitrario en el proceso. Queda apagado salvo que se pida explícitamente con `FLASK_DEBUG=1`.

---

## Contexto

Challenge de APIs REST y persistencia. La consigna pedía un servicio que recibiera logs de múltiples fuentes con autenticación, los almacenara y permitiera consultarlos con filtros.

Este proyecto genera los datos que analiza el challenge siguiente ([6_Basic_Logs_Analysis](https://github.com/Nishikawaz/6_Basic_Logs_Analysis)): acá se produce y se ingesta, allá se detecta el incidente.

---
