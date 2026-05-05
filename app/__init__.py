
from flask import Flask
from .routes.index import main
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from .config import Config

## initialize app
db = SQLAlchemy()
migrate = Migrate()



def create_app(config_name):
    app = Flask(__name__)
    app.config.from_object(config_name)
    db.init_app(app)
    migrate.init_app(app, db)
    return app

app = create_app(Config)
app.register_blueprint(main)
# db.create_all()
## run app
# if __name__ == '__main__':
#     app.run(debug=True)