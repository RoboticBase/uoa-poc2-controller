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
ROBOT_UI_SERVICEPATH = os.environ[const.ROBOT_UI_SERVICEPATH]
ROBOT_UI_TYPE = os.environ[const.ROBOT_UI_TYPE]
ID_TABLE = json.loads(os.environ[const.ID_TABLE])


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
        return self.calc_state(is_navi, remaining_waypoints_list)

    def calc_state(self, is_navi, remaining_waypoints_list):
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

    def get_destination(self, robot_id):
        navigating_waypoints = orion.get_entity(
            FIWARE_SERVICE,
            DELIVERY_ROBOT_SERVICEPATH,
            DELIVERY_ROBOT_TYPE,
            robot_id)['navigating_waypoints']['value']
        if not isinstance(navigating_waypoints, dict):
            return ''

        destination = orion.get_entity(
            FIWARE_SERVICE,
            DELIVERY_ROBOT_SERVICEPATH,
            const.PLACE_TYPE,
            navigating_waypoints['to'])
        return destination['name']['value']


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
        destination = self.get_destination(robot_id)

        return jsonify({'id': robot_id, 'state': current_state, 'destination': destination}), 200


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


class RobotNotificationAPI(CommonMixin, MethodView):
    NAME = 'robotnotificationapi'

    def post(self):
        for data in request.json['data']:
            robot_id = data['id']
            next_mode = data['mode']['value']

            remaining_waypoints_list = self.get_remaining_waypoints_list(robot_id)
            next_state = self.calc_state(next_mode == const.MODE_NAVI, remaining_waypoints_list)

            ui_id = ID_TABLE[robot_id]
            ui = orion.get_entity(
                FIWARE_SERVICE,
                ROBOT_UI_SERVICEPATH,
                ROBOT_UI_TYPE,
                ui_id)

            if ui['current_state']['value'] != next_state and ui['current_mode']['value'] != next_mode:
                destination = self.get_destination(robot_id)
                payload = orion.make_robotui_command(next_state, next_mode, destination)
                orion.send_command(
                    FIWARE_SERVICE,
                    ROBOT_UI_SERVICEPATH,
                    ROBOT_UI_TYPE,
                    ui_id,
                    payload)
                print(f'publish new state to robot ui({ui_id}), '
                      f'next_state={next_state}, next_mode={next_mode}, destination={destination}')

        return jsonify({'result': 'success'}), 200
