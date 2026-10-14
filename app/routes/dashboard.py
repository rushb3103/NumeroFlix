from flask import Blueprint

dashboard = Blueprint("dashboard", __name__)

@dashboard.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    pass