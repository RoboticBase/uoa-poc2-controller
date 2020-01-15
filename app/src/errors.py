from logging import getLogger

from flask import Blueprint, make_response, jsonify

logger = getLogger(__name__)
app = Blueprint('errors', __name__)


@app.app_errorhandler(400)
@app.app_errorhandler(401)
@app.app_errorhandler(403)
@app.app_errorhandler(404)
@app.app_errorhandler(405)
@app.app_errorhandler(412)
@app.app_errorhandler(422)
@app.app_errorhandler(423)
@app.app_errorhandler(500)
@app.app_errorhandler(Exception)
def error_handler(error):
    code = error.code if hasattr(error, 'code') else 500
    description = error.description if hasattr(error, 'description') else {}

    if code >= 500:
        level = 'error'
    else:
        level = 'warning'
    getattr(logger, level)(str(error))

    return make_response(jsonify(description), code)
