# Consultoría Ambiental - Flask

## Requisitos
- Python 3.10+
- PostgreSQL (BD: Consultora_ambiental)

## Configuración rápida (Windows)
1. Crear entorno virtual:
   python -m venv .venv
   .venv\\Scripts\\activate
2. Instalar dependencias:
   pip install -r requirements.txt
3. Configurar variables:
   Copiar .env.example a .env y ajustar DATABASE_URL, SECRET_KEY y credenciales de admin.
4. Inicializar base (usa tus tablas existentes, no migra):
   Si no existen tablas, puedes generar con Flask-Migrate:
   flask db init
   flask db migrate -m "init"
   flask db upgrade
5. Ejecutar:
   python run.py

Usuario por defecto: ADMIN_USER/ADMIN_PASSWORD desde .env

## Estructura
- app/__init__.py: app factory y registro de blueprints
- app/models.py: modelos que mapean a tablas existentes
- app/*/routes.py: módulos (auth, dashboard, clientes, etc.)
- app/templates/: vistas Bootstrap
- app/static/: assets
- uploads/: carpeta de archivos

## Próximos pasos
- Completar CRUD de propiedades, proyectos, pagos, facturas
- Exportar planillas a Excel/PDF
- Envío de notificaciones reales (email/WhatsApp)
