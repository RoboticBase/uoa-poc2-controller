#!/usr/bin/env python
import os

from flask import Flask

from src import api, const, errors

app = Flask(__name__)
app.config.from_pyfile('config.cfg')

shipment_api_view = api.ShipmentAPI.as_view(api.ShipmentAPI.NAME)
app.add_url_rule('/api/v1/shipments/', view_func=shipment_api_view, methods=['POST', ])

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
