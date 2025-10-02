import os
from flask import Flask
from dotenv import load_dotenv
from .extensions import db, migrate, login_manager, scheduler


def create_app():
    load_dotenv()
    app = Flask(__name__, static_folder="static", template_folder="templates")

    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["UPLOAD_FOLDER"] = os.getenv("UPLOAD_FOLDER", "uploads")

    # Extensiones
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

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
