from flask import Blueprint, flash
from app.models.user import User
from app.controllers.user import UserController
from flask import request
from app.forms.auth import LoginForm, RegisterForm
from flask import render_template
from pydantic import ValidationError

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['POST', "GET"])
def login():
    form = LoginForm()

    if form.validate_on_submit():
        username = request.form.get('username')
        password = request.form.get('password')
        user = UserController(User)
        user = user.get(username)
        if user and user.password == password:
            flash(f'Validated User: {user.username}', 'success')
        else:
            flash('Invalid username or password', 'danger')
    return render_template('login.html', form=form)

@auth.route('/register', methods=['POST', "GET"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
    
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        user = UserController(User)
        try:
            
            user = user.create(username, email, password)
            flash(f'Validated User: {user.username}', 'success')
        except ValidationError as e:
            import traceback
            traceback.print_exc()
            # errors = [
            #     f"{err['loc'][0]}: {err['msg']}"
            #     for err in e.errors()
            # ]
            for error in e.errors():
                print(error)

                flash(f"{error['loc'][0]}: {error['msg']}", "danger")
            # return 0
        # if user:
        #     return 'Registered'
        # return 'Error'
    return render_template('signup.html', form=form)