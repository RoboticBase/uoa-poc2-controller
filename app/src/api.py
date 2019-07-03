from flask import abort, jsonify, request
from flask.views import MethodView


class ShipmentAPI(MethodView):
    NAME = 'shipmentapi'

    def post(self):
        payload = request.json

        if not isinstance(payload, dict):
            abort(400, {
                'message': 'invalid payload',
            })

        res = {
            'result': None,
        }

        res['result'] = 'success'
        return jsonify(res), 201
