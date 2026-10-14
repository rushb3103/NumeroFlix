
from flask import Blueprint, flash, render_template

from app.forms.video import UploadVideoForm
video = Blueprint("video", __name__)


video_api = Blueprint("video_api", __name__)

# Allowed extensions
ALLOWED_EXTENSIONS = {
    "mp4",
    "mkv",
    "webm",
    "mov"
}

# Max upload size (example: 5GB)
MAX_CONTENT_LENGTH = 5 * 1024 * 1024 * 1024


def allowed_file(filename):
    return (
        "." in filename and
        filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


@video.route("/upload", methods=["POST", "GET"])
def upload_video():
    form = UploadVideoForm()

    if form.validate_on_submit():
        pass    

    return render_template("video_upload.html", form=form)
    