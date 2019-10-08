import os
import json

from flask import abort, jsonify, request
from flask.views import MethodView

from src import const, orion
from src.waypoint import Waypoint

FIWARE_SERVICE = os.environ[const.FIWARE_SERVICE]
DELIVERY_ROBOT_SERVICEPATH = os.environ[const.DELIVERY_ROBOT_SERVICEPATH]
DELIVERY_ROBOT_TYPE = os.environ[const.DELIVERY_ROBOT_TYPE]
DELIVERY_ROBOT_LIST = json.loads(os.environ[const.DELIVERY_ROBOT_LIST])


class CommonMixin:
    def check_mode(self, robot_id):
        if self.__check_navi(robot_id):
            abort(423, {
                'message': f'robot({robot_id}) is navigating now',
                'id': robot_id,
            })

    def __check_navi(self, robot_id):
        current_mode = orion.get_entity(
            FIWARE_SERVICE,
            DELIVERY_ROBOT_SERVICEPATH,
            DELIVERY_ROBOT_TYPE,
            robot_id)['mode']['value']

        return current_mode == const.MODE_NAVI

    def check_working(self, robot_id):
        remaining_waypoints_list = self.get_remaining_waypoints_list(robot_id)
        return isinstance(remaining_waypoints_list, list) and len(remaining_waypoints_list) != 0

    def get_remaining_waypoints_list(self, robot_id):
        return orion.get_entity(
            FIWARE_SERVICE,
            DELIVERY_ROBOT_SERVICEPATH,
            DELIVERY_ROBOT_TYPE,
            robot_id)['remaining_waypoints_list']['value']

    def get_available_robot(self):
        for robot_id in DELIVERY_ROBOT_LIST:
            if robot_id and not (self.__check_navi(robot_id) or self.check_working(robot_id)):
                return {
                    'id': robot_id
                }
        abort(422, {
            'message': f'no available robot',
        })

    def get_state(self, robot_id):
        is_navi = self.__check_navi(robot_id)
        remaining_waypoints_list = self.get_remaining_waypoints_list(robot_id)

        if is_navi:
            return const.STATE_MOVING
        else:
            if not isinstance(remaining_waypoints_list, list):
                return const.STATE_STANDBY
            else:
                if len(remaining_waypoints_list) == 0:
                    return const.STATE_STANDBY
                if len(remaining_waypoints_list) == 1:
                    return const.STATE_DELIVERING
                else:
                    return const.STATE_PICKING


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


class RobotStateAPI(CommonMixin, MethodView):
    NAME = 'robotstateapi'

    def get(self, robot_id):
        current_state = self.get_state(robot_id)
        to_id = orion.get_entity(
            FIWARE_SERVICE,
            DELIVERY_ROBOT_SERVICEPATH,
            DELIVERY_ROBOT_TYPE,
            robot_id)['navigating_waypoints']['value']['to']

        return jsonify({'id': robot_id, 'state': current_state, 'to': to_id}), 200


class MoveNextAPI(CommonMixin, MethodView):
    NAME = 'movenextapi'

    def patch(self, robot_id):
        self.check_mode(robot_id)

        remaining_waypoints_list = self.get_remaining_waypoints_list(robot_id)
        if not isinstance(remaining_waypoints_list, list) or len(remaining_waypoints_list) == 0:
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
