import os
import json
from logging import getLogger

from flask import abort, jsonify, request
from flask.views import MethodView

from src import const, orion
from src.waypoint import Waypoint
from src.token import Token, TokenMode
from src.caller import Caller
from src.utils import flatten

FIWARE_SERVICE = os.environ[const.FIWARE_SERVICE]
DELIVERY_ROBOT_SERVICEPATH = os.environ[const.DELIVERY_ROBOT_SERVICEPATH]
DELIVERY_ROBOT_TYPE = os.environ[const.DELIVERY_ROBOT_TYPE]
DELIVERY_ROBOT_LIST = json.loads(os.environ[const.DELIVERY_ROBOT_LIST])
ROBOT_UI_SERVICEPATH = os.environ[const.ROBOT_UI_SERVICEPATH]
ROBOT_UI_TYPE = os.environ[const.ROBOT_UI_TYPE]
ID_TABLE = json.loads(os.environ[const.ID_TABLE])

logger = getLogger(__name__)


class CommonMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._waypoint = Waypoint()

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
        return self.calc_state(is_navi, robot_id)

    def calc_state(self, is_navi, robot_id, robot_entity=None):
        if is_navi:
            return const.STATE_MOVING
        else:
            if not robot_entity:
                robot_entity = orion.get_entity(
                    FIWARE_SERVICE,
                    DELIVERY_ROBOT_SERVICEPATH,
                    DELIVERY_ROBOT_TYPE,
                    robot_id)
            navigating_waypoints = robot_entity['navigating_waypoints']['value']
            order = robot_entity['order']['value']

            if not isinstance(navigating_waypoints, dict) or not navigating_waypoints:
                return const.STATE_STANDBY
            else:
                to = navigating_waypoints['to']
                if to == order['source']:
                    return const.STATE_STANDBY
                elif to == order['destination']:
                    try:
                        caller = Caller.value_of(robot_entity['caller']['value'])
                        return const.STATE_DELIVERING if caller == Caller.ORDERING else const.STATE_PICKING
                    except ValueError as e:
                        logger.warn(f'unkown caller (estimate "state" as const.STATE_PICKING), {e}')
                        return const.STATE_PICKING
                elif to in order['via']:
                    return const.STATE_PICKING
                else:
                    return const.STATE_MOVING

    def get_destination_id(self, robot_id):
        navigating_waypoints = orion.get_entity(
            FIWARE_SERVICE,
            DELIVERY_ROBOT_SERVICEPATH,
            DELIVERY_ROBOT_TYPE,
            robot_id)['navigating_waypoints']['value']
        if not isinstance(navigating_waypoints, dict) or not navigating_waypoints:
            return ''
        else:
            return navigating_waypoints['destination']

    def get_destination_name(self, robot_id):
        navigating_waypoints_to = self.get_destination_id(robot_id)
        if navigating_waypoints_to == '':
            return ''

        destination = orion.get_entity(
            FIWARE_SERVICE,
            DELIVERY_ROBOT_SERVICEPATH,
            const.PLACE_TYPE,
            navigating_waypoints_to)
        return destination['name']['value']

    def move_next(self, robot_id):
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
        logger.info(f'move robot({robot_id}) to "{head["to"]}" (waypoints={head["waypoints"]}')


class ShipmentAPI(CommonMixin, MethodView):
    NAME = 'shipmentapi'

    def post(self):
        logger.debug(f'ShipmentAPI.post')
        shipment_list = request.json

        if not isinstance(shipment_list, dict):
            abort(400, {
                'message': f'invalid shipment_list, {shipment_list}',
            })

        available_robot = self.get_available_robot()
        caller = Caller.get(shipment_list)
        routes, waypoints_list, order = self._waypoint.estimate_routes(shipment_list, available_robot['id'])
        head, *tail = waypoints_list

        payload = orion.make_delivery_robot_command('navi', head['waypoints'], head, tail, routes, order, caller)

        orion.send_command(
            FIWARE_SERVICE,
            DELIVERY_ROBOT_SERVICEPATH,
            DELIVERY_ROBOT_TYPE,
            available_robot['id'],
            payload
        )
        logger.info(f'move robot({available_robot["id"]}) to "{head["to"]}" (waypoints={head["waypoints"]}, order={order}, caller={caller}')

        return jsonify({'result': 'success', 'delivery_robot': available_robot, 'order': order, 'caller': caller.value}), 201


class RobotStateAPI(CommonMixin, MethodView):
    NAME = 'robotstateapi'

    def get(self, robot_id):
        logger.debug(f'RobotStateAPI.get, robot_id={robot_id}')
        current_state = self.get_state(robot_id)
        destination = self.get_destination_name(robot_id)
        return jsonify({'id': robot_id, 'state': current_state, 'destination': destination}), 200


class MoveNextAPI(CommonMixin, MethodView):
    NAME = 'movenextapi'

    def patch(self, robot_id):
        logger.debug(f'MoveNextAPI.patch, robot_id={robot_id}')
        self.move_next(robot_id)
        return jsonify({'result': 'success'}), 200


class EmergencyAPI(MethodView):
    NAME = 'emergencyapi'

    def patch(self, robot_id):
        logger.debug(f'EmergencyAPI.patch, robot_id={robot_id}')
        payload = orion.make_emergency_command('stop')

        orion.send_command(
            FIWARE_SERVICE,
            DELIVERY_ROBOT_SERVICEPATH,
            DELIVERY_ROBOT_TYPE,
            robot_id,
            payload
        )
        logger.info(f'send emergency command ("stop") to robot({robot_id})')

        return jsonify({'result': 'success'}), 200


class RobotNotificationAPI(CommonMixin, MethodView):
    NAME = 'robotnotificationapi'

    def post(self):
        logger.debug(f'RobotNotificationAPI.post')
        for data in request.json['data']:
            robot_id = data['id']
            next_mode = data['mode']['value']

            robot_entity = orion.get_entity(
                FIWARE_SERVICE,
                DELIVERY_ROBOT_SERVICEPATH,
                DELIVERY_ROBOT_TYPE,
                robot_id)

            next_state = self.calc_state(next_mode == const.MODE_NAVI, robot_id, robot_entity)
            current_mode = robot_entity['current_mode']['value']
            current_state = robot_entity['current_state']['value']
            ui_id = ID_TABLE[robot_id]

            if next_mode != current_mode:
                payload = orion.make_updatemode_command(next_mode)
                orion.send_command(
                    FIWARE_SERVICE,
                    DELIVERY_ROBOT_SERVICEPATH,
                    DELIVERY_ROBOT_TYPE,
                    robot_id,
                    payload)
                logger.info(f'update robot state, robot_id={robot_id}, current_mode={current_mode}, next_mode={next_mode}')

                self._action(robot_id, ui_id, robot_entity, next_mode)
                self._send_state(robot_id, ui_id, next_state, current_state)

        return jsonify({'result': 'success'}), 200

    def _action(self, robot_id, ui_id, robot_entity, next_mode):
        if next_mode == const.MODE_STANDBY:
            nws = robot_entity['navigating_waypoints']['value']

            if isinstance(nws, dict) and nws and 'action' in nws and 'func' in nws['action'] and nws['action']['func']:
                func = nws['action']['func']
                token = Token.get(nws['action']['token'])
                waiting_route = nws['action']['waiting_route']
                if func == 'lock':
                    has_lock = token.get_lock(robot_id)
                    if has_lock:
                        self.move_next(robot_id)
                        self._send_token_info(ui_id, token, TokenMode.LOCK)
                    else:
                        if waiting_route:
                            self._take_refuge(robot_id, waiting_route)
                        self._send_token_info(ui_id, token, TokenMode.SUSPEND)
                elif func == 'release':
                    new_owner_id = token.release_lock(robot_id)
                    self.move_next(robot_id)
                    self._send_token_info(ui_id, token, TokenMode.RELEASE)
                    if new_owner_id:
                        self.move_next(new_owner_id)
                        self._send_token_info(ID_TABLE[new_owner_id], token, TokenMode.RESUME)
                        self._send_token_info(ID_TABLE[new_owner_id], token, TokenMode.LOCK)

    def _send_state(self, robot_id, ui_id, next_state, current_state):
        if next_state != current_state:
            payload = orion.make_updatestate_command(next_state)
            orion.send_command(
                FIWARE_SERVICE,
                DELIVERY_ROBOT_SERVICEPATH,
                DELIVERY_ROBOT_TYPE,
                robot_id,
                payload)

            destination = self.get_destination_name(robot_id)
            payload = orion.make_robotui_sendstate_command(next_state, destination)
            orion.send_command(
                FIWARE_SERVICE,
                ROBOT_UI_SERVICEPATH,
                ROBOT_UI_TYPE,
                ui_id,
                payload)
            logger.info(f'publish new state to robot ui({ui_id}), '
                        f'current_state={current_state}, next_state={next_state}, destination={destination}')

    def _send_token_info(self, ui_id, token, mode):
        payload = orion.make_robotui_sendtokeninfo_command(token, mode)
        orion.send_command(
            FIWARE_SERVICE,
            ROBOT_UI_SERVICEPATH,
            ROBOT_UI_TYPE,
            ui_id,
            payload)
        logger.info(f'publish new token_info to robot ui({ui_id}), token={token}, mode={mode}, '
                    f'lock_owner_id={token.lock_owner_id}, prev_owner_id={token.prev_owner_id}')

    def _take_refuge(self, robot_id, waiting_route):
        places = self._waypoint.get_places([flatten([waiting_route['via'], waiting_route['to']])])
        waypoints = self._waypoint.get_waypoints(
            [places[place_id] for place_id in waiting_route['via']],
            [places[waiting_route['to']]]
        )
        navigating_waypoints = {
            'to': waiting_route['to'],
            'destination': self.get_destination_id(robot_id),
            'action': {
                'func': '',
                'token': '',
                'waiting_route': {},
            },
            'waypoints': waypoints,
        }
        payload = orion.make_delivery_robot_command('navi', waypoints, navigating_waypoints)
        orion.send_command(
            FIWARE_SERVICE,
            DELIVERY_ROBOT_SERVICEPATH,
            DELIVERY_ROBOT_TYPE,
            robot_id,
            payload
        )
        logger.info(f'take refuge a robot({robot_id}) in "{waiting_route["to"]}"')
