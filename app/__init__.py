from flask_login import LoginManager
from .models.user import User

login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'your-secret-key'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///local.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    migrate = Migrate()
    migrate.init_app(app, db)

    db.init_app(app)
    login_manager.init_app(app)

    from .main.routes import main_bp
    from .auth.routes import auth_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)

    return app

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
