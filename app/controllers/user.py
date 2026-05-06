from app.utils.db import db
from app.models.user import User, UserCreateSchema


class UserController:
    def __init__(self, user):
        self.user = user

    def create(self, username, email, password):
        try:
            data = UserCreateSchema(username=username, email=email, password=password)
        except Exception:
            import traceback
            traceback.print_exc()
            return None
        user = self.user.from_schema(data)
        db.session.add(user)
        db.session.commit()
        return user

    def get(self, id):
        return db.session.query(User).filter_by(id=id).first()

    def update(self, id, username, email, password):
        user = db.session.query(User).filter_by(id=id).first()
        if user:
            user.username = username
            user.email = email
            user.password = password
            db.session.commit()
        return None

    def delete(self, id):
        user = db.session.query(User).filter_by(id=id).first()
        if user:
            db.session.delete(user)
            db.session.commit()
            return user
        return None
