import os

from flask import abort, jsonify, request
from flask.views import MethodView

from src import const, orion
from src.waypoint import Waypoint


class ShipmentAPI(MethodView):
    NAME = 'shipmentapi'

    def post(self):
        shipment_list = request.json

        if not isinstance(shipment_list, dict):
            abort(400, {
                'message': f'invalid shipment_list, {shipment_list}',
            })

        res = {
            'result': None,
        }
        waypoints = Waypoint().calculate(shipment_list)
        payload = orion.make_delivery_robot_command('navi', waypoints)

        orion.send_command(
            os.environ[const.FIWARE_SERVICE],
            os.environ[const.DELIVERY_ROBOT_SERVICEPATH],
            os.environ[const.DELIVERY_ROBOT_TYPE],
            os.environ[const.DELIVERY_ROBOT_01],
            payload
        )

        res['result'] = 'success'
        return jsonify(res), 201
