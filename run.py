#!../venv/bin/python

from werkzeug.serving import run_simple
from werkzeug.middleware.dispatcher import DispatcherMiddleware

from frontend import app as frontend_app

# werkzeug.wsgi.DispatcherMiddleware allows combining applications. 
application = DispatcherMiddleware(frontend_app)

if __name__ == "__main__":
    run_simple('0.0.0.0', 
               port = 5000, 
               application = application,
               use_reloader=True, 
               use_debugger=True, 
               use_evalex=True,
               threaded=True)
    