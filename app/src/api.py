import os

from flask import abort, jsonify, request
from flask.views import MethodView

from src import const, orion
from src.waypoint import Waypoint

FIWARE_SERVICE = os.environ[const.FIWARE_SERVICE]
DELIVERY_ROBOT_SERVICEPATH = os.environ[const.DELIVERY_ROBOT_SERVICEPATH]
DELIVERY_ROBOT_TYPE = os.environ[const.DELIVERY_ROBOT_TYPE]
DELIVERY_ROBOT_01 = os.environ[const.DELIVERY_ROBOT_01]


class CommonMixin:
    def check_mode(self):
        current_mode = orion.get_entity(
            FIWARE_SERVICE,
            DELIVERY_ROBOT_SERVICEPATH,
            DELIVERY_ROBOT_TYPE,
            DELIVERY_ROBOT_01)['mode']['value']

        if current_mode == const.MODE_NAVI:
            abort(423, {
                'message': f'robot is navigating now'
            })


class ShipmentAPI(CommonMixin, MethodView):
    NAME = 'shipmentapi'

    def post(self):
        shipment_list = request.json

        if not isinstance(shipment_list, dict):
            abort(400, {
                'message': f'invalid shipment_list, {shipment_list}',
            })

        self.check_mode()

        routes, waypoints_list = Waypoint().estimate_routes(shipment_list)
        head, *tail = waypoints_list
        payload = orion.make_delivery_robot_command('navi', head['waypoints'], head, tail, routes)

        orion.send_command(
            FIWARE_SERVICE,
            DELIVERY_ROBOT_SERVICEPATH,
            DELIVERY_ROBOT_TYPE,
            DELIVERY_ROBOT_01,
            payload
        )

        return jsonify({'result': 'success'}), 201
