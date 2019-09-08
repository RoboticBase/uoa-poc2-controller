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
    def check_mode(self, robot_id):
        current_mode = orion.get_entity(
            FIWARE_SERVICE,
            DELIVERY_ROBOT_SERVICEPATH,
            DELIVERY_ROBOT_TYPE,
            robot_id)['mode']['value']

        if current_mode == const.MODE_NAVI:
            abort(423, {
                'message': f'robot({robot_id}) is navigating now',
                'id': robot_id,
            })

    def get_available_robot(self):
        # FIXME
        self.check_mode(DELIVERY_ROBOT_01)
        return {
            'id': DELIVERY_ROBOT_01
        }


class ShipmentAPI(CommonMixin, MethodView):
    NAME = 'shipmentapi'

    def post(self):
        shipment_list = request.json

        if not isinstance(shipment_list, dict):
            abort(400, {
                'message': f'invalid shipment_list, {shipment_list}',
            })

        available_robot = self.get_available_robot()

        routes, waypoints_list = Waypoint().estimate_routes(shipment_list)
        head, *tail = waypoints_list
        payload = orion.make_delivery_robot_command('navi', head['waypoints'], head, tail, routes)

        orion.send_command(
            FIWARE_SERVICE,
            DELIVERY_ROBOT_SERVICEPATH,
            DELIVERY_ROBOT_TYPE,
            available_robot['id'],
            payload
        )
        print(f'move robot({available_robot["id"]}) to "{head["to"]}" (waypoints={head["waypoints"]}')

        return jsonify({'result': 'success', 'delivery_robot': available_robot}), 201


class MoveNextAPI(CommonMixin, MethodView):
    NAME = 'movenextapi'

    def patch(self, robot_id):
        self.check_mode(robot_id)

        remaining_waypoints_list = orion.get_entity(
            FIWARE_SERVICE,
            DELIVERY_ROBOT_SERVICEPATH,
            DELIVERY_ROBOT_TYPE,
            robot_id)['remaining_waypoints_list']['value']

        if len(remaining_waypoints_list) == 0:
            abort(412, {
                'message': f'no remaining waypoints for robot({robot_id})',
                'id': robot_id,
            })

        head, *tail = remaining_waypoints_list
        payload = orion.make_delivery_robot_command('navi', head['waypoints'], head, tail)

        orion.send_command(
            FIWARE_SERVICE,
            DELIVERY_ROBOT_SERVICEPATH,
            DELIVERY_ROBOT_TYPE,
            robot_id,
            payload
        )
        print(f'move robot({robot_id}) to "{head["to"]}" (waypoints={head["waypoints"]}')

        return jsonify({'result': 'success'}), 200


class EmergencyAPI(MethodView):
    NAME = 'emergencyapi'

    def patch(self, robot_id):
        payload = orion.make_emergency_command('stop')

        orion.send_command(
            FIWARE_SERVICE,
            DELIVERY_ROBOT_SERVICEPATH,
            DELIVERY_ROBOT_TYPE,
            robot_id,
            payload
        )
        print(f'send emergency command ("stop") to robot({robot_id})')

        return jsonify({'result': 'success'}), 200
