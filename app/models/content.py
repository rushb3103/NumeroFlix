from app.utils.db import db
from pydantic import BaseModel, Field

class Content(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(128), nullable=False)
    description = db.Column(db.String(256), nullable=False)
    thumbnail = db.Column(db.String(256), nullable=False)
    content_type = db.Column(db.Enum("movie", "series", "episode"), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=db.func.now())
    updated_at = db.Column(db.DateTime, nullable=False, default=db.func.now(), onupdate=db.func.now())

    def __repr__(self):
        return f"<Content {self.title}>"
    
class ContentCreateSchema(BaseModel):
    title: str = Field(min_length=4, max_length=128)
    description: str = Field(min_length=4, max_length=256)
    thumbnail: str = Field(min_length=4, max_length=256)

