from app import db
from pydantic import BaseModel, EmailStr, field_validator, Field


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password = db.Column(db.String(128))
    last_login_at = db.Column(db.DateTime)

    def __repr__(self):
        return f"<User {self.username}>"

    @classmethod
    def from_schema(cls, schema):
        return cls(
            username=schema.username, email=schema.email, password=schema.password
        )


class UserCreateSchema(BaseModel):
    username: str = Field(min_length=4, max_length=32)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

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
