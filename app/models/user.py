# import datetime
# from sqlalchemy import Column, Integer, String, DateTime
from app import db
from flask_validator import ValidateString, ValidateEmail
from sqlalchemy.orm import validates

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password = db.Column(db.String(128))
    last_login_at = db.Column(db.DateTime)

    def __repr__(self):
        return '<User %r>' % self.username
    
    @classmethod
    def __declare_last__(cls):
        ValidateEmail(User.email, message='Invalid email')
        ValidateString(User.username, message='Invalid username')
        ValidateString(User.password, message='Invalid password')

    @validates('username')
    def validate_username(self, key, value):
        if value is None:
            return value
        if not value:
            raise ValueError('Username cannot be empty')
        if len(value) < 4:
            raise ValueError('Username must be at least 4 characters')
        if len(value) > 32:
            raise ValueError('Username cannot be longer than 32 characters')
        return value

    # @validates('email')
    # def validate_email(self, key, value):
    #     if value is None:
    #         return value
    #     if not value:
    #         raise ValueError('Email cannot be empty')
    #     if '@' not in value:
    #         raise ValueError('Email must contain @')
    #     return value
    
    @validates('password')
    def validate_password(self, key, value):
        if value is None:
            return value
        if not value:
            raise ValueError('Password cannot be empty')
        if len(value) < 8:
            raise ValueError('Password must be at least 8 characters')
        if len(value) > 128:
            raise ValueError('Password cannot be longer than 128 characters')
        return value