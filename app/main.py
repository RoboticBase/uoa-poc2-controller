#!/usr/bin/env python
import os

from flask import Flask
from flask_cors import CORS

from src import api, const, errors

CORS_ORIGINS = os.environ.get(const.CORS_ORIGINS, None)

app = Flask(__name__)
if CORS_ORIGINS:
    CORS(app, resources={r'/*': {'origins': CORS_ORIGINS}})
app.config.from_pyfile('config.cfg')

shipment_api_view = api.ShipmentAPI.as_view(api.ShipmentAPI.NAME)
movenext_api_view = api.MoveNextAPI.as_view(api.MoveNextAPI.NAME)
emergency_api_view = api.EmergencyAPI.as_view(api.EmergencyAPI.NAME)
app.add_url_rule('/api/v1/shipments/', view_func=shipment_api_view, methods=['POST', ])
app.add_url_rule('/api/v1/robots/<robot_id>/nexts/', view_func=movenext_api_view, methods=['PATCH', ])
app.add_url_rule('/api/v1/robots/<robot_id>/emergencies/', view_func=emergency_api_view, methods=['PATCH', ])

app.register_blueprint(errors.app)


if __name__ == '__main__':
    default_port = app.config['DEFAULT_PORT']
    try:
        port = int(os.environ.get(const.LISTEN_PORT, str(default_port)))
        if port < 1 or 65535 < port:
            port = default_port
    except ValueError:
        port = default_port
    app.run(host='0.0.0.0', port=port)
