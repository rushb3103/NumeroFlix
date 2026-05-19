from app.utils.db import db
from pydantic import BaseModel, Field
from app.models.content import Content

class VideoContent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content_id = db.Column(db.Integer, db.ForeignKey(Content.id), nullable=False)
    video_url = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=db.func.now())
    updated_at = db.Column(db.DateTime, nullable=False, default=db.func.now(), onupdate=db.func.now())

    def __repr__(self):
        return f"<VideoContent {self.content_id}>"
    
class VideoContentCreateSchema(BaseModel):
    content_id: int = Field(min_value=1, max_value=100)
    video_url: str = Field(min_length=4, max_length=256)
