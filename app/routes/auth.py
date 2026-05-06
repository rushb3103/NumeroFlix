from flask import Blueprint
from app.models.user import User
from app.controllers.user import UserController
from flask import request
from app.forms.auth import LoginForm, RegisterForm
from flask import render_template

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['POST', "GET"])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    user = UserController(User)
    user = user.get(username)
    if user and user.password == password:
        return 'Logged in'
    

@auth.route('/register', methods=['POST', "GET"])
def register():
    if request.method == "GET":
        return render_template('signup.html', form=RegisterForm())

    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')
    user = UserController(User)
    user = user.create(username, email, password)
    if user:
        return 'Registered'
    return 'Error'