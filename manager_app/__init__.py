from flask import Flask
from manager_app.config import Config

app = Flask(__name__)

app.config.from_object(Config)

from manager_app import main




