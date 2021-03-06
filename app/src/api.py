from time import sleep
from logging import getLogger

from flask import abort, jsonify, request
from flask.views import MethodView

import dateutil.parser

from src import const, orion
from src.waypoint import Waypoint
from src.token import Token, TokenMode
from src.caller import Caller
from src.utils import flatten
from src.mongo_lock import MongoThrottling, MongoLockError

logger = getLogger(__name__)


class CommonMixin:
    _waypoint = None

    @classmethod
    def waypoint(cls):
        if cls._waypoint is None:
            cls._waypoint = Waypoint()
            logger.debug('waypoint created')
        return cls._waypoint

    def check_mode(self, robot_id):
        if self.__check_navi(robot_id):
            abort(423, {
                'message': f'robot({robot_id}) is navigating now',
                'id': robot_id,
            })

    def __check_navi(self, robot_id):
        current_mode = orion.get_entity(
            const.FIWARE_SERVICE,
            const.DELIVERY_ROBOT_SERVICEPATH,
            const.DELIVERY_ROBOT_TYPE,
            robot_id)['mode']['value']

        return current_mode == const.MODE_NAVI

    def check_working(self, robot_id):
        remaining_waypoints_list = self.get_remaining_waypoints_list(robot_id)
        return isinstance(remaining_waypoints_list, list) and len(remaining_waypoints_list) != 0

    def get_remaining_waypoints_list(self, robot_id):
        return orion.get_entity(
            const.FIWARE_SERVICE,
            const.DELIVERY_ROBOT_SERVICEPATH,
            const.DELIVERY_ROBOT_TYPE,
            robot_id)['remaining_waypoints_list']['value']

    def get_available_robot(self):
        for robot_id in const.DELIVERY_ROBOT_LIST:
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
                    const.FIWARE_SERVICE,
                    const.DELIVERY_ROBOT_SERVICEPATH,
                    const.DELIVERY_ROBOT_TYPE,
                    robot_id)
            navigating_waypoints = robot_entity['navigating_waypoints']['value']
            order = robot_entity['order']['value']

            if not (isinstance(navigating_waypoints, dict) and 'to' in navigating_waypoints and isinstance(order, dict)
                    and 'source' in order and 'destination' in order and 'via' in order and isinstance(order['via'], list)):
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
                        logger.warning(f'unkown caller (estimate "state" as const.STATE_PICKING), {e}')
                        return const.STATE_PICKING
                elif to in order['via']:
                    return const.STATE_PICKING
                else:
                    return const.STATE_MOVING

    def get_destination_id(self, robot_id):
        navigating_waypoints = orion.get_entity(
            const.FIWARE_SERVICE,
            const.DELIVERY_ROBOT_SERVICEPATH,
            const.DELIVERY_ROBOT_TYPE,
            robot_id)['navigating_waypoints']['value']
        if not isinstance(navigating_waypoints, dict) or 'destination' not in navigating_waypoints:
            return ''
        else:
            return navigating_waypoints['destination']

    def get_destination_name(self, robot_id):
        navigating_waypoints_to = self.get_destination_id(robot_id)
        if navigating_waypoints_to == '':
            return ''

        destination = orion.get_entity(
            const.FIWARE_SERVICE,
            const.DELIVERY_ROBOT_SERVICEPATH,
            const.PLACE_TYPE,
            navigating_waypoints_to)
        if not isinstance(destination, dict) or 'name' not in destination:
            return ''

        return destination['name']['value']

    def move_robot(self, robot_id, cmd_waypoints, navigating_waypoints,
                   remaining_waypoints_list=None, current_routes=None, order=None, caller=None):

        def _move(cmd):
            payload = orion.make_delivery_robot_command(cmd, cmd_waypoints, navigating_waypoints,
                                                        remaining_waypoints_list, current_routes, order, caller)
            orion.send_command(
                const.FIWARE_SERVICE,
                const.DELIVERY_ROBOT_SERVICEPATH,
                const.DELIVERY_ROBOT_TYPE,
                robot_id,
                payload
            )

            cnt = 0
            while cnt < const.MOVENEXT_WAIT_MAX_NUM:
                cnt += 1
                robot_entity = orion.get_entity(
                    const.FIWARE_SERVICE,
                    const.DELIVERY_ROBOT_SERVICEPATH,
                    const.DELIVERY_ROBOT_TYPE,
                    robot_id)
                if robot_entity['send_cmd_status']['value'] == 'OK':
                    break
                sleep(const.MOVENEXT_WAIT_MSEC / 1000.0)
            else:
                msg = f'send_cmd_status still pending, robot_id={robot_id}, ' \
                    f'wait_msec={const.MOVENEXT_WAIT_MSEC}, wait_count={cnt}'
                logger.error(msg)
                abort(500, {
                    'message': msg
                })

            cmd_info = robot_entity['send_cmd_info']['value']
            if not (isinstance(cmd_info, dict) and 'result' in cmd_info):
                msg = f'invalid send_cmd_info, {cmd_info}'
                logger.error(msg)
                abort(500, {
                    'message': msg,
                })
            if cmd_info['result'] not in ['ack', 'ignore']:
                msg = f'move robot error, robot_id={robot_id}, errors="{cmd_info["errors"] if "errors" in cmd_info else ""}"'
                logger.error(msg)
                abort(500, {
                    'message': msg,
                })
            return cmd_info['result']

        result = _move('navi')
        logger.info(f'send "navi" command to robot({robot_id}), result={result}')
        if result == 'ignore':
            result2 = _move('refresh')
            logger.info(f'send "refresh" command to robot({robot_id}), result={result2}')
            if result2 != 'ack':
                msg = f'cannot move robot({robot_id}) to "{navigating_waypoints["to"]}" using "navi" and "refresh", ' \
                    f'navi result={result} refresh result={result2}'
                logger.error(msg)
                abort(500, {
                    'message': msg,
                })

        logger.info(f'move robot({robot_id}) to "{navigating_waypoints["to"]}" (waypoints={navigating_waypoints["waypoints"]}, '
                    f'order={order}, caller={caller}')

    def move_next(self, robot_id, check=True):
        if check:
            self.check_mode(robot_id)

        remaining_waypoints_list = self.get_remaining_waypoints_list(robot_id)
        if not isinstance(remaining_waypoints_list, list) or len(remaining_waypoints_list) == 0:
            abort(412, {
                'message': f'no remaining waypoints for robot({robot_id})',
                'id': robot_id,
            })

        head, *tail = remaining_waypoints_list
        self.move_robot(robot_id, head['waypoints'], head, tail)


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

        routes, waypoints_list, order = ShipmentAPI.waypoint().estimate_routes(shipment_list, available_robot['id'])
        if not(isinstance(waypoints_list, list) and len(waypoints_list) > 0):
            return jsonify({'result': 'ignore',
                            'message': 'no available waypoints_list'}), 200

        head, *tail = waypoints_list

        self.move_robot(available_robot['id'], head['waypoints'], head, tail, routes, order, caller)

        return jsonify({'result': 'success',
                        'delivery_robot': available_robot,
                        'order': order,
                        'caller': caller.value}), 201


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
            const.FIWARE_SERVICE,
            const.DELIVERY_ROBOT_SERVICEPATH,
            const.DELIVERY_ROBOT_TYPE,
            robot_id,
            payload
        )
        logger.info(f'send emergency command ("stop") to robot({robot_id})')

        return jsonify({'result': 'success'}), 200


class RobotNotificationAPI(CommonMixin, MethodView):
    NAME = 'robotnotificationapi'

    def post(self):
        logger.debug(f'RobotNotificationAPI.post')
        ignored_data = []
        processed_data = []

        for data in request.json['data']:
            robot_id = data['id']
            next_mode = data['mode']['value']
            time = dateutil.parser.parse(data['time']['value'])

            try:
                MongoThrottling.lock(robot_id, time)
                robot_entity = orion.get_entity(
                    const.FIWARE_SERVICE,
                    const.DELIVERY_ROBOT_SERVICEPATH,
                    const.DELIVERY_ROBOT_TYPE,
                    robot_id)

                next_state = self.calc_state(next_mode == const.MODE_NAVI, robot_id, robot_entity)
                current_mode = robot_entity['current_mode']['value']
                current_state = robot_entity['current_state']['value']
                last_processed_time = dateutil.parser.parse(robot_entity['last_processed_time']['value'])
                ui_id = const.ID_TABLE[robot_id]

                payload = orion.make_updatelastprocessedtime_command(time)
                orion.send_command(
                    const.FIWARE_SERVICE,
                    const.DELIVERY_ROBOT_SERVICEPATH,
                    const.DELIVERY_ROBOT_TYPE,
                    robot_id,
                    payload)
                logger.debug(f'update robot last_processed_time, robot_id={robot_id}, '
                             f'time={time}, last_processed_time={last_processed_time}')

                if next_mode != current_mode:
                    payload = orion.make_updatemode_command(next_mode)
                    orion.send_command(
                        const.FIWARE_SERVICE,
                        const.DELIVERY_ROBOT_SERVICEPATH,
                        const.DELIVERY_ROBOT_TYPE,
                        robot_id,
                        payload)
                    logger.info(f'update robot state, robot_id={robot_id}, '
                                f'current_mode={current_mode}, next_mode={next_mode}')

                    self._action(robot_id, ui_id, robot_entity, next_mode)
                    self._send_state(robot_id, ui_id, next_state, current_state)
                    processed_data.append(data)
                else:
                    logger.debug(f'ignore notification, next_mode={next_mode} current_mode={current_mode}')
                    ignored_data.append(data)
            except MongoLockError as e:
                logger.warning(str(e))
                ignored_data.append(data)

        logger.debug(f'processed_data = {processed_data}, ignored_data = {ignored_data}')
        return jsonify({'result': 'success', 'processed_data': processed_data, 'ignored_data': ignored_data}), 200

    def _action(self, robot_id, ui_id, robot_entity, next_mode):
        if next_mode == const.MODE_STANDBY:
            nws = robot_entity['navigating_waypoints']['value']

            if isinstance(nws, dict) and nws and 'action' in nws \
                    and 'func' in nws['action'] and nws['action']['func'] \
                    and 'token' in nws['action'] and nws['action']['token'] and isinstance(nws['action']['token'], str) \
                    and 'waiting_route' in nws['action']:
                func = nws['action']['func']
                token = Token.get(nws['action']['token'])
                waiting_route = nws['action']['waiting_route']
                if func == 'lock':
                    has_lock = token.get_lock(robot_id)
                    if has_lock:
                        self.move_next(robot_id, check=False)
                        self._send_token_info(ui_id, token, TokenMode.LOCK)
                    else:
                        if waiting_route:
                            self._take_refuge(robot_id, waiting_route)
                        self._send_token_info(ui_id, token, TokenMode.SUSPEND)
                elif func == 'release':
                    new_owner_id = token.release_lock(robot_id)
                    self.move_next(robot_id, check=False)
                    self._send_token_info(ui_id, token, TokenMode.RELEASE)
                    if new_owner_id:
                        self.move_next(new_owner_id, check=False)
                        self._send_token_info(const.ID_TABLE[new_owner_id], token, TokenMode.RESUME)
                        self._send_token_info(const.ID_TABLE[new_owner_id], token, TokenMode.LOCK)

    def _send_state(self, robot_id, ui_id, next_state, current_state):
        if next_state != current_state:
            payload = orion.make_updatestate_command(next_state)
            orion.send_command(
                const.FIWARE_SERVICE,
                const.DELIVERY_ROBOT_SERVICEPATH,
                const.DELIVERY_ROBOT_TYPE,
                robot_id,
                payload)

            destination = self.get_destination_name(robot_id)
            payload = orion.make_robotui_sendstate_command(next_state, destination)
            orion.send_command(
                const.FIWARE_SERVICE,
                const.ROBOT_UI_SERVICEPATH,
                const.ROBOT_UI_TYPE,
                ui_id,
                payload)
            logger.info(f'publish new state to robot ui({ui_id}), '
                        f'current_state={current_state}, next_state={next_state}, destination={destination}')

    def _send_token_info(self, ui_id, token, mode):
        payload = orion.make_robotui_sendtokeninfo_command(token, mode)
        orion.send_command(
            const.FIWARE_SERVICE,
            const.ROBOT_UI_SERVICEPATH,
            const.ROBOT_UI_TYPE,
            ui_id,
            payload)
        logger.info(f'publish new token_info to robot ui({ui_id}), token={token}, mode={mode}, '
                    f'lock_owner_id={token.lock_owner_id}, prev_owner_id={token.prev_owner_id}')

    def _take_refuge(self, robot_id, waiting_route):
        places = RobotNotificationAPI.waypoint().get_places([flatten([waiting_route['via'], waiting_route['to']])])
        waypoints = RobotNotificationAPI.waypoint().get_waypoints(
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
        self.move_robot(robot_id, waypoints, navigating_waypoints)
        logger.info(f'take refuge a robot({robot_id}) in "{waiting_route["to"]}"')
