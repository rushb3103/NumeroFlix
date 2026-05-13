from app.utils.db import db
from pydantic import BaseModel, EmailStr, field_validator, Field
from werkzeug.security import generate_password_hash, check_password_hash


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True, nullable=False)
    email = db.Column(db.String(120), index=True, unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    last_login_at = db.Column(db.DateTime)

    def __repr__(self):
        return f"<User {self.username}>"

    def set_password(self, password: str) -> None:
        self.password = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password, password)

    @classmethod
    def from_schema(cls, schema):
        obj = cls(username=schema.username, email=schema.email)
        obj.set_password(schema.password)
        return obj


class UserCreateSchema(BaseModel):
    username: str = Field(min_length=4, max_length=32)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)

    @field_validator("username")
    def validate_username(cls, v):
        if not v.strip():
            raise ValueError("Username cannot be empty")
        return v.strip()

    @field_validator("password")
    def validate_password(cls, v):
        if not v.strip():
            raise ValueError("Password cannot be empty")
        return v.strip()