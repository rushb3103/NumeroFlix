from app import db
from app.models.user import User

class UserController:
    def __init__(self, user):
        self.user = user
    
    def create(self, username, email, password):
        self.user.username = username
        self.user.email = email
        self.user.password = password
        db.session.add(self.user)
        db.session.commit()
        return self.user
    
    def get(self, id):
        return db.session.query(User).filter_by(id=id).first()
    
    def update(self, id, username, email, password):
        user = db.session.query(User).filter_by(id=id).first()
        if user:
            user.username = username
            user.email = email
            user.password = password
            db.session.commit()
            return user
        return None
    
    def delete(self, id):
        user = db.session.query(User).filter_by(id=id).first()
        if user:
            db.session.delete(user)
            db.session.commit()
            return user
        return None
    