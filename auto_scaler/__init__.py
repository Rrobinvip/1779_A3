from flask import Flask
from auto_scaler.config import Config

app = Flask(__name__)

from auto_scaler import main