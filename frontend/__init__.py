from flask import Flask
from frontend.config import Config

global memcache

app = Flask(__name__)
memcache = {}

app.config.from_object(Config)

from frontend import main




