import os
from flask import Flask
from dotenv import load_dotenv
from sqlalchemy import event
from .extensions import db, migrate, login_manager, scheduler


def create_app():
    load_dotenv()
    app = Flask(__name__, static_folder="static", template_folder="templates")

    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev")
    # Normalizar la URL de DB para forzar UTF-8 si no está presente
    _raw_db_url = os.getenv("DATABASE_URL")
    if _raw_db_url:
        _lower = _raw_db_url.lower()
        if ("client_encoding" not in _lower) and ("options=" not in _lower):
            sep = "&" if "?" in _raw_db_url else "?"
            _raw_db_url = f"{_raw_db_url}{sep}options=-c%20client_encoding%3DUTF8"
    app.config["SQLALCHEMY_DATABASE_URI"] = _raw_db_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["UPLOAD_FOLDER"] = os.getenv("UPLOAD_FOLDER", "uploads")

    # Extensiones
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    # Asegurar que el cliente use UTF-8 al conectarse a PostgreSQL
    # Esto ayuda a prevenir UnicodeDecodeError cuando la DB o los datos tienen acentos/ñ
    def _set_client_encoding(dbapi_connection, connection_record):
        try:
            cursor = dbapi_connection.cursor()
            cursor.execute("SET client_encoding TO 'UTF8';")
            cursor.close()
        except Exception:
            # Evitar romper el arranque si el SET falla por algún motivo
            pass

    with app.app_context():
        try:
            event.listen(db.engine, "connect", _set_client_encoding)
        except Exception:
            # Si aún no hay engine o falla la escucha, lo ignoramos silenciosamente
            pass

    # Programador de tareas para alertas
    from .jobs.alerts import register_jobs
    register_jobs(app)

    # Blueprints
    from .auth.routes import bp as auth_bp
    from .dashboard.routes import bp as dashboard_bp
    from .clientes.routes import bp as clientes_bp
    from .proyectos.routes import bp as proyectos_bp
    from .propiedades.routes import bp as propiedades_bp
    from .vencimientos.routes import bp as vencimientos_bp
    from .documentos.routes import bp as documentos_bp
    from .mades.routes import bp as mades_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(clientes_bp, url_prefix="/clientes")
    app.register_blueprint(propiedades_bp, url_prefix="/propiedades")
    app.register_blueprint(proyectos_bp, url_prefix="/proyectos")
    app.register_blueprint(vencimientos_bp, url_prefix="/vencimientos")
    app.register_blueprint(documentos_bp, url_prefix="/documentos")
    app.register_blueprint(mades_bp, url_prefix="/mades")

    # Crear carpeta de uploads
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    return app
