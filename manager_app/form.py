from flask_wtf import FlaskForm
from flask_wtf.file import DataRequired
# from wtforms import StringField, SubmitField, FileField
from wtforms.fields import IntegerField, SelectField, SubmitField, DecimalField
from wtforms.validators import DataRequired, NumberRange
from decimal import ROUND_DOWN
from frontend import app

'''
This module gives all forms needed for every pages. Forms are written in classes to acquire decent ability on expension.
'''

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

class AutoForm(FlaskForm):
    max_threshold = DecimalField(
        "max_threshold",
        rounding=ROUND_DOWN,
        validators=[
            DataRequired(),
            NumberRange(min=0, max=1)
        ],
        render_kw={"placeholder": "Max threshold: put a decimal greater > 0 and < 1"}
    )
    min_threshold = DecimalField(
        "min_threshold",
        rounding=ROUND_DOWN,
        validators=[
            DataRequired(),
            NumberRange(min=0, max=1)
        ],
        render_kw={"placeholder": "Min threshold: put a decimal greater > 0 and < 1"}
    )
    expand_ratio = DecimalField(
        "expend_ratio",
        rounding=ROUND_DOWN,
        validators=[
            DataRequired(),
            NumberRange(min=1.01, max=8)
        ],
        render_kw={"placeholder": "Expend ratio, max 8 and min 1.01 (Cannot be 1)"}
    )
    shrink_ratio = DecimalField(
        "shrink_ratio",
        rounding=ROUND_DOWN,
        validators=[
            DataRequired(),
            NumberRange(min=0.01, max=0.99)
        ],
        render_kw={"placeholder": "Shrink ratio, max 0.99 and min 0.01 (Cannot be 1 and 0)"}
    )
    submit = SubmitField("Apply")

class ManualForm(FlaskForm):
    growing = SubmitField("Growing")
    shrinking = SubmitField("Shrinking")
    refresh = SubmitField("Refresh status")

class ClearForm(FlaskForm):
    clear = SubmitField("Clear Memcache")

class DeleteForm(FlaskForm):
    delete = SubmitField("Delete all data")

