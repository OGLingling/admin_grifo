# Estación Norte · Sistema administrativo

Aplicación web Django para registrar ventas y compras, controlar existencias de tienda y tanques de combustible, y llevar aperturas, movimientos y cierres de caja. La interfaz y los mensajes están en español y la zona horaria es `America/Lima`.

## Requisitos

- Python 3.12 o superior.
- MariaDB 10.11 o superior (o MySQL 8.4 o superior).
- En Windows, instala los componentes de compilación que `mysqlclient` requiera si pip no encuentra una rueda compatible.

Django 6.1 mantiene compatibilidad con MariaDB 10.11+ y MySQL 8.4+; la versión y compatibilidad están detalladas en las [notas oficiales de Django 6.1](https://docs.djangoproject.com/en/6.1/releases/6.1/).

## Preparación en XAMPP

Abre PowerShell en `C:\xampp\htdocs\admin_grifo` y ejecuta:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Crea la base en phpMyAdmin o en la consola de MariaDB:

```sql
CREATE DATABASE admin_grifo_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

Edita `.env` y asigna las credenciales de MariaDB. Django carga este archivo automáticamente al iniciar. No compartas ni agregues `.env` al repositorio.

Después crea las tablas y la cuenta administradora:

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py createsuperuser
.\.venv\Scripts\python.exe manage.py runserver
```

Abre `http://127.0.0.1:8000/`. Usa `/admin/` para gestionar cuentas de operadores; la cuenta inicial se crea con `createsuperuser`.

## Flujo operativo incluido

1. Crea los productos de combustible y de tienda.
2. Configura tanques con capacidad y nivel de alerta. La existencia inicial se puede indicar al crear el tanque; después cambia mediante compras y ventas.
3. Abre la caja con el efectivo inicial del turno.
4. Registra compras para aumentar existencias y ventas para descontarlas. Las ventas de combustible requieren tanque y se validan contra su nivel disponible.
5. Registra ingresos y egresos de efectivo. El efectivo esperado calcula fondo inicial + ventas en efectivo + ingresos − egresos; tarjeta y transferencia no aumentan efectivo.
6. Cierra caja indicando el efectivo contado. El sistema guarda ese conteo para compararlo con el esperado.

Las altas de compra, venta y movimientos se guardan en transacciones atómicas; las ventas bloquean las filas de inventario durante el despacho para evitar vender existencias que ya consumió otra operación concurrente. Los registros de operaciones no se pueden modificar ni borrar desde el panel de administración.

## Variables de entorno

| Variable | Uso |
| --- | --- |
| `DJANGO_SECRET_KEY` | Clave secreta de Django |
| `DJANGO_DEBUG` | Depuración local; debe ser `False` en producción |
| `DJANGO_ALLOWED_HOSTS` | Lista de hosts separados por comas |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD` | Base y usuario de MariaDB |
| `DB_HOST`, `DB_PORT` | Servidor MariaDB; XAMPP suele usar `127.0.0.1:3306` |

Antes de exponer el sistema fuera del equipo local, configura una clave secreta nueva, `DJANGO_DEBUG=False`, `DJANGO_ALLOWED_HOSTS` con el dominio real, HTTPS y las opciones de cookies seguras de Django. La configuración actual está preparada para desarrollo local.
