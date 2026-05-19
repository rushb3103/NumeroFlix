from flask import Flask
from .routes.index import main
from .routes.auth import auth
from .routes.video import video
from .utils.db import db
from flask_migrate import Migrate
from .config import Config
from flask_bootstrap import Bootstrap5

## initialize app

migrate = Migrate()


def create_app(config_name):
    app = Flask(__name__)
    app.config.from_object(config_name)
    db.init_app(app)
    migrate.init_app(app, db)
    return app


app = create_app(Config)
bootstrap = Bootstrap5(app)
app.register_blueprint(main)
app.register_blueprint(auth, url_prefix='/auth')
app.register_blueprint(video, url_prefix='/video')

# db.create_all()
## run app
# if __name__ == '__main__':
#     app.run(debug=True)
