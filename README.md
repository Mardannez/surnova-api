# SURNOVA-API

Repositorio: [Mardannez/surnova-api](https://github.com/Mardannez/surnova-api).

API REST compartida por **SURNOVA Web** y **SURNOVAAPP (React Native / Expo)**. Django Admin es el panel administrativo inicial. Todos los clientes utilizan los mismos endpoints y reglas de negocio.

Incluye usuario personalizado por email, JWT, catálogo, inventario con auditoría, carrito autenticado o anónimo, checkout transaccional, pedidos históricos, OpenAPI y pruebas sobre PostgreSQL. No incluye pagos reales, transportistas, cupones complejos, facturación fiscal ni un frontend administrativo separado.

## Arquitectura

```text
config/                  settings base/local/production/test, URLs, ASGI y WSGI
apps/users/              usuario UUID, registro, login, perfil y logout
apps/catalog/            categorías, marcas, productos, variantes e imágenes
apps/inventory/          existencias, movimientos y servicio transaccional
apps/carts/              carritos, artículos y servicio de cantidades
apps/orders/             pedidos, direcciones, snapshots y servicios de checkout/estados
common/                  modelos base, permisos, paginación, validadores, errores y esquema
tests/                   fixtures, API, Admin, reglas de dominio y concurrencia
requirements/            dependencias directas y restricciones transitivas
scripts/setup_local.py   generación de .env local con secretos aleatorios
docker-compose.yml       PostgreSQL local con volumen persistente
```

Las views reciben solicitudes; los serializers validan y representan datos; los servicios realizan las operaciones de negocio. Las restricciones de base de datos refuerzan unicidad, cantidades y consistencia monetaria. No hay lógica específica del cliente web o móvil.

## Requisitos y versiones

Python **3.12 o 3.13**, Docker Desktop con motor Linux y PowerShell. La implementación se verifica con Python **3.12.14**.

| Componente | Versión fijada |
| --- | --- |
| Django | 5.2.18 LTS |
| Django REST Framework | 3.18.3 |
| Simple JWT | 5.5.1 |
| Psycopg / psycopg-binary | 3.3.6 |
| PostgreSQL | 17.11, imagen bookworm |
| drf-spectacular | 0.30.0 |
| Pillow | 13.0.0 |
| pytest / pytest-django | 8.4.2 / 4.11.1 |
| Ruff | 0.14.3 |
| Django Unfold | 0.110.0 |

Se eligió [Django 5.2 LTS](https://www.djangoproject.com/download/) por su soporte extendido. [Simple JWT 5.5.1](https://pypi.org/project/djangorestframework-simplejwt/5.5.1/) declara compatibilidad con Django 5.2 y Python 3.12/3.13. Las dependencias directas están fijadas en `requirements/base.txt` y `dev.txt`; `constraints.txt` fija también las transitivas. PostgreSQL permanece en la rama 17 con su [parche estable](https://www.postgresql.org/support/versioning/).

## Instalación en Windows PowerShell

Todos los comandos se ejecutan dentro de este proyecto. No se necesitan cambios en carpetas vecinas.

```powershell
Set-Location C:\surnova-api
py -3.12 --version
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements\dev.txt
```

Si PowerShell bloquea la activación, habilítala solo en esa terminal con `Set-ExecutionPolicy -Scope Process Bypass` o utiliza directamente `.\.venv\Scripts\python.exe` en lugar de `python`. Si los alias `py`/`python` de Microsoft Store no funcionan, instala Python 3.12/3.13 o sustituye `py -3.12` por la ruta completa a un intérprete instalado. El entorno virtual de esta carpeta ya fue preparado durante la construcción.

### Entorno y PostgreSQL

```powershell
python scripts\setup_local.py
docker desktop start
docker compose up -d --wait db
python manage.py migrate
python manage.py createsuperuser
python manage.py seed_demo
python manage.py changepassword cliente@example.test
python manage.py runserver 127.0.0.1:8000
```

`setup_local.py` copia `.env.example`, genera `DJANGO_SECRET_KEY` y una contraseña aleatoria de PostgreSQL coherente con `DATABASE_URL`, y nunca sobreescribe un `.env` existente ni imprime sus valores. El `.env` local está ignorado por Git. El puerto PostgreSQL es **54329** para reducir conflictos con otras instalaciones; solo se publica en `127.0.0.1`. La API utiliza `config.settings.local` por defecto.

También puedes copiar `.env.example` manualmente y completar sus valores. `DJANGO_SECRET_KEY` y `DATABASE_URL` son obligatorios. No uses `CHANGE_ME` como contraseña. `DJANGO_ALLOWED_HOSTS` y `CORS_ALLOWED_ORIGINS` son listas separadas por comas; CORS lleva orígenes completos, sin barra final.

Para detener y liberar recursos sin borrar datos:

```powershell
# Detener runserver: Ctrl+C en su terminal.
docker compose stop db
# Reanudar:
docker compose up -d --wait db
```

No utilices `docker compose down -v` si quieres conservar los datos. Cambiar `POSTGRES_PASSWORD` en `.env` no cambia la contraseña de una base ya inicializada: actualízala también en PostgreSQL y en `DATABASE_URL`.

### Direcciones locales

| Recurso | Dirección |
| --- | --- |
| Django Admin | http://127.0.0.1:8000/admin/ |
| Swagger | http://127.0.0.1:8000/api/docs/ |
| ReDoc | http://127.0.0.1:8000/api/redoc/ |
| OpenAPI | http://127.0.0.1:8000/api/schema/ |
| Productos | http://127.0.0.1:8000/api/v1/products/ |

Swagger y ReDoc requieren acceso a sus recursos CDN. Para autorizar Swagger, usa **Authorize** e introduce solo el access token en el esquema Bearer.

## Datos de demostración

`seed_demo` crea de forma idempotente:

- Categorías `ropa` y `accesorios`, marca `surnova`.
- Camiseta SURNOVA: `SN-CAM-M` a **350.00 HNL** y `SN-CAM-L` a **375.00 HNL**.
- Mochila SURNOVA: `SN-MOC-NEG` a **890.00 HNL**.
- 25 unidades iniciales por variante y movimientos de entrada auditables.
- Cliente `cliente@example.test`, sin privilegios administrativos.

No hay contraseña predeterminada ni superusuario demo. Configura la contraseña del cliente con `changepassword`, o establece `DEMO_CUSTOMER_PASSWORD` antes de crear el cliente por primera vez. Las ejecuciones posteriores preservan stock, precios, contraseñas y cambios administrativos. No se descargan imágenes; no había recursos locales apropiados. Puedes subirlas desde Admin. El comando se rechaza en settings de producción.

## Autenticación

```powershell
$base = 'http://127.0.0.1:8000/api/v1'
$password = [System.Net.NetworkCredential]::new('', (Read-Host 'Contraseña del cliente' -AsSecureString)).Password
$registro = @{
    email = 'comprador@example.test'
    password = $password
    first_name = 'Ana'
    last_name = 'López'
} | ConvertTo-Json
Invoke-RestMethod "$base/auth/register/" -Method Post -ContentType 'application/json' -Body $registro

$login = @{email = 'comprador@example.test'; password = $password} | ConvertTo-Json
$tokens = Invoke-RestMethod "$base/auth/login/" -Method Post -ContentType 'application/json' -Body $login
$headers = @{Authorization = "Bearer $($tokens.access)"}
Invoke-RestMethod "$base/auth/me/" -Headers $headers
Invoke-RestMethod "$base/auth/me/" -Method Patch -Headers $headers -ContentType 'application/json' -Body '{"phone":"+50499990000"}'
```

La contraseña se lee sin mostrarla y se convierte solo en memoria para la solicitud. No guardes tokens ni contraseñas en scripts o registros.

Respuesta de login (valores ilustrativos):

```json
{"access": "<JWT access>", "refresh": "<JWT refresh>"}
```

Access dura 5 minutos y refresh 7 días por defecto, configurables mediante entorno. Refresh rota en cada uso; guarda el nuevo refresh y descarta el anterior. Las rotaciones invalidan el refresh anterior mediante blacklist.

```powershell
$refreshBody = @{refresh = $tokens.refresh} | ConvertTo-Json
$tokens = Invoke-RestMethod "$base/auth/refresh/" -Method Post -ContentType 'application/json' -Body $refreshBody
$headers.Authorization = "Bearer $($tokens.access)"

# Cerrar sesión cuando termines el flujo de compra:
$logoutBody = @{refresh = $tokens.refresh} | ConvertTo-Json
Invoke-RestMethod "$base/auth/logout/" -Method Post -Headers $headers -ContentType 'application/json' -Body $logoutBody
```

Logout requiere access válido y un refresh propio. Revoca ese refresh; el access ya emitido sigue válido hasta su vencimiento. Ejecuta periódicamente `python manage.py flushexpiredtokens` para limpiar tokens vencidos. Email se normaliza a minúsculas y no puede cambiarse desde `/me/`. Los endpoints de perfil nunca permiten cambiar permisos.

## Flujo carrito → checkout → pedido

Ejecuta este ejemplo después del login, antes del logout. El servidor ignora importes enviados por clientes y vuelve a consultar el precio durante checkout.

```powershell
$catalogo = Invoke-RestMethod "$base/products/?search=SN-CAM-M"
$variant = $catalogo.results[0].variants | Where-Object sku -eq 'SN-CAM-M'
$itemBody = @{variant = $variant.id; quantity = 2} | ConvertTo-Json
$cart = Invoke-RestMethod "$base/cart/items/" -Method Post -Headers $headers -ContentType 'application/json' -Body $itemBody
$cart
# Repetir la misma variante suma cantidades, no crea otra línea.
$cart = Invoke-RestMethod "$base/cart/" -Headers $headers

$checkoutBody = @{
    addresses = @(@{
        address_type = 'SHIPPING'
        full_name = 'Ana López'
        phone = '+50499990000'
        address_line_1 = 'Colonia Centro, casa 10'
        address_line_2 = ''
        city = 'Tegucigalpa'
        state = 'Francisco Morazán'
        postal_code = ''
        country = 'HN'
    })
    notes = 'Llamar al llegar'
} | ConvertTo-Json -Depth 5
$checkoutHeaders = @{
    Authorization = $headers.Authorization
    'Idempotency-Key' = [guid]::NewGuid().ToString()
}
$order = Invoke-RestMethod "$base/checkout/" -Method Post -Headers $checkoutHeaders -ContentType 'application/json' -Body $checkoutBody
Invoke-RestMethod "$base/orders/$($order.id)/" -Headers $headers
Invoke-RestMethod "$base/orders/" -Headers $headers

# Ante un fallo de red, reintenta con EL MISMO cuerpo y la MISMA clave.
$sameOrder = Invoke-RestMethod "$base/checkout/" -Method Post -Headers $checkoutHeaders -ContentType 'application/json' -Body $checkoutBody
```

La primera respuesta es **201**. El reintento devuelve **200**, el mismo pedido y sus snapshots, aunque el precio actual cambie. Reutilizar la clave con otros datos devuelve **409**. Usa una clave nueva para cada compra distinta y conserva la clave durante reintentos. Las claves son únicas por usuario y se conservan con el pedido. La operación serializa los checkouts de un mismo usuario y bloquea variantes en orden determinista, dentro de `transaction.atomic()`.

Checkout exige al menos un artículo, JWT y una dirección `SHIPPING`; permite otra `BILLING`. Reconsulta precios, comprueba actividad del producto y existencias, reserva unidades, guarda nombres/SKU/precios históricos, crea historial y vacía/cierra el carrito. Cualquier fallo revierte toda la operación, incluidas reservas previas de otras líneas.

Los importes de la API son cadenas decimales, por ejemplo `"350.00"`. Moneda de esta versión: **HNL**. Subtotal y total del ejemplo son `"700.00"`; descuentos, impuestos y envío permanecen en cero hasta definir sus reglas. No se calcula facturación fiscal.

### Carrito anónimo y límites

`GET /cart/` sin JWT genera un carrito y devuelve un token opaco firmado en el header **X-Cart-Token**. Guárdalo y reenvíalo en las operaciones posteriores. El token permite acceder a ese carrito: trátalo como una credencial. No se usan cookies para autorizar carritos anónimos. Sin token se crea otro carrito vacío. El token vence a los 30 días; no hay limpieza automática de carritos en esta versión.

Para adoptar el carrito, envía simultáneamente JWT y `X-Cart-Token` a `/cart/` o a checkout. Se asigna al usuario y se revoca inmediatamente el acceso anónimo. Si el usuario ya tiene un carrito con artículos, se devuelve 409: vacíalo antes de adoptar el anónimo. No hay fusión silenciosa de cantidades.

Cada cantidad debe ser un **entero JSON entre 1 y 100**, con hasta 100 variantes por carrito. El carrito no reserva existencias; la disponibilidad definitiva se verifica en checkout.

| Operación | Endpoint |
| --- | --- |
| Consultar carrito | `GET /api/v1/cart/` |
| Sumar variante | `POST /api/v1/cart/items/` con `variant`, `quantity` |
| Reemplazar cantidad | `PATCH /api/v1/cart/items/{id}/` con `quantity` |
| Quitar línea | `DELETE /api/v1/cart/items/{id}/` |
| Vaciar | `DELETE /api/v1/cart/clear/` |

## Catálogo público

Categorías: `GET /api/v1/categories/` y `GET /api/v1/categories/{slug}/`. Marcas: `GET /api/v1/brands/`. Productos: `GET /api/v1/products/` y `GET /api/v1/products/{slug}/`. Todos son de solo lectura, incluso para staff; las ediciones se realizan desde Admin.

| Parámetro de productos | Ejemplo / comportamiento |
| --- | --- |
| `search` | Nombre, descripciones y SKU de variantes activas |
| `category` | Slug: `ropa` |
| `brand` | Slug: `surnova` |
| `min_price`, `max_price` | Límites del precio mínimo de las variantes activas del producto |
| `featured` | `true` o `false` |
| `ordering` | `price`, `-price`, `name`, `-name`, `created_at`, `-created_at` |
| `page`, `page_size` | 20 por defecto; máximo 100 por página |

Solo se muestran productos activos en categorías activas, con marca activa si tienen marca y al menos una variante activa. Las variantes e imágenes de variantes inactivas se excluyen. Se utilizan agregaciones, `select_related` y `prefetch_related` para reducir consultas. Listados paginados devuelven `count`, `next`, `previous`, `results`.

## Inventario y administración

El panel utiliza Django Unfold con la identidad SURNOVA: primario `#1A1A2E`, secundario `#16213E`, acento `#E8FF47`, fondo `#F8F8F6` y Plus Jakarta Sans servida localmente con su licencia OFL. La navegación es oscura y el área de trabajo clara. Configura navegación y paleta en `config/admin_theme.py`; los estilos están en `static/surnova/admin.css` y las plantillas en `templates/`.

El inicio muestra métricas reales y actividad administrativa, respetando los permisos del operador. El listado de productos incluye miniatura, precio mínimo, existencias y alertas de stock. El detalle de pedidos presenta cliente, dirección histórica, líneas, totales y seguimiento; conserva el historial y los importes de solo lectura. Las transiciones se ejecutan desde las acciones del listado.

Tras actualizar dependencias, reinicia Django y recarga el navegador (Ctrl+F5). En producción ejecuta `collectstatic --noinput` para publicar también los recursos de Unfold y la fuente. Esta personalización sigue dentro de Django Admin.

Para revisar el diseño sin datos reales ni usuarios permanentes, puedes generar vistas HTML usando una base de pruebas aislada:

```powershell
python scripts\render_admin_preview.py
python scripts\serve_admin_preview.py
# Abrir http://127.0.0.1:8765/index.html
# También: products.html, order.html, product-form.html, login.html
```

Estas vistas son estáticas y usan datos de demostración; los enlaces/formularios no operan sobre la API. El servidor de vistas es temporal y se detiene con Ctrl+C. La base temporal se elimina al finalizar el render. Los archivos generados en `.artifacts/` no se versionan.

En Admin puedes crear categorías, marcas, productos, variantes e imágenes. Para gestionar existencias, añade un **movimiento de inventario**:

- `IN`: entrada de unidades libres.
- `OUT`: salida manual de unidades libres.
- `ADJUSTMENT`: diferencia firmada de conteo; admite negativos si hay suficientes unidades libres.

El servicio crea el registro de inventario cuando haga falta. En Inventarios solo se edita el nivel de reorden; cantidades y variante existente son de solo lectura. Los movimientos registran usuario, fecha y referencia y no se editan ni borran desde Admin. `RESERVATION` y `RELEASE` son operaciones internas de pedidos y no se admiten como movimiento manual en Admin.

`quantity_available` significa **unidades libres**, además de `quantity_reserved`. Checkout resta libres y suma reservadas; el envío consume reservadas; cancelar libera la reserva. Las restricciones de PostgreSQL y los bloqueos impiden valores negativos. Los cambios de stock deben realizarse mediante `move_stock`; no uses `QuerySet.update` ni SQL directo para operaciones de negocio.

Las acciones de pedidos usan el servicio de transiciones y requieren `is_staff` activo más el permiso `orders.change_order` (o superusuario):

```text
PENDING → CONFIRMED → PROCESSING → SHIPPED → DELIVERED → REFUNDED
   └─────────┴─────────────┴──────→ CANCELLED
```

Se permite cancelar desde PENDING, CONFIRMED y PROCESSING. No se cancela desde SHIPPED ni se retrocede desde DELIVERED. CANCELLED y REFUNDED son terminales. Los reembolsos son un estado administrativo; no procesan dinero ni reponen stock automáticamente. Registra una entrada si una devolución física se acepta. Las reservas no expiran automáticamente: cancela pedidos abandonados desde Admin.

Totales, snapshots, direcciones históricas e historial son de solo lectura. Carritos se inspeccionan desde Admin sin alterar sus artículos. La API de pedidos solo muestra pedidos del propio usuario; un administrador utiliza Admin para consultar todos.

Las imágenes aceptan JPEG, PNG y WebP, máximo 5 MB y 20 megapíxeles, con inspección del contenido. Una imagen vinculada a variante debe corresponder al mismo producto. Solo puede existir una imagen primaria por producto. En desarrollo se guardan en `media/`, servidas por Django solo con DEBUG activo.

## Errores y límites de solicitudes

```json
{"error": {"code": "conflict", "details": {"detail": "Inventario insuficiente para completar la operación."}}}
```

Validación usa 400; JWT ausente/inválido, 401; permisos, 403; recursos ajenos o inexistentes, 404; conflictos de dominio, 409; rate limiting, 429. `details` puede ser objeto, lista o texto. En producción los errores internos son JSON genérico sin traceback. Admin conserva sus formularios y mensajes estándar.

Login/refresh: 10 por minuto; registro: 5 por hora; checkout: 20 por hora. Configura `LOGIN_RATE`, `REGISTER_RATE` y `CHECKOUT_RATE`. El throttling DRF es una protección de aplicación aproximada; añade límites en el proxy para ataques y concurrencia elevada. El cache local solo sirve en desarrollo; producción exige cache compartida.

## Pruebas y calidad

Arranca PostgreSQL antes de ejecutar pruebas. Usa una base exclusiva de desarrollo: pytest crea y elimina `test_surnova`, y el usuario de pruebas necesita permiso `CREATEDB`. Las pruebas no deben apuntar a producción.

```powershell
python -m pytest
python -m ruff check .
python -m ruff format --check .
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py spectacular --file schema.yml --validate --fail-on-warn
python -m pip check
```

La suite cubre registro/login/refresh/logout, privacidad, filtros y variantes ocultas, totales del servidor, cantidades inválidas, adopción de carrito, checkout, rollback completo, inventario negativo, snapshots, transiciones, permisos de Admin, idempotencia y compras simultáneas de la última unidad. Las pruebas concurrentes requieren PostgreSQL real; no se sustituyen por SQLite. `config.settings.test` utiliza hash rápido únicamente para tests.

## Producción

Utiliza `DJANGO_SETTINGS_MODULE=config.settings.production`, un secreto aleatorio de al menos 50 caracteres y `DJANGO_DEBUG=False`. Producción mantiene DEBUG desactivado aunque el entorno indique lo contrario, exige PostgreSQL y cache compartida. No uses `runserver` como servidor de producción.

- **HTTPS obligatorio** para API y Admin. Usa un servidor ASGI/WSGI y un proxy TLS. Se habilitan redirección HTTPS, cookies seguras y HSTS.
- Base de datos con TLS por defecto (`DATABASE_SSL_REQUIRE=True`). Puede deshabilitarse explícitamente para una red privada controlada, según tu infraestructura. El usuario de producción no debe ser el superusuario del contenedor local.
- Configura `DJANGO_ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS` y `CSRF_TRUSTED_ORIGINS` con dominios concretos. CORS no sustituye autenticación.
- Cache compartida: `DJANGO_CACHE_BACKEND=django.core.cache.backends.redis.RedisCache` y `DJANGO_CACHE_LOCATION=redis://.../1`. Redis no se levanta por defecto en Compose; aporta un servicio de cache en tu despliegue.
- Si el proxy elimina y reemplaza headers reenviados de clientes, habilita `DJANGO_TRUST_PROXY_SSL_HEADER=True` y configura `DJANGO_NUM_PROXIES` según la topología. El valor predeterminado 0 limita por dirección remota directa.
- Ejecuta `python manage.py collectstatic --noinput` y sirve `staticfiles/` con tu infraestructura. Para imágenes externas, instala el backend de almacenamiento elegido, configura `DJANGO_MEDIA_STORAGE` y sus opciones JSON en `DJANGO_MEDIA_STORAGE_OPTIONS`; `DJANGO_MEDIA_URL` es configurable. Sirve subidas desde un origen separado sin ejecución de contenido.
- Guarda secretos en un gestor de secretos; limita accesos a Admin y base, realiza backups y prueba restauraciones. No registres cabeceras Authorization, cuerpos de login/refresh, tokens de carrito, contraseñas ni secretos.
- Verifica el despliegue con `python manage.py check --deploy --settings=config.settings.production`, migra antes de atender tráfico y programa `flushexpiredtokens`.

No se han configurado un proveedor de hosting, certificado, bucket, cache de producción ni pasarela de pago. El proyecto deja definidos los puntos de configuración para esa infraestructura.
