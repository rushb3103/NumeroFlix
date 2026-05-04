
from flask import Flask
from .routes.index import main

## initialize app
app = Flask(__name__)

app.register_blueprint(main)

## run app
# if __name__ == '__main__':
#     app.run(debug=True)