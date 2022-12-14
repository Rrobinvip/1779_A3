from re import L
from flask_uploads import UploadSet, IMAGES, configure_uploads
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed, DataRequired
# from wtforms import StringField, SubmitField, FileField
from wtforms.fields import IntegerField, SelectField, StringField, SubmitField, FileField
from wtforms.validators import DataRequired, NumberRange
from frontend import app

'''
This module gives all forms needed for every pages. Forms are written in classes to acquire decent ability on expension.
'''

pictures = UploadSet('photos', IMAGES)
configure_uploads(app, pictures)

class UploadForm(FlaskForm):
    pictures = FileField(
        "Picture",
        validators=[
            FileAllowed(pictures, "Only pictures are allowed"),
            FileRequired("File should not be empty")
        ]
    )
    key = StringField(
        "Key",
        validators=[ 
            DataRequired()
        ],
        render_kw={"placeholder": "Key"}
    )
    submit = SubmitField("Upload")

class UploadForm_api(FlaskForm):
    key = StringField(
        "Key",
        validators=[ 
            DataRequired()
        ]
    )
    file = FileField(
        "Picture",
        validators=[
            FileAllowed(pictures, "Only pictures are allowed"),
            FileRequired("File should not be empty")
        ]
    )
class SearchForm(FlaskForm):
    key = StringField(
        "Key",
        validators=[
            DataRequired()
        ],
        render_kw={"placeholder": "Key"}
    )
    submit = SubmitField("Search")

class ConfigForm(FlaskForm):
    size = IntegerField(
        "size",
        validators=[
            DataRequired(),
            NumberRange(min=1, max=1024)
        ],
        render_kw={"placeholder": "Size ~MB"}
    )
    replacement_policy = SelectField(
        "replacement_policy",
        choices=[(1, "Drop least use"), (2, "Random drop")]
    )
    submit = SubmitField("Apply")

class ClearForm(FlaskForm):
    clear = SubmitField("Clear Memcache")