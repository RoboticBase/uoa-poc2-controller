import json
import importlib
from unittest.mock import call

import dateutil.parser

import pytest
import lazy_import

api = lazy_import.lazy_module('src.api')
caller = lazy_import.lazy_module('src.caller')
const = lazy_import.lazy_module('src.const')


@pytest.fixture
def mocked_api(mocker):
    api.orion = mocker.MagicMock()
    api.Waypoint = mocker.MagicMock()
    api.MongoThrottling = mocker.MagicMock()
    api.Token = mocker.MagicMock()
    yield api
    importlib.reload(api)


class TestShipmentAPI:

    @pytest.mark.parametrize('robot_data, available_robot_id, called_robot_id', [
        ({'robot_01': {'mode': ' ', 'rwl': []}, 'robot_02': {'mode': ' ', 'rwl': []}},
         'robot_01', ['robot_01', 'robot_01', 'robot_01']),
        ({'robot_01': {'mode': 'standby', 'rwl': []}, 'robot_02': {'mode': ' ', 'rwl': []}},
         'robot_01', ['robot_01', 'robot_01', 'robot_01']),
        ({'robot_01': {'mode': 'error', 'rwl': []}, 'robot_02': {'mode': ' ', 'rwl': []}},
         'robot_01', ['robot_01', 'robot_01', 'robot_01']),
        ({'robot_01': {'mode': ' ', 'rwl': None}, 'robot_02': {'mode': ' ', 'rwl': []}},
         'robot_01', ['robot_01', 'robot_01', 'robot_01']),
        ({'robot_01': {'mode': ' ', 'rwl': 0}, 'robot_02': {'mode': ' ', 'rwl': []}},
         'robot_01', ['robot_01', 'robot_01', 'robot_01']),
        ({'robot_01': {'mode': ' ', 'rwl': 'dummy'}, 'robot_02': {'mode': ' ', 'rwl': []}},
         'robot_01', ['robot_01', 'robot_01', 'robot_01']),
        ({'robot_01': {'mode': 'navi', 'rwl': []}, 'robot_02': {'mode': ' ', 'rwl': []}},
         'robot_02', ['robot_01', 'robot_02', 'robot_02', 'robot_02']),
        ({'robot_01': {'mode': ' ', 'rwl': ['dummy']}, 'robot_02': {'mode': ' ', 'rwl': []}},
         'robot_02', ['robot_01', 'robot_01', 'robot_02', 'robot_02', 'robot_02']),
    ])
    @pytest.mark.parametrize('waypoints_list', [
        [
            {
                'to': 'E_id', 'destination': 'dest_id', 'action': 'action_0',
                'waypoints': [
                    {'point': 'pC', 'angle': None}, {'point': 'pD', 'angle': None}, {'point': 'pE', 'angle': 'aE'},
                ]
            },
        ],
        [
            {
                'to': 'E_id', 'destination': 'dest_id', 'action': 'action_0',
                'waypoints': [
                    {'point': 'pC', 'angle': None}, {'point': 'pD', 'angle': None}, {'point': 'pE', 'angle': 'aE'},
                ]
            },
            {
                'to': 'F_id', 'destination': 'dest2_id', 'action': 'action_1',
                'waypoints': [
                    {'point': 'pF', 'angle': 'aF'},
                ]
            },
        ]
    ])
    @pytest.mark.parametrize('update_caller, caller_value', [
        ({'caller': 'zaico-extensions'}, 'ordering'),
        ({'caller': ''}, 'warehouse'),
        ({'caller': 0}, 'warehouse'),
        ({}, 'warehouse'),
    ])
    def test_success(self, app, mocked_api,
                     robot_data, available_robot_id, called_robot_id,
                     waypoints_list,
                     update_caller, caller_value):
        shipment_list = {}
        shipment_list.update(update_caller)

        def get_entity(fs, fsp, t, id):
            return {
                'mode': {
                    'value': robot_data[id]['mode'],
                },
                'remaining_waypoints_list': {
                    'value': robot_data[id]['rwl'],
                },
                'send_cmd_status': {
                    'value': 'OK',
                },
                'send_cmd_info': {
                    'value': {
                        'result': 'ack'
                    }
                }
            }
        mocked_api.orion.get_entity.side_effect = get_entity
        mocked_api.orion.make_delivery_robot_command.return_value = 'make_delivery_robot_command_return_value'

        routes = [{'from': 'B_id', 'via': ['C_id', 'D_id'], 'to': 'E_id', 'destination': 'dest_id', 'action': 'action_0'}]
        order = {'source': 'src', 'via': ['A_id'], 'destination': 'dest_id'}

        mocked_api.Waypoint.return_value.estimate_routes.return_value = (routes, waypoints_list, order)

        response = app.test_client().post('/api/v1/shipments/', content_type='application/json', data=json.dumps(shipment_list))
        assert response.status_code == 201
        assert response.json == {
            'result': 'success',
            'delivery_robot': {'id': available_robot_id},
            'order': order,
            'caller': caller_value,
        }

        assert mocked_api.orion.get_entity.call_count == len(called_robot_id)
        for i, rid in enumerate(called_robot_id):
            assert mocked_api.orion.get_entity.call_args_list[i] == call(const.FIWARE_SERVICE,
                                                                         const.DELIVERY_ROBOT_SERVICEPATH,
                                                                         const.DELIVERY_ROBOT_TYPE,
                                                                         rid)
        assert mocked_api.orion.make_delivery_robot_command.call_count == 1
        rwl = [] if len(waypoints_list) == 1 else [waypoints_list[1]]
        assert mocked_api.orion.make_delivery_robot_command.call_args == call('navi',
                                                                              waypoints_list[0]['waypoints'],
                                                                              waypoints_list[0],
                                                                              rwl,
                                                                              routes,
                                                                              order,
                                                                              caller.Caller.value_of(caller_value))
        assert mocked_api.orion.send_command.call_count == 1
        assert mocked_api.orion.send_command.call_args == call(const.FIWARE_SERVICE,
                                                               const.DELIVERY_ROBOT_SERVICEPATH,
                                                               const.DELIVERY_ROBOT_TYPE,
                                                               available_robot_id,
                                                               'make_delivery_robot_command_return_value')
        assert mocked_api.CommonMixin.waypoint().estimate_routes.call_count == 1
        assert mocked_api.CommonMixin.waypoint().estimate_routes.call_args == call(shipment_list, available_robot_id)
        assert mocked_api.orion.make_emergency_command.call_count == 0
        assert mocked_api.orion.make_updatelastprocessedtime_command.call_count == 0
        assert mocked_api.orion.make_updatemode_command.call_count == 0
        assert mocked_api.orion.make_updatestate_command.call_count == 0
        assert mocked_api.orion.make_robotui_sendstate_command.call_count == 0
        assert mocked_api.orion.make_robotui_sendtokeninfo_command.call_count == 0
        assert mocked_api.CommonMixin.waypoint().get_places.call_count == 0
        assert mocked_api.CommonMixin.waypoint().get_waypoints.call_count == 0
        assert mocked_api.Token.get.call_count == 0
        assert mocked_api.Token.get.return_value.get_lock.call_count == 0
        assert mocked_api.MongoThrottling.lock.call_count == 0

    @pytest.mark.parametrize('robot_01_data, robot_01_count', [
        ({'mode': 'navi', 'rwl': []}, 1),
        ({'mode': 'standby', 'rwl': ['dummy']}, 2),
        ({'mode': 'navi', 'rwl': ['dummy']}, 1),
    ])
    @pytest.mark.parametrize('robot_02_data, robot_02_count', [
        ({'mode': 'navi', 'rwl': []}, 1),
        ({'mode': 'standby', 'rwl': ['dummy']}, 2),
        ({'mode': 'navi', 'rwl': ['dummy']}, 1),
    ])
    def test_no_available_robot(self, app, mocked_api, robot_01_data, robot_01_count, robot_02_data, robot_02_count):
        shipment_list = {}

        def get_entity(fs, fsp, t, id):
            d = robot_01_data if id == 'robot_01' else robot_02_data
            return {
                'mode': {
                    'value': d['mode'],
                },
                'remaining_waypoints_list': {
                    'value': d['rwl'],
                },
                'send_cmd_status': {
                    'value': 'OK',
                },
                'send_cmd_info': {
                    'value': {
                        'result': 'ack'
                    }
                }
            }
        mocked_api.orion.get_entity.side_effect = get_entity

        response = app.test_client().post('/api/v1/shipments/', content_type='application/json', data=json.dumps(shipment_list))
        assert response.status_code == 422
        assert response.json == {
            'message': 'no available robot'
        }

        assert mocked_api.orion.get_entity.call_count == robot_01_count + robot_02_count

        for i in range(robot_01_count):
            assert mocked_api.orion.get_entity.call_args_list[i] == call(const.FIWARE_SERVICE,
                                                                         const.DELIVERY_ROBOT_SERVICEPATH,
                                                                         const.DELIVERY_ROBOT_TYPE,
                                                                         'robot_01')
        for i in range(robot_02_count):
            assert mocked_api.orion.get_entity.call_args_list[i + robot_01_count] == call(const.FIWARE_SERVICE,
                                                                                          const.DELIVERY_ROBOT_SERVICEPATH,
                                                                                          const.DELIVERY_ROBOT_TYPE,
                                                                                          'robot_02')
        assert mocked_api.orion.make_delivery_robot_command.call_count == 0
        assert mocked_api.orion.send_command.call_count == 0
        assert mocked_api.CommonMixin.waypoint().estimate_routes.call_count == 0
        assert mocked_api.orion.make_emergency_command.call_count == 0
        assert mocked_api.orion.make_updatelastprocessedtime_command.call_count == 0
        assert mocked_api.orion.make_updatemode_command.call_count == 0
        assert mocked_api.orion.make_updatestate_command.call_count == 0
        assert mocked_api.orion.make_robotui_sendstate_command.call_count == 0
        assert mocked_api.orion.make_robotui_sendtokeninfo_command.call_count == 0
        assert mocked_api.CommonMixin.waypoint().get_places.call_count == 0
        assert mocked_api.CommonMixin.waypoint().get_waypoints.call_count == 0
        assert mocked_api.Token.get.call_count == 0
        assert mocked_api.Token.get.return_value.get_lock.call_count == 0
        assert mocked_api.MongoThrottling.lock.call_count == 0

    @pytest.mark.parametrize('waypoints_list', [
        [], {}, {'a': 1}, tuple([1]), set([1, 2]), 'dummy', 0, 1e-1, None
    ])
    def test_no_waypoints_list(self, app, mocked_api, waypoints_list):
        shipment_list = {}

        def get_entity(fs, fsp, t, id):
            return {
                'mode': {
                    'value': 'standby'
                },
                'remaining_waypoints_list': {
                    'value': [],
                },
                'send_cmd_status': {
                    'value': 'OK',
                },
                'send_cmd_info': {
                    'value': {
                        'result': 'ack'
                    }
                }
            }
        mocked_api.orion.get_entity.side_effect = get_entity
        mocked_api.orion.make_delivery_robot_command.return_value = 'make_delivery_robot_command_return_value'

        routes = [{'from': 'B_id', 'via': ['C_id', 'D_id'], 'to': 'E_id', 'destination': 'dest_id', 'action': 'action_0'}]
        order = {'source': 'src', 'via': ['A_id'], 'destination': 'dest_id'}

        mocked_api.Waypoint.return_value.estimate_routes.return_value = (routes, waypoints_list, order)

        response = app.test_client().post('/api/v1/shipments/', content_type='application/json', data=json.dumps(shipment_list))
        assert response.status_code == 200
        assert response.json == {
            'result': 'ignore',
            'message': 'no available waypoints_list',
        }
        assert mocked_api.orion.get_entity.call_count == 2
        for i in range(2):
            assert mocked_api.orion.get_entity.call_args_list[i] == call(const.FIWARE_SERVICE,
                                                                         const.DELIVERY_ROBOT_SERVICEPATH,
                                                                         const.DELIVERY_ROBOT_TYPE,
                                                                         'robot_01')
        assert mocked_api.orion.make_delivery_robot_command.call_count == 0
        assert mocked_api.orion.send_command.call_count == 0
        assert mocked_api.CommonMixin.waypoint().estimate_routes.call_count == 1
        assert mocked_api.CommonMixin.waypoint().estimate_routes.call_args == call(shipment_list, 'robot_01')
        assert mocked_api.orion.make_emergency_command.call_count == 0
        assert mocked_api.orion.make_updatelastprocessedtime_command.call_count == 0
        assert mocked_api.orion.make_updatemode_command.call_count == 0
        assert mocked_api.orion.make_updatestate_command.call_count == 0
        assert mocked_api.orion.make_robotui_sendstate_command.call_count == 0
        assert mocked_api.orion.make_robotui_sendtokeninfo_command.call_count == 0
        assert mocked_api.CommonMixin.waypoint().get_places.call_count == 0
        assert mocked_api.CommonMixin.waypoint().get_waypoints.call_count == 0
        assert mocked_api.Token.get.call_count == 0
        assert mocked_api.Token.get.return_value.get_lock.call_count == 0
        assert mocked_api.MongoThrottling.lock.call_count == 0

    def test_send_cmd_status_pending(self, app, mocked_api):
        shipment_list = {}

        def get_entity(fs, fsp, t, id):
            return {
                'mode': {
                    'value': 'standby'
                },
                'remaining_waypoints_list': {
                    'value': [],
                },
                'send_cmd_status': {
                    'value': 'pending',
                },
                'send_cmd_info': {
                    'value': {
                        'result': 'ack'
                    }
                }
            }
        mocked_api.orion.get_entity.side_effect = get_entity
        mocked_api.orion.make_delivery_robot_command.return_value = 'make_delivery_robot_command_return_value'

        routes = [{'from': 'B_id', 'via': ['C_id', 'D_id'], 'to': 'E_id', 'destination': 'dest_id', 'action': 'action_0'}]
        waypoints_list = [
            {
                'to': 'E_id', 'destination': 'dest_id', 'action': 'action_0',
                'waypoints': [
                    {'point': 'pC', 'angle': None}, {'point': 'pD', 'angle': None}, {'point': 'pE', 'angle': 'aE'},
                ]
            },
        ]
        order = {'source': 'src', 'via': ['A_id'], 'destination': 'dest_id'}
        mocked_api.Waypoint.return_value.estimate_routes.return_value = (routes, waypoints_list, order)

        response = app.test_client().post('/api/v1/shipments/', content_type='application/json', data=json.dumps(shipment_list))
        assert response.status_code == 500
        assert response.json == {
            'message': 'send_cmd_status still pending, robot_id=robot_01, wait_msec=10, wait_count=3',
        }
        assert mocked_api.orion.get_entity.call_count == 5
        for i in range(5):
            assert mocked_api.orion.get_entity.call_args_list[i] == call(const.FIWARE_SERVICE,
                                                                         const.DELIVERY_ROBOT_SERVICEPATH,
                                                                         const.DELIVERY_ROBOT_TYPE,
                                                                         'robot_01')
        assert mocked_api.orion.make_delivery_robot_command.call_count == 1
        assert mocked_api.orion.make_delivery_robot_command.call_args == call('navi',
                                                                              waypoints_list[0]['waypoints'],
                                                                              waypoints_list[0],
                                                                              [],
                                                                              routes,
                                                                              order,
                                                                              caller.Caller.WAREHOUSE)
        assert mocked_api.orion.send_command.call_count == 1
        assert mocked_api.orion.send_command.call_args == call(const.FIWARE_SERVICE,
                                                               const.DELIVERY_ROBOT_SERVICEPATH,
                                                               const.DELIVERY_ROBOT_TYPE,
                                                               'robot_01',
                                                               'make_delivery_robot_command_return_value')
        assert mocked_api.CommonMixin.waypoint().estimate_routes.call_count == 1
        assert mocked_api.CommonMixin.waypoint().estimate_routes.call_args == call(shipment_list, 'robot_01')
        assert mocked_api.orion.make_emergency_command.call_count == 0
        assert mocked_api.orion.make_updatelastprocessedtime_command.call_count == 0
        assert mocked_api.orion.make_updatemode_command.call_count == 0
        assert mocked_api.orion.make_updatestate_command.call_count == 0
        assert mocked_api.orion.make_robotui_sendstate_command.call_count == 0
        assert mocked_api.orion.make_robotui_sendtokeninfo_command.call_count == 0
        assert mocked_api.CommonMixin.waypoint().get_places.call_count == 0
        assert mocked_api.CommonMixin.waypoint().get_waypoints.call_count == 0
        assert mocked_api.Token.get.call_count == 0
        assert mocked_api.Token.get.return_value.get_lock.call_count == 0
        assert mocked_api.MongoThrottling.lock.call_count == 0

    @pytest.mark.parametrize('send_cmd_info_value, errmsg', [
        ({'result': 'error', 'errors': 'dummy error'}, 'move robot error, robot_id=robot_01, errors="dummy error"'),
        ({'result': 'error'}, 'move robot error, robot_id=robot_01, errors=""'),
        ({'result': 0}, 'move robot error, robot_id=robot_01, errors=""'),
        ({'result': 1e-1}, 'move robot error, robot_id=robot_01, errors=""'),
        ({'result': True}, 'move robot error, robot_id=robot_01, errors=""'),
        ({'result': []}, 'move robot error, robot_id=robot_01, errors=""'),
        ({'result': ['a', 1]}, 'move robot error, robot_id=robot_01, errors=""'),
        ({'result': {}}, 'move robot error, robot_id=robot_01, errors=""'),
        ({'result': {'a': 1}}, 'move robot error, robot_id=robot_01, errors=""'),
        ({'result': tuple(['a', 1])}, 'move robot error, robot_id=robot_01, errors=""'),
        ({'result': set(['a', 1])}, 'move robot error, robot_id=robot_01, errors=""'),
        ({'result': caller.Caller.WAREHOUSE}, 'move robot error, robot_id=robot_01, errors=""'),
        ({'result': None}, 'move robot error, robot_id=robot_01, errors=""'),
        ({'errors': 'dummy error'}, "invalid send_cmd_info, {'errors': 'dummy error'}"),
        ({}, "invalid send_cmd_info, {}"),
        ('dummy', "invalid send_cmd_info, dummy"),
        (0, "invalid send_cmd_info, 0"),
        (1e-1, "invalid send_cmd_info, 0.1"),
        (True, "invalid send_cmd_info, True"),
        ([], "invalid send_cmd_info, []"),
        (tuple([]), "invalid send_cmd_info, ()"),
        (set([]), "invalid send_cmd_info, set()"),
        (caller.Caller.WAREHOUSE, "invalid send_cmd_info, warehouse"),
        (None, "invalid send_cmd_info, None"),
    ])
    def test_send_cmd_result_invalid(self, app, mocked_api, send_cmd_info_value, errmsg):
        shipment_list = {}

        def get_entity(fs, fsp, t, id):
            return {
                'mode': {
                    'value': 'standby'
                },
                'remaining_waypoints_list': {
                    'value': [],
                },
                'send_cmd_status': {
                    'value': 'OK',
                },
                'send_cmd_info': {
                    'value': send_cmd_info_value,
                },
            }
        mocked_api.orion.get_entity.side_effect = get_entity
        mocked_api.orion.make_delivery_robot_command.return_value = 'make_delivery_robot_command_return_value'

        routes = [{'from': 'B_id', 'via': ['C_id', 'D_id'], 'to': 'E_id', 'destination': 'dest_id', 'action': 'action_0'}]
        waypoints_list = [
            {
                'to': 'E_id', 'destination': 'dest_id', 'action': 'action_0',
                'waypoints': [
                    {'point': 'pC', 'angle': None}, {'point': 'pD', 'angle': None}, {'point': 'pE', 'angle': 'aE'},
                ]
            },
        ]
        order = {'source': 'src', 'via': ['A_id'], 'destination': 'dest_id'}
        mocked_api.Waypoint.return_value.estimate_routes.return_value = (routes, waypoints_list, order)

        response = app.test_client().post('/api/v1/shipments/', content_type='application/json', data=json.dumps(shipment_list))
        assert response.status_code == 500
        assert response.json == {
            'message': errmsg,
        }
        assert mocked_api.orion.get_entity.call_count == 3
        for i in range(3):
            assert mocked_api.orion.get_entity.call_args_list[i] == call(const.FIWARE_SERVICE,
                                                                         const.DELIVERY_ROBOT_SERVICEPATH,
                                                                         const.DELIVERY_ROBOT_TYPE,
                                                                         'robot_01')
        assert mocked_api.orion.make_delivery_robot_command.call_count == 1
        assert mocked_api.orion.make_delivery_robot_command.call_args == call('navi',
                                                                              waypoints_list[0]['waypoints'],
                                                                              waypoints_list[0],
                                                                              [],
                                                                              routes,
                                                                              order,
                                                                              caller.Caller.WAREHOUSE)
        assert mocked_api.orion.send_command.call_count == 1
        assert mocked_api.orion.send_command.call_args == call(const.FIWARE_SERVICE,
                                                               const.DELIVERY_ROBOT_SERVICEPATH,
                                                               const.DELIVERY_ROBOT_TYPE,
                                                               'robot_01',
                                                               'make_delivery_robot_command_return_value')
        assert mocked_api.CommonMixin.waypoint().estimate_routes.call_count == 1
        assert mocked_api.CommonMixin.waypoint().estimate_routes.call_args == call(shipment_list, 'robot_01')
        assert mocked_api.orion.make_emergency_command.call_count == 0
        assert mocked_api.orion.make_updatelastprocessedtime_command.call_count == 0
        assert mocked_api.orion.make_updatemode_command.call_count == 0
        assert mocked_api.orion.make_updatestate_command.call_count == 0
        assert mocked_api.orion.make_robotui_sendstate_command.call_count == 0
        assert mocked_api.orion.make_robotui_sendtokeninfo_command.call_count == 0
        assert mocked_api.CommonMixin.waypoint().get_places.call_count == 0
        assert mocked_api.CommonMixin.waypoint().get_waypoints.call_count == 0
        assert mocked_api.Token.get.call_count == 0
        assert mocked_api.Token.get.return_value.get_lock.call_count == 0
        assert mocked_api.MongoThrottling.lock.call_count == 0

    def test_send_cmd_result_navi_ignore_refresh_ack(self, app, mocked_api):
        shipment_list = {}

        def get_entity():
            c = 0

            def _result(fs, fsp, t, id):
                nonlocal c
                result = None
                if c < 3:
                    result = {
                        'mode': {
                            'value': 'standby'
                        },
                        'remaining_waypoints_list': {
                            'value': [],
                        },
                        'send_cmd_status': {
                            'value': 'OK',
                        },
                        'send_cmd_info': {
                            'value': {
                                'result': 'ignore'
                            }
                        }
                    }
                else:
                    result = {
                        'mode': {
                            'value': 'standby'
                        },
                        'remaining_waypoints_list': {
                            'value': [],
                        },
                        'send_cmd_status': {
                            'value': 'OK',
                        },
                        'send_cmd_info': {
                            'value': {
                                'result': 'ack'
                            }
                        }
                    }
                c += 1
                return result
            return _result

        mocked_api.orion.get_entity.side_effect = get_entity()
        mocked_api.orion.make_delivery_robot_command.return_value = 'make_delivery_robot_command_return_value'

        routes = [{'from': 'B_id', 'via': ['C_id', 'D_id'], 'to': 'E_id', 'destination': 'dest_id', 'action': 'action_0'}]
        waypoints_list = [
            {
                'to': 'E_id', 'destination': 'dest_id', 'action': 'action_0',
                'waypoints': [
                    {'point': 'pC', 'angle': None}, {'point': 'pD', 'angle': None}, {'point': 'pE', 'angle': 'aE'},
                ]
            },
        ]
        order = {'source': 'src', 'via': ['A_id'], 'destination': 'dest_id'}
        mocked_api.Waypoint.return_value.estimate_routes.return_value = (routes, waypoints_list, order)

        response = app.test_client().post('/api/v1/shipments/', content_type='application/json', data=json.dumps(shipment_list))
        assert response.status_code == 201
        assert response.json == {
            'result': 'success',
            'delivery_robot': {'id': 'robot_01'},
            'order': order,
            'caller': 'warehouse',
        }
        assert mocked_api.orion.get_entity.call_count == 4
        for i in range(4):
            assert mocked_api.orion.get_entity.call_args_list[i] == call(const.FIWARE_SERVICE,
                                                                         const.DELIVERY_ROBOT_SERVICEPATH,
                                                                         const.DELIVERY_ROBOT_TYPE,
                                                                         'robot_01')
        assert mocked_api.orion.make_delivery_robot_command.call_count == 2
        assert mocked_api.orion.make_delivery_robot_command.call_args_list[0] == call('navi',
                                                                                      waypoints_list[0]['waypoints'],
                                                                                      waypoints_list[0],
                                                                                      [],
                                                                                      routes,
                                                                                      order,
                                                                                      caller.Caller.WAREHOUSE)
        assert mocked_api.orion.make_delivery_robot_command.call_args_list[1] == call('refresh',
                                                                                      waypoints_list[0]['waypoints'],
                                                                                      waypoints_list[0],
                                                                                      [],
                                                                                      routes,
                                                                                      order,
                                                                                      caller.Caller.WAREHOUSE)
        assert mocked_api.orion.send_command.call_count == 2
        for i in range(2):
            assert mocked_api.orion.send_command.call_args_list[i] == call(const.FIWARE_SERVICE,
                                                                           const.DELIVERY_ROBOT_SERVICEPATH,
                                                                           const.DELIVERY_ROBOT_TYPE,
                                                                           'robot_01',
                                                                           'make_delivery_robot_command_return_value')
        assert mocked_api.CommonMixin.waypoint().estimate_routes.call_count == 1
        assert mocked_api.CommonMixin.waypoint().estimate_routes.call_args == call(shipment_list, 'robot_01')
        assert mocked_api.orion.make_emergency_command.call_count == 0
        assert mocked_api.orion.make_updatelastprocessedtime_command.call_count == 0
        assert mocked_api.orion.make_updatemode_command.call_count == 0
        assert mocked_api.orion.make_updatestate_command.call_count == 0
        assert mocked_api.orion.make_robotui_sendstate_command.call_count == 0
        assert mocked_api.orion.make_robotui_sendtokeninfo_command.call_count == 0
        assert mocked_api.CommonMixin.waypoint().get_places.call_count == 0
        assert mocked_api.CommonMixin.waypoint().get_waypoints.call_count == 0
        assert mocked_api.Token.get.call_count == 0
        assert mocked_api.Token.get.return_value.get_lock.call_count == 0
        assert mocked_api.MongoThrottling.lock.call_count == 0

    def test_send_cmd_result_navi_ignore_refresh_ignore(self, app, mocked_api):
        shipment_list = {}

        def get_entity(fs, fsp, t, id):
            return {
                'mode': {
                    'value': 'standby'
                },
                'remaining_waypoints_list': {
                    'value': [],
                },
                'send_cmd_status': {
                    'value': 'OK',
                },
                'send_cmd_info': {
                    'value': {
                        'result': 'ignore'
                    }
                }
            }

        mocked_api.orion.get_entity.side_effect = get_entity
        mocked_api.orion.make_delivery_robot_command.return_value = 'make_delivery_robot_command_return_value'

        routes = [{'from': 'B_id', 'via': ['C_id', 'D_id'], 'to': 'E_id', 'destination': 'dest_id', 'action': 'action_0'}]
        waypoints_list = [
            {
                'to': 'E_id', 'destination': 'dest_id', 'action': 'action_0',
                'waypoints': [
                    {'point': 'pC', 'angle': None}, {'point': 'pD', 'angle': None}, {'point': 'pE', 'angle': 'aE'},
                ]
            },
        ]
        order = {'source': 'src', 'via': ['A_id'], 'destination': 'dest_id'}
        mocked_api.Waypoint.return_value.estimate_routes.return_value = (routes, waypoints_list, order)

        response = app.test_client().post('/api/v1/shipments/', content_type='application/json', data=json.dumps(shipment_list))
        assert response.status_code == 500
        assert response.json == {
            'message': 'cannot move robot(robot_01) to "E_id" using "navi" and "refresh", '
            'navi result=ignore refresh result=ignore'
        }
        assert mocked_api.orion.get_entity.call_count == 4
        for i in range(4):
            assert mocked_api.orion.get_entity.call_args_list[i] == call(const.FIWARE_SERVICE,
                                                                         const.DELIVERY_ROBOT_SERVICEPATH,
                                                                         const.DELIVERY_ROBOT_TYPE,
                                                                         'robot_01')
        assert mocked_api.orion.make_delivery_robot_command.call_count == 2
        assert mocked_api.orion.make_delivery_robot_command.call_args_list[0] == call('navi',
                                                                                      waypoints_list[0]['waypoints'],
                                                                                      waypoints_list[0],
                                                                                      [],
                                                                                      routes,
                                                                                      order,
                                                                                      caller.Caller.WAREHOUSE)
        assert mocked_api.orion.make_delivery_robot_command.call_args_list[1] == call('refresh',
                                                                                      waypoints_list[0]['waypoints'],
                                                                                      waypoints_list[0],
                                                                                      [],
                                                                                      routes,
                                                                                      order,
                                                                                      caller.Caller.WAREHOUSE)
        assert mocked_api.orion.send_command.call_count == 2
        for i in range(2):
            assert mocked_api.orion.send_command.call_args_list[i] == call(const.FIWARE_SERVICE,
                                                                           const.DELIVERY_ROBOT_SERVICEPATH,
                                                                           const.DELIVERY_ROBOT_TYPE,
                                                                           'robot_01',
                                                                           'make_delivery_robot_command_return_value')
        assert mocked_api.CommonMixin.waypoint().estimate_routes.call_count == 1
        assert mocked_api.CommonMixin.waypoint().estimate_routes.call_args == call(shipment_list, 'robot_01')
        assert mocked_api.orion.make_emergency_command.call_count == 0
        assert mocked_api.orion.make_updatelastprocessedtime_command.call_count == 0
        assert mocked_api.orion.make_updatemode_command.call_count == 0
        assert mocked_api.orion.make_updatestate_command.call_count == 0
        assert mocked_api.orion.make_robotui_sendstate_command.call_count == 0
        assert mocked_api.orion.make_robotui_sendtokeninfo_command.call_count == 0
        assert mocked_api.CommonMixin.waypoint().get_places.call_count == 0
        assert mocked_api.CommonMixin.waypoint().get_waypoints.call_count == 0
        assert mocked_api.Token.get.call_count == 0
        assert mocked_api.Token.get.return_value.get_lock.call_count == 0
        assert mocked_api.MongoThrottling.lock.call_count == 0

    @pytest.mark.parametrize('data, errmsg', [
        ('dummy', 'invalid shipment_list, dummy'),
        (0, 'invalid shipment_list, 0'),
        (1e-1, 'invalid shipment_list, 0.1'),
        (True, 'invalid shipment_list, True'),
        ([], 'invalid shipment_list, []'),
        (['a', 1], "invalid shipment_list, ['a', 1]"),
        (tuple(['a', 1]), "invalid shipment_list, ['a', 1]"),
        (None, 'invalid shipment_list, None'),
    ])
    def test_invalid_type(self, app, mocked_api, data, errmsg):
        response = app.test_client().post('/api/v1/shipments/', content_type='application/json', data=json.dumps(data))

        assert response.status_code == 400
        assert response.json == {'message': errmsg}
        assert mocked_api.orion.get_entity.call_count == 0
        assert mocked_api.orion.make_delivery_robot_command.call_count == 0
        assert mocked_api.orion.send_command.call_count == 0
        assert mocked_api.CommonMixin.waypoint().estimate_routes.call_count == 0
        assert mocked_api.orion.make_emergency_command.call_count == 0
        assert mocked_api.orion.make_updatelastprocessedtime_command.call_count == 0
        assert mocked_api.orion.make_updatemode_command.call_count == 0
        assert mocked_api.orion.make_updatestate_command.call_count == 0
        assert mocked_api.orion.make_robotui_sendstate_command.call_count == 0
        assert mocked_api.orion.make_robotui_sendtokeninfo_command.call_count == 0
        assert mocked_api.CommonMixin.waypoint().get_places.call_count == 0
        assert mocked_api.CommonMixin.waypoint().get_waypoints.call_count == 0
        assert mocked_api.Token.get.call_count == 0
        assert mocked_api.Token.get.return_value.get_lock.call_count == 0
        assert mocked_api.MongoThrottling.lock.call_count == 0


class TestRobotStateAPI:

    @pytest.mark.parametrize('navigation_waypoints_value, place_name, call_count', [
        ({'destination': 'A_id'}, 'place_A', 3),
        ({'test': 'dummy'}, '', 2),
        ({}, '', 2),
        ([], '', 2),
        (tuple([]), '', 2),
        (set([]), '', 2),
        ('dummy', '', 2),
        (0, '', 2),
        (1e-1, '', 2),
        (caller.Caller.WAREHOUSE, '', 2),
        (None, '', 2),
    ])
    def test_state_moving(self, app, mocked_api, navigation_waypoints_value, place_name, call_count):
        robot_id = 'robot_01'

        def get_entity(fs, fsp, t, id):
            if t == const.DELIVERY_ROBOT_TYPE:
                return {
                    'mode': {
                        'value': 'navi',
                    },
                    'navigating_waypoints': {
                        'value': navigation_waypoints_value,
                    }
                }
            else:
                return {
                    'name': {
                        'value': place_name
                    }
                }

        mocked_api.orion.get_entity.side_effect = get_entity

        response = app.test_client().get(f'/api/v1/robots/{robot_id}/')
        assert response.status_code == 200
        assert response.json == {'id': robot_id, 'state': const.STATE_MOVING, 'destination': place_name}

        assert mocked_api.orion.get_entity.call_count == call_count

        for i in range(2):
            assert mocked_api.orion.get_entity.call_args_list[i] == call(const.FIWARE_SERVICE,
                                                                         const.DELIVERY_ROBOT_SERVICEPATH,
                                                                         const.DELIVERY_ROBOT_TYPE,
                                                                         robot_id)
        if call_count > 2:
            assert mocked_api.orion.get_entity.call_args_list[2] == call(const.FIWARE_SERVICE,
                                                                         const.DELIVERY_ROBOT_SERVICEPATH,
                                                                         const.PLACE_TYPE,
                                                                         'A_id')
        assert mocked_api.orion.make_delivery_robot_command.call_count == 0
        assert mocked_api.orion.make_emergency_command.call_count == 0
        assert mocked_api.orion.make_updatelastprocessedtime_command.call_count == 0
        assert mocked_api.orion.make_updatemode_command.call_count == 0
        assert mocked_api.orion.make_updatestate_command.call_count == 0
        assert mocked_api.orion.make_robotui_sendstate_command.call_count == 0
        assert mocked_api.orion.make_robotui_sendtokeninfo_command.call_count == 0
        assert mocked_api.orion.send_command.call_count == 0
        assert mocked_api.CommonMixin.waypoint().estimate_routes.call_count == 0
        assert mocked_api.CommonMixin.waypoint().get_places.call_count == 0
        assert mocked_api.CommonMixin.waypoint().get_waypoints.call_count == 0
        assert mocked_api.Token.get.call_count == 0
        assert mocked_api.Token.get.return_value.get_lock.call_count == 0
        assert mocked_api.MongoThrottling.lock.call_count == 0

    @pytest.mark.parametrize('mode', [
        'standby', 'error', '', None, 0, 1e-1, True, {}, []
    ])
    @pytest.mark.parametrize('navigation_waypoints_value', [
        {'test': 'dummy'}, {}, 'dummy', 0, 1e-1, True, [], tuple([]), set([]), caller.Caller.WAREHOUSE, None
    ])
    def test_state_standby1(self, app, mocked_api, mode, navigation_waypoints_value):
        robot_id = 'robot_01'

        def get_entity(fs, fsp, t, id):
            if t == const.DELIVERY_ROBOT_TYPE:
                return {
                    'mode': {
                        'value': mode,
                    },
                    'navigating_waypoints': {
                        'value': navigation_waypoints_value,
                    },
                    'order': {
                        'value': None
                    },
                }
            else:
                return {
                    'name': {
                        'value': ''
                    }
                }

        mocked_api.orion.get_entity.side_effect = get_entity

        response = app.test_client().get(f'/api/v1/robots/{robot_id}/')
        assert response.status_code == 200
        assert response.json == {'id': robot_id, 'state': const.STATE_STANDBY, 'destination': ''}

        assert mocked_api.orion.get_entity.call_count == 3
        for i in range(3):
            assert mocked_api.orion.get_entity.call_args_list[i] == call(const.FIWARE_SERVICE,
                                                                         const.DELIVERY_ROBOT_SERVICEPATH,
                                                                         const.DELIVERY_ROBOT_TYPE,
                                                                         robot_id)
        assert mocked_api.orion.make_delivery_robot_command.call_count == 0
        assert mocked_api.orion.make_emergency_command.call_count == 0
        assert mocked_api.orion.make_updatelastprocessedtime_command.call_count == 0
        assert mocked_api.orion.make_updatemode_command.call_count == 0
        assert mocked_api.orion.make_updatestate_command.call_count == 0
        assert mocked_api.orion.make_robotui_sendstate_command.call_count == 0
        assert mocked_api.orion.make_robotui_sendtokeninfo_command.call_count == 0
        assert mocked_api.orion.send_command.call_count == 0
        assert mocked_api.CommonMixin.waypoint().estimate_routes.call_count == 0
        assert mocked_api.CommonMixin.waypoint().get_places.call_count == 0
        assert mocked_api.CommonMixin.waypoint().get_waypoints.call_count == 0
        assert mocked_api.Token.get.call_count == 0
        assert mocked_api.Token.get.return_value.get_lock.call_count == 0
        assert mocked_api.MongoThrottling.lock.call_count == 0

    @pytest.mark.parametrize('mode', [
        'standby', 'error', '', None, 0, 1e-1, True, {}, []
    ])
    @pytest.mark.parametrize('order', [
        {'source': 's', 'destination': 'd'}, {'source': 's', 'via': ['v']}, {'destination': 'd', 'via': ['v']},
        {'source': 's', 'destination': 'd', 'via': 'v'},
        {'test': 'dummy'}, {}, 'dummy', 0, 1e-1, True, [], tuple([]), set([]), caller.Caller.WAREHOUSE, None
    ])
    def test_state_standby2(self, app, mocked_api, mode, order):
        robot_id = 'robot_01'

        def get_entity(fs, fsp, t, id):
            if t == const.DELIVERY_ROBOT_TYPE:
                return {
                    'mode': {
                        'value': mode,
                    },
                    'navigating_waypoints': {
                        'value': {
                            'to': 'A_id',
                        }
                    },
                    'order': {
                        'value': order
                    },
                }
            else:
                return {
                    'name': {
                        'value': ''
                    }
                }

        mocked_api.orion.get_entity.side_effect = get_entity

        response = app.test_client().get(f'/api/v1/robots/{robot_id}/')
        assert response.status_code == 200
        assert response.json == {'id': robot_id, 'state': const.STATE_STANDBY, 'destination': ''}

        assert mocked_api.orion.get_entity.call_count == 3
        for i in range(3):
            assert mocked_api.orion.get_entity.call_args_list[i] == call(const.FIWARE_SERVICE,
                                                                         const.DELIVERY_ROBOT_SERVICEPATH,
                                                                         const.DELIVERY_ROBOT_TYPE,
                                                                         robot_id)
        assert mocked_api.orion.make_delivery_robot_command.call_count == 0
        assert mocked_api.orion.make_emergency_command.call_count == 0
        assert mocked_api.orion.make_updatelastprocessedtime_command.call_count == 0
        assert mocked_api.orion.make_updatemode_command.call_count == 0
        assert mocked_api.orion.make_updatestate_command.call_count == 0
        assert mocked_api.orion.make_robotui_sendstate_command.call_count == 0
        assert mocked_api.orion.make_robotui_sendtokeninfo_command.call_count == 0
        assert mocked_api.orion.send_command.call_count == 0
        assert mocked_api.CommonMixin.waypoint().estimate_routes.call_count == 0
        assert mocked_api.CommonMixin.waypoint().get_places.call_count == 0
        assert mocked_api.CommonMixin.waypoint().get_waypoints.call_count == 0
        assert mocked_api.Token.get.call_count == 0
        assert mocked_api.Token.get.return_value.get_lock.call_count == 0
        assert mocked_api.MongoThrottling.lock.call_count == 0

    @pytest.mark.parametrize('mode', [
        'standby', 'error', '', None, 0, 1e-1, True, {}, []
    ])
    @pytest.mark.parametrize('navigation_waypoints_value, order, place_name, state, call_count', [
        (
            {'destination': 'A_id', 'to': 'A_id'},
            {'source': 'A_id', 'via': [], 'destination': None},
            'A_id',
            'standby',
            4,
        ),
        (
            {'to': 'A_id'},
            {'source': 'A_id', 'via': [], 'destination': None},
            '',
            'standby',
            3,
        ),
        (
            {'destination': 'A_id', 'to': 'A_id'},
            {'source': None, 'via': [], 'destination': 'A_id'},
            'A_id',
            'd_p',
            4,
        ),
        (
            {'to': 'A_id'},
            {'source': None, 'via': [], 'destination': 'A_id'},
            '',
            'd_p',
            3,
        ),
        (
            {'destination': 'A_id', 'to': 'A_id'},
            {'source': None, 'via': ['A_id'], 'destination': None},
            'A_id',
            'picking',
            4,
        ),
        (
            {'to': 'A_id'},
            {'source': None, 'via': ['A_id'], 'destination': None},
            '',
            'picking',
            3,
        ),
        (
            {'destination': 'A_id', 'to': 'A_id'},
            {'source': None, 'via': [], 'destination': None},
            'A_id',
            'moving',
            4,
        ),
        (
            {'to': 'A_id'},
            {'source': None, 'via': [], 'destination': None},
            '',
            'moving',
            3,
        ),
    ])
    @pytest.mark.parametrize('c', [
        'ordering', 'warehouse', '', None, 0, 1e-1, True, {}, []
    ])
    def test_state_other(self, app, mocked_api, mode, navigation_waypoints_value, order, place_name, state, c, call_count):
        robot_id = 'robot_01'

        def get_entity(fs, fsp, t, id):
            if t == const.DELIVERY_ROBOT_TYPE:
                return {
                    'mode': {
                        'value': mode,
                    },
                    'navigating_waypoints': {
                        'value': navigation_waypoints_value,
                    },
                    'order': {
                        'value': order
                    },
                    'caller': {
                        'value': c
                    }
                }
            else:
                return {
                    'name': {
                        'value': place_name
                    }
                }

        mocked_api.orion.get_entity.side_effect = get_entity

        response = app.test_client().get(f'/api/v1/robots/{robot_id}/')
        assert response.status_code == 200
        s = state if state != 'd_p' else 'delivering' if c == caller.Caller.ORDERING.value else 'picking'

        assert response.json == {'id': robot_id, 'state': s, 'destination': place_name}

        assert mocked_api.orion.get_entity.call_count == call_count
        for i in range(3):
            assert mocked_api.orion.get_entity.call_args_list[i] == call(const.FIWARE_SERVICE,
                                                                         const.DELIVERY_ROBOT_SERVICEPATH,
                                                                         const.DELIVERY_ROBOT_TYPE,
                                                                         robot_id)
        if call_count > 3:
            assert mocked_api.orion.get_entity.call_args_list[3] == call(const.FIWARE_SERVICE,
                                                                         const.DELIVERY_ROBOT_SERVICEPATH,
                                                                         const.PLACE_TYPE,
                                                                         'A_id')
        assert mocked_api.orion.make_delivery_robot_command.call_count == 0
        assert mocked_api.orion.make_emergency_command.call_count == 0
        assert mocked_api.orion.make_updatelastprocessedtime_command.call_count == 0
        assert mocked_api.orion.make_updatemode_command.call_count == 0
        assert mocked_api.orion.make_updatestate_command.call_count == 0
        assert mocked_api.orion.make_robotui_sendstate_command.call_count == 0
        assert mocked_api.orion.make_robotui_sendtokeninfo_command.call_count == 0
        assert mocked_api.orion.send_command.call_count == 0
        assert mocked_api.CommonMixin.waypoint().estimate_routes.call_count == 0
        assert mocked_api.CommonMixin.waypoint().get_places.call_count == 0
        assert mocked_api.CommonMixin.waypoint().get_waypoints.call_count == 0
        assert mocked_api.Token.get.call_count == 0
        assert mocked_api.Token.get.return_value.get_lock.call_count == 0
        assert mocked_api.MongoThrottling.lock.call_count == 0


class TestMoveNextAPI:

    @pytest.mark.parametrize('mode', [
        ' ', 'standby', 'error', [], {}, tuple([1]), 'dummy', 0, 1e-1, None
    ])
    @pytest.mark.parametrize('rwl', [
        [
            {
                'to': 'E_id', 'destination': 'dest_id', 'action': 'action_0',
                'waypoints': [
                    {'point': 'pC', 'angle': None}, {'point': 'pD', 'angle': None}, {'point': 'pE', 'angle': 'aE'},
                ]
            },
        ],
        [
            {
                'to': 'E_id', 'destination': 'dest_id', 'action': 'action_0',
                'waypoints': [
                    {'point': 'pC', 'angle': None}, {'point': 'pD', 'angle': None}, {'point': 'pE', 'angle': 'aE'},
                ]
            },
            {
                'to': 'F_id', 'destination': 'dest2_id', 'action': 'action_1',
                'waypoints': [
                    {'point': 'pF', 'angle': 'aF'},
                ]
            },
        ]
    ])
    def test_success(self, app, mocked_api, mode, rwl):
        robot_id = 'robot_01'

        def get_entity(fs, fsp, t, id):
            return {
                'mode': {
                    'value': mode,
                },
                'remaining_waypoints_list': {
                    'value': rwl,
                },
                'send_cmd_status': {
                    'value': 'OK',
                },
                'send_cmd_info': {
                    'value': {
                        'result': 'ack'
                    }
                }
            }
        mocked_api.orion.get_entity.side_effect = get_entity
        mocked_api.orion.make_delivery_robot_command.return_value = 'make_delivery_robot_command_return_value'

        response = app.test_client().patch(f'/api/v1/robots/{robot_id}/nexts/')
        assert response.status_code == 200
        assert response.json == {'result': 'success'}

        assert mocked_api.orion.get_entity.call_count == 3
        for i in range(3):
            assert mocked_api.orion.get_entity.call_args_list[i] == call(const.FIWARE_SERVICE,
                                                                         const.DELIVERY_ROBOT_SERVICEPATH,
                                                                         const.DELIVERY_ROBOT_TYPE,
                                                                         robot_id)
        assert mocked_api.orion.make_delivery_robot_command.call_count == 1
        assert mocked_api.orion.make_delivery_robot_command.call_args == call('navi',
                                                                              rwl[0]['waypoints'],
                                                                              rwl[0],
                                                                              [] if len(rwl) == 1 else [rwl[1]],
                                                                              None,
                                                                              None,
                                                                              None)
        assert mocked_api.orion.send_command.call_count == 1
        assert mocked_api.orion.send_command.call_args == call(const.FIWARE_SERVICE,
                                                               const.DELIVERY_ROBOT_SERVICEPATH,
                                                               const.DELIVERY_ROBOT_TYPE,
                                                               robot_id,
                                                               'make_delivery_robot_command_return_value')
        assert mocked_api.CommonMixin.waypoint().estimate_routes.call_count == 0
        assert mocked_api.orion.make_emergency_command.call_count == 0
        assert mocked_api.orion.make_updatelastprocessedtime_command.call_count == 0
        assert mocked_api.orion.make_updatemode_command.call_count == 0
        assert mocked_api.orion.make_updatestate_command.call_count == 0
        assert mocked_api.orion.make_robotui_sendstate_command.call_count == 0
        assert mocked_api.orion.make_robotui_sendtokeninfo_command.call_count == 0
        assert mocked_api.CommonMixin.waypoint().get_places.call_count == 0
        assert mocked_api.CommonMixin.waypoint().get_waypoints.call_count == 0
        assert mocked_api.Token.get.call_count == 0
        assert mocked_api.Token.get.return_value.get_lock.call_count == 0
        assert mocked_api.MongoThrottling.lock.call_count == 0

    @pytest.mark.parametrize('rwl', [
        [], ['a', 1], {}, {'a': 1}, tuple(['a', 1]), set([1, 2]), 'dummy', caller.Caller.WAREHOUSE, 0, 1e-1, None
    ])
    def test_navigating(self, app, mocked_api, rwl):
        robot_id = 'robot_01'
        mode = 'navi'

        def get_entity(fs, fsp, t, id):
            return {
                'mode': {
                    'value': mode,
                },
                'remaining_waypoints_list': {
                    'value': rwl
                },
                'send_cmd_status': {
                    'value': 'OK',
                },
                'send_cmd_info': {
                    'value': {
                        'result': 'ack'
                    }
                }
            }
        mocked_api.orion.get_entity.side_effect = get_entity

        response = app.test_client().patch(f'/api/v1/robots/{robot_id}/nexts/')
        assert response.status_code == 423
        assert response.json == {
            'message': 'robot(robot_01) is navigating now',
            'id': 'robot_01',
        }

        assert mocked_api.orion.get_entity.call_count == 1
        assert mocked_api.orion.get_entity.call_args_list[0] == call(const.FIWARE_SERVICE,
                                                                     const.DELIVERY_ROBOT_SERVICEPATH,
                                                                     const.DELIVERY_ROBOT_TYPE,
                                                                     robot_id)
        assert mocked_api.orion.make_delivery_robot_command.call_count == 0
        assert mocked_api.orion.send_command.call_count == 0
        assert mocked_api.CommonMixin.waypoint().estimate_routes.call_count == 0
        assert mocked_api.orion.make_emergency_command.call_count == 0
        assert mocked_api.orion.make_updatelastprocessedtime_command.call_count == 0
        assert mocked_api.orion.make_updatemode_command.call_count == 0
        assert mocked_api.orion.make_updatestate_command.call_count == 0
        assert mocked_api.orion.make_robotui_sendstate_command.call_count == 0
        assert mocked_api.orion.make_robotui_sendtokeninfo_command.call_count == 0
        assert mocked_api.CommonMixin.waypoint().get_places.call_count == 0
        assert mocked_api.CommonMixin.waypoint().get_waypoints.call_count == 0
        assert mocked_api.Token.get.call_count == 0
        assert mocked_api.Token.get.return_value.get_lock.call_count == 0
        assert mocked_api.MongoThrottling.lock.call_count == 0

    @pytest.mark.parametrize('mode', [
        ' ', 'standby', 'error', [], {}, tuple([1]), 'dummy', 0, 1e-1, None
    ])
    @pytest.mark.parametrize('rwl', [
        [], {}, {'a': 1}, tuple([1]), set([1, 2]), 'dummy', 0, 1e-1, None
    ])
    def test_no_remaining_waypoints_list(self, app, mocked_api, mode, rwl):
        robot_id = 'robot_01'

        def get_entity(fs, fsp, t, id):
            return {
                'mode': {
                    'value': mode,
                },
                'remaining_waypoints_list': {
                    'value': rwl
                },
                'send_cmd_status': {
                    'value': 'OK',
                },
                'send_cmd_info': {
                    'value': {
                        'result': 'ack'
                    }
                }
            }
        mocked_api.orion.get_entity.side_effect = get_entity

        response = app.test_client().patch(f'/api/v1/robots/{robot_id}/nexts/')
        assert response.status_code == 412
        assert response.json == {
            'message': 'no remaining waypoints for robot(robot_01)',
            'id': 'robot_01',
        }

        assert mocked_api.orion.get_entity.call_count == 2
        for i in range(2):
            assert mocked_api.orion.get_entity.call_args_list[i] == call(const.FIWARE_SERVICE,
                                                                         const.DELIVERY_ROBOT_SERVICEPATH,
                                                                         const.DELIVERY_ROBOT_TYPE,
                                                                         robot_id)
        assert mocked_api.orion.make_delivery_robot_command.call_count == 0
        assert mocked_api.orion.send_command.call_count == 0
        assert mocked_api.CommonMixin.waypoint().estimate_routes.call_count == 0
        assert mocked_api.orion.make_emergency_command.call_count == 0
        assert mocked_api.orion.make_updatelastprocessedtime_command.call_count == 0
        assert mocked_api.orion.make_updatemode_command.call_count == 0
        assert mocked_api.orion.make_updatestate_command.call_count == 0
        assert mocked_api.orion.make_robotui_sendstate_command.call_count == 0
        assert mocked_api.orion.make_robotui_sendtokeninfo_command.call_count == 0
        assert mocked_api.CommonMixin.waypoint().get_places.call_count == 0
        assert mocked_api.CommonMixin.waypoint().get_waypoints.call_count == 0
        assert mocked_api.Token.get.call_count == 0
        assert mocked_api.Token.get.return_value.get_lock.call_count == 0
        assert mocked_api.MongoThrottling.lock.call_count == 0

    def test_send_cmd_status_pending(self, app, mocked_api):
        robot_id = 'robot_01'
        mode = 'standby'
        rwl = [
            {
                'to': 'E_id', 'destination': 'dest_id', 'action': 'action_0',
                'waypoints': [
                    {'point': 'pC', 'angle': None}, {'point': 'pD', 'angle': None}, {'point': 'pE', 'angle': 'aE'},
                ]
            },
        ]

        def get_entity(fs, fsp, t, id):
            return {
                'mode': {
                    'value': mode,
                },
                'remaining_waypoints_list': {
                    'value': rwl,
                },
                'send_cmd_status': {
                    'value': 'pending',
                },
                'send_cmd_info': {
                    'value': {
                        'result': 'ack'
                    }
                }
            }
        mocked_api.orion.get_entity.side_effect = get_entity
        mocked_api.orion.make_delivery_robot_command.return_value = 'make_delivery_robot_command_return_value'

        response = app.test_client().patch(f'/api/v1/robots/{robot_id}/nexts/')
        assert response.status_code == 500
        assert response.json == {
            'message': 'send_cmd_status still pending, robot_id=robot_01, wait_msec=10, wait_count=3',
        }
        assert mocked_api.orion.get_entity.call_count == 5
        for i in range(5):
            assert mocked_api.orion.get_entity.call_args_list[i] == call(const.FIWARE_SERVICE,
                                                                         const.DELIVERY_ROBOT_SERVICEPATH,
                                                                         const.DELIVERY_ROBOT_TYPE,
                                                                         'robot_01')
        assert mocked_api.orion.make_delivery_robot_command.call_count == 1
        assert mocked_api.orion.make_delivery_robot_command.call_args == call('navi',
                                                                              rwl[0]['waypoints'],
                                                                              rwl[0],
                                                                              [],
                                                                              None,
                                                                              None,
                                                                              None)
        assert mocked_api.orion.send_command.call_count == 1
        assert mocked_api.orion.send_command.call_args == call(const.FIWARE_SERVICE,
                                                               const.DELIVERY_ROBOT_SERVICEPATH,
                                                               const.DELIVERY_ROBOT_TYPE,
                                                               'robot_01',
                                                               'make_delivery_robot_command_return_value')
        assert mocked_api.CommonMixin.waypoint().estimate_routes.call_count == 0
        assert mocked_api.orion.make_emergency_command.call_count == 0
        assert mocked_api.orion.make_updatelastprocessedtime_command.call_count == 0
        assert mocked_api.orion.make_updatemode_command.call_count == 0
        assert mocked_api.orion.make_updatestate_command.call_count == 0
        assert mocked_api.orion.make_robotui_sendstate_command.call_count == 0
        assert mocked_api.orion.make_robotui_sendtokeninfo_command.call_count == 0
        assert mocked_api.CommonMixin.waypoint().get_places.call_count == 0
        assert mocked_api.CommonMixin.waypoint().get_waypoints.call_count == 0
        assert mocked_api.Token.get.call_count == 0
        assert mocked_api.Token.get.return_value.get_lock.call_count == 0
        assert mocked_api.MongoThrottling.lock.call_count == 0

    @pytest.mark.parametrize('send_cmd_info_value, errmsg', [
        ({'result': 'error', 'errors': 'dummy error'}, 'move robot error, robot_id=robot_01, errors="dummy error"'),
        ({'result': 'error'}, 'move robot error, robot_id=robot_01, errors=""'),
        ({'result': 0}, 'move robot error, robot_id=robot_01, errors=""'),
        ({'result': 1e-1}, 'move robot error, robot_id=robot_01, errors=""'),
        ({'result': True}, 'move robot error, robot_id=robot_01, errors=""'),
        ({'result': []}, 'move robot error, robot_id=robot_01, errors=""'),
        ({'result': ['a', 1]}, 'move robot error, robot_id=robot_01, errors=""'),
        ({'result': {}}, 'move robot error, robot_id=robot_01, errors=""'),
        ({'result': {'a': 1}}, 'move robot error, robot_id=robot_01, errors=""'),
        ({'result': tuple(['a', 1])}, 'move robot error, robot_id=robot_01, errors=""'),
        ({'result': set(['a', 1])}, 'move robot error, robot_id=robot_01, errors=""'),
        ({'result': caller.Caller.WAREHOUSE}, 'move robot error, robot_id=robot_01, errors=""'),
        ({'result': None}, 'move robot error, robot_id=robot_01, errors=""'),
        ({'errors': 'dummy error'}, "invalid send_cmd_info, {'errors': 'dummy error'}"),
        ({}, "invalid send_cmd_info, {}"),
        ('dummy', "invalid send_cmd_info, dummy"),
        (0, "invalid send_cmd_info, 0"),
        (1e-1, "invalid send_cmd_info, 0.1"),
        (True, "invalid send_cmd_info, True"),
        ([], "invalid send_cmd_info, []"),
        (tuple([]), "invalid send_cmd_info, ()"),
        (set([]), "invalid send_cmd_info, set()"),
        (caller.Caller.WAREHOUSE, "invalid send_cmd_info, warehouse"),
        (None, "invalid send_cmd_info, None"),
    ])
    def test_send_cmd_result_invalid(self, app, mocked_api, send_cmd_info_value, errmsg):
        robot_id = 'robot_01'
        mode = 'standby'
        rwl = [
            {
                'to': 'E_id', 'destination': 'dest_id', 'action': 'action_0',
                'waypoints': [
                    {'point': 'pC', 'angle': None}, {'point': 'pD', 'angle': None}, {'point': 'pE', 'angle': 'aE'},
                ]
            },
        ]

        def get_entity(fs, fsp, t, id):
            return {
                'mode': {
                    'value': mode,
                },
                'remaining_waypoints_list': {
                    'value': rwl,
                },
                'send_cmd_status': {
                    'value': 'OK',
                },
                'send_cmd_info': {
                    'value': send_cmd_info_value,
                },
            }
        mocked_api.orion.get_entity.side_effect = get_entity
        mocked_api.orion.make_delivery_robot_command.return_value = 'make_delivery_robot_command_return_value'

        response = app.test_client().patch(f'/api/v1/robots/{robot_id}/nexts/')
        assert response.status_code == 500
        assert response.json == {
            'message': errmsg,
        }
        assert mocked_api.orion.get_entity.call_count == 3
        for i in range(3):
            assert mocked_api.orion.get_entity.call_args_list[i] == call(const.FIWARE_SERVICE,
                                                                         const.DELIVERY_ROBOT_SERVICEPATH,
                                                                         const.DELIVERY_ROBOT_TYPE,
                                                                         'robot_01')
        assert mocked_api.orion.make_delivery_robot_command.call_count == 1
        assert mocked_api.orion.make_delivery_robot_command.call_args == call('navi',
                                                                              rwl[0]['waypoints'],
                                                                              rwl[0],
                                                                              [],
                                                                              None,
                                                                              None,
                                                                              None)
        assert mocked_api.orion.send_command.call_count == 1
        assert mocked_api.orion.send_command.call_args == call(const.FIWARE_SERVICE,
                                                               const.DELIVERY_ROBOT_SERVICEPATH,
                                                               const.DELIVERY_ROBOT_TYPE,
                                                               'robot_01',
                                                               'make_delivery_robot_command_return_value')
        assert mocked_api.CommonMixin.waypoint().estimate_routes.call_count == 0
        assert mocked_api.orion.make_emergency_command.call_count == 0
        assert mocked_api.orion.make_updatelastprocessedtime_command.call_count == 0
        assert mocked_api.orion.make_updatemode_command.call_count == 0
        assert mocked_api.orion.make_updatestate_command.call_count == 0
        assert mocked_api.orion.make_robotui_sendstate_command.call_count == 0
        assert mocked_api.orion.make_robotui_sendtokeninfo_command.call_count == 0
        assert mocked_api.CommonMixin.waypoint().get_places.call_count == 0
        assert mocked_api.CommonMixin.waypoint().get_waypoints.call_count == 0
        assert mocked_api.Token.get.call_count == 0
        assert mocked_api.Token.get.return_value.get_lock.call_count == 0
        assert mocked_api.MongoThrottling.lock.call_count == 0

    def test_send_cmd_result_navi_ignore_refresh_ack(self, app, mocked_api):
        robot_id = 'robot_01'
        mode = 'standby'
        rwl = [
            {
                'to': 'E_id', 'destination': 'dest_id', 'action': 'action_0',
                'waypoints': [
                    {'point': 'pC', 'angle': None}, {'point': 'pD', 'angle': None}, {'point': 'pE', 'angle': 'aE'},
                ]
            },
        ]

        def get_entity():
            c = 0

            def _result(fs, fsp, t, id):
                nonlocal c
                result = None
                if c < 3:
                    result = {
                        'mode': {
                            'value': mode,
                        },
                        'remaining_waypoints_list': {
                            'value': rwl,
                        },
                        'send_cmd_status': {
                            'value': 'OK',
                        },
                        'send_cmd_info': {
                            'value': {
                                'result': 'ignore'
                            }
                        }
                    }
                else:
                    result = {
                        'mode': {
                            'value': mode,
                        },
                        'remaining_waypoints_list': {
                            'value': rwl,
                        },
                        'send_cmd_status': {
                            'value': 'OK',
                        },
                        'send_cmd_info': {
                            'value': {
                                'result': 'ack'
                            }
                        }
                    }
                c += 1
                return result
            return _result

        mocked_api.orion.get_entity.side_effect = get_entity()
        mocked_api.orion.make_delivery_robot_command.return_value = 'make_delivery_robot_command_return_value'

        response = app.test_client().patch(f'/api/v1/robots/{robot_id}/nexts/')
        assert response.status_code == 200
        assert response.json == {'result': 'success'}

        assert mocked_api.orion.get_entity.call_count == 4
        for i in range(4):
            assert mocked_api.orion.get_entity.call_args_list[i] == call(const.FIWARE_SERVICE,
                                                                         const.DELIVERY_ROBOT_SERVICEPATH,
                                                                         const.DELIVERY_ROBOT_TYPE,
                                                                         'robot_01')
        assert mocked_api.orion.make_delivery_robot_command.call_count == 2
        assert mocked_api.orion.make_delivery_robot_command.call_args_list[0] == call('navi',
                                                                                      rwl[0]['waypoints'],
                                                                                      rwl[0],
                                                                                      [],
                                                                                      None,
                                                                                      None,
                                                                                      None)
        assert mocked_api.orion.make_delivery_robot_command.call_args_list[1] == call('refresh',
                                                                                      rwl[0]['waypoints'],
                                                                                      rwl[0],
                                                                                      [],
                                                                                      None,
                                                                                      None,
                                                                                      None)
        assert mocked_api.orion.send_command.call_count == 2
        for i in range(2):
            assert mocked_api.orion.send_command.call_args_list[i] == call(const.FIWARE_SERVICE,
                                                                           const.DELIVERY_ROBOT_SERVICEPATH,
                                                                           const.DELIVERY_ROBOT_TYPE,
                                                                           'robot_01',
                                                                           'make_delivery_robot_command_return_value')
        assert mocked_api.CommonMixin.waypoint().estimate_routes.call_count == 0
        assert mocked_api.orion.make_emergency_command.call_count == 0
        assert mocked_api.orion.make_updatelastprocessedtime_command.call_count == 0
        assert mocked_api.orion.make_updatemode_command.call_count == 0
        assert mocked_api.orion.make_updatestate_command.call_count == 0
        assert mocked_api.orion.make_robotui_sendstate_command.call_count == 0
        assert mocked_api.orion.make_robotui_sendtokeninfo_command.call_count == 0
        assert mocked_api.CommonMixin.waypoint().get_places.call_count == 0
        assert mocked_api.CommonMixin.waypoint().get_waypoints.call_count == 0
        assert mocked_api.Token.get.call_count == 0
        assert mocked_api.Token.get.return_value.get_lock.call_count == 0
        assert mocked_api.MongoThrottling.lock.call_count == 0

    def test_send_cmd_result_navi_ignore_refresh_ignore(self, app, mocked_api):
        robot_id = 'robot_01'
        mode = 'standby'
        rwl = [
            {
                'to': 'E_id', 'destination': 'dest_id', 'action': 'action_0',
                'waypoints': [
                    {'point': 'pC', 'angle': None}, {'point': 'pD', 'angle': None}, {'point': 'pE', 'angle': 'aE'},
                ]
            },
        ]

        def get_entity(fs, fsp, t, id):
            return {
                'mode': {
                    'value': mode,
                },
                'remaining_waypoints_list': {
                    'value': rwl,
                },
                'send_cmd_status': {
                    'value': 'OK',
                },
                'send_cmd_info': {
                    'value': {
                        'result': 'ignore'
                    }
                }
            }
        mocked_api.orion.get_entity.side_effect = get_entity
        mocked_api.orion.make_delivery_robot_command.return_value = 'make_delivery_robot_command_return_value'

        response = app.test_client().patch(f'/api/v1/robots/{robot_id}/nexts/')
        assert response.status_code == 500
        assert response.json == {
            'message': 'cannot move robot(robot_01) to "E_id" using "navi" and "refresh", '
            'navi result=ignore refresh result=ignore'
        }
        assert mocked_api.orion.get_entity.call_count == 4
        for i in range(4):
            assert mocked_api.orion.get_entity.call_args_list[i] == call(const.FIWARE_SERVICE,
                                                                         const.DELIVERY_ROBOT_SERVICEPATH,
                                                                         const.DELIVERY_ROBOT_TYPE,
                                                                         'robot_01')
        assert mocked_api.orion.make_delivery_robot_command.call_count == 2
        assert mocked_api.orion.make_delivery_robot_command.call_args_list[0] == call('navi',
                                                                                      rwl[0]['waypoints'],
                                                                                      rwl[0],
                                                                                      [],
                                                                                      None,
                                                                                      None,
                                                                                      None)
        assert mocked_api.orion.make_delivery_robot_command.call_args_list[1] == call('refresh',
                                                                                      rwl[0]['waypoints'],
                                                                                      rwl[0],
                                                                                      [],
                                                                                      None,
                                                                                      None,
                                                                                      None)
        assert mocked_api.orion.send_command.call_count == 2
        for i in range(2):
            assert mocked_api.orion.send_command.call_args_list[i] == call(const.FIWARE_SERVICE,
                                                                           const.DELIVERY_ROBOT_SERVICEPATH,
                                                                           const.DELIVERY_ROBOT_TYPE,
                                                                           'robot_01',
                                                                           'make_delivery_robot_command_return_value')
        assert mocked_api.CommonMixin.waypoint().estimate_routes.call_count == 0
        assert mocked_api.orion.make_emergency_command.call_count == 0
        assert mocked_api.orion.make_updatelastprocessedtime_command.call_count == 0
        assert mocked_api.orion.make_updatemode_command.call_count == 0
        assert mocked_api.orion.make_updatestate_command.call_count == 0
        assert mocked_api.orion.make_robotui_sendstate_command.call_count == 0
        assert mocked_api.orion.make_robotui_sendtokeninfo_command.call_count == 0
        assert mocked_api.CommonMixin.waypoint().get_places.call_count == 0
        assert mocked_api.CommonMixin.waypoint().get_waypoints.call_count == 0
        assert mocked_api.Token.get.call_count == 0
        assert mocked_api.Token.get.return_value.get_lock.call_count == 0
        assert mocked_api.MongoThrottling.lock.call_count == 0


class TestEmergencyAPI:

    def test_success(self, app, mocked_api):
        robot_id = 'robot_01'

        mocked_api.orion.make_emergency_command.return_value = 'make_emergency_command_return_value'

        response = app.test_client().patch(f'/api/v1/robots/{robot_id}/emergencies/')
        assert response.status_code == 200
        assert response.json == {'result': 'success'}

        assert mocked_api.orion.get_entity.call_count == 0
        assert mocked_api.orion.make_emergency_command.call_count == 1
        assert mocked_api.orion.make_emergency_command.call_args == call('stop')
        assert mocked_api.orion.send_command.call_count == 1
        assert mocked_api.orion.send_command.call_args == call(const.FIWARE_SERVICE,
                                                               const.DELIVERY_ROBOT_SERVICEPATH,
                                                               const.DELIVERY_ROBOT_TYPE,
                                                               robot_id,
                                                               'make_emergency_command_return_value')
        assert mocked_api.CommonMixin.waypoint().estimate_routes.call_count == 0
        assert mocked_api.orion.make_delivery_robot_command.call_count == 0
        assert mocked_api.orion.make_updatelastprocessedtime_command.call_count == 0
        assert mocked_api.orion.make_updatemode_command.call_count == 0
        assert mocked_api.orion.make_updatestate_command.call_count == 0
        assert mocked_api.orion.make_robotui_sendstate_command.call_count == 0
        assert mocked_api.orion.make_robotui_sendtokeninfo_command.call_count == 0
        assert mocked_api.CommonMixin.waypoint().get_places.call_count == 0
        assert mocked_api.CommonMixin.waypoint().get_waypoints.call_count == 0
        assert mocked_api.Token.get.call_count == 0
        assert mocked_api.Token.get.return_value.get_lock.call_count == 0
        assert mocked_api.MongoThrottling.lock.call_count == 0


class TestRobotNotificationAPI:

    def test_moving_to_moving(self, app, mocked_api):
        robot_id = 'robot_01'
        next_mode = 'navi'
        time = '2020-01-02T03:04:05.678+09:00'
        current_mode = 'navi'
        current_state = const.STATE_MOVING
        last_processed_time = '2020-01-02T03:04:05.000+09:00'

        data = {
            'id': robot_id,
            'mode': {
                'value': next_mode,
            },
            'time': {
                'value': time,
            },
        }

        notified_data = {
            'data': [data]
        }

        def get_entity(fs, fsp, t, id):
            return {
                'mode': {
                    'value': None,
                },
                'navigating_waypoints': {
                    'value': None,
                },
                'current_mode': {
                    'value': current_mode,
                },
                'current_state': {
                    'value': current_state,
                },
                'last_processed_time': {
                    'value': last_processed_time,
                }
            }
        mocked_api.orion.get_entity.side_effect = get_entity
        mocked_api.orion.make_updatelastprocessedtime_command.return_value = 'make_updatelastprocessedtime_command_return_value'

        response = app.test_client().post(f'/api/v1/robots/notifications/',
                                          content_type='application/json', data=json.dumps(notified_data))
        assert response.status_code == 200
        assert response.json == {
            'result': 'success',
            'processed_data': [],
            'ignored_data': [data],
        }
        assert mocked_api.orion.get_entity.call_count == 1
        assert mocked_api.orion.get_entity.call_args == call(const.FIWARE_SERVICE,
                                                             const.DELIVERY_ROBOT_SERVICEPATH,
                                                             const.DELIVERY_ROBOT_TYPE,
                                                             robot_id)
        assert mocked_api.orion.make_updatelastprocessedtime_command.call_count == 1
        assert mocked_api.orion.make_updatelastprocessedtime_command.call_args == call(dateutil.parser.parse(time))
        assert mocked_api.orion.make_updatemode_command.call_count == 0
        assert mocked_api.orion.send_command.call_count == 1
        assert mocked_api.orion.send_command.call_args == call(const.FIWARE_SERVICE,
                                                               const.DELIVERY_ROBOT_SERVICEPATH,
                                                               const.DELIVERY_ROBOT_TYPE,
                                                               robot_id,
                                                               'make_updatelastprocessedtime_command_return_value')
        assert mocked_api.orion.make_delivery_robot_command.call_count == 0
        assert mocked_api.orion.make_emergency_command.call_count == 0
        assert mocked_api.orion.make_updatestate_command.call_count == 0
        assert mocked_api.orion.make_robotui_sendstate_command.call_count == 0
        assert mocked_api.orion.make_robotui_sendtokeninfo_command.call_count == 0
        assert mocked_api.CommonMixin.waypoint().estimate_routes.call_count == 0
        assert mocked_api.CommonMixin.waypoint().get_places.call_count == 0
        assert mocked_api.CommonMixin.waypoint().get_waypoints.call_count == 0
        assert mocked_api.Token.get.call_count == 0
        assert mocked_api.Token.get.return_value.get_lock.call_count == 0
        assert mocked_api.MongoThrottling.lock.call_count == 1
        assert mocked_api.MongoThrottling.lock.call_args == call(robot_id, dateutil.parser.parse(time))

    @pytest.mark.parametrize('current_mode', [
        '', 'standby', 'error',
    ])
    def test_navi_to_moving(self, app, mocked_api, current_mode):
        robot_id = 'robot_01'
        next_mode = 'navi'
        current_state = const.STATE_MOVING
        time = '2020-01-02T03:04:05.678+09:00'
        last_processed_time = '2020-01-02T03:04:05.000+09:00'

        data = {
            'id': robot_id,
            'mode': {
                'value': next_mode,
            },
            'time': {
                'value': time,
            },
        }

        notified_data = {
            'data': [data]
        }

        def get_entity(fs, fsp, t, id):
            return {
                'mode': {
                    'value': None,
                },
                'navigating_waypoints': {
                    'value': None,
                },
                'current_mode': {
                    'value': current_mode,
                },
                'current_state': {
                    'value': current_state,
                },
                'last_processed_time': {
                    'value': last_processed_time,
                }
            }
        mocked_api.orion.get_entity.side_effect = get_entity
        mocked_api.orion.make_updatelastprocessedtime_command.return_value = 'make_updatelastprocessedtime_command_return_value'
        mocked_api.orion.make_updatemode_command.return_value = 'make_updatemode_command_return_value'

        response = app.test_client().post(f'/api/v1/robots/notifications/',
                                          content_type='application/json', data=json.dumps(notified_data))
        assert response.status_code == 200
        assert response.json == {
            'result': 'success',
            'processed_data': [data],
            'ignored_data': [],
        }
        assert mocked_api.orion.get_entity.call_count == 1
        assert mocked_api.orion.get_entity.call_args == call(const.FIWARE_SERVICE,
                                                             const.DELIVERY_ROBOT_SERVICEPATH,
                                                             const.DELIVERY_ROBOT_TYPE,
                                                             robot_id)
        assert mocked_api.orion.make_updatelastprocessedtime_command.call_count == 1
        assert mocked_api.orion.make_updatelastprocessedtime_command.call_args == call(dateutil.parser.parse(time))
        assert mocked_api.orion.make_updatemode_command.call_count == 1
        assert mocked_api.orion.make_updatemode_command.call_args == call(next_mode)
        assert mocked_api.orion.send_command.call_count == 2
        assert mocked_api.orion.send_command.call_args_list[0] == call(const.FIWARE_SERVICE,
                                                                       const.DELIVERY_ROBOT_SERVICEPATH,
                                                                       const.DELIVERY_ROBOT_TYPE,
                                                                       robot_id,
                                                                       'make_updatelastprocessedtime_command_return_value')
        assert mocked_api.orion.send_command.call_args_list[1] == call(const.FIWARE_SERVICE,
                                                                       const.DELIVERY_ROBOT_SERVICEPATH,
                                                                       const.DELIVERY_ROBOT_TYPE,
                                                                       robot_id,
                                                                       'make_updatemode_command_return_value')
        assert mocked_api.orion.make_delivery_robot_command.call_count == 0
        assert mocked_api.orion.make_emergency_command.call_count == 0
        assert mocked_api.orion.make_updatestate_command.call_count == 0
        assert mocked_api.orion.make_robotui_sendstate_command.call_count == 0
        assert mocked_api.orion.make_robotui_sendtokeninfo_command.call_count == 0
        assert mocked_api.CommonMixin.waypoint().estimate_routes.call_count == 0
        assert mocked_api.CommonMixin.waypoint().get_places.call_count == 0
        assert mocked_api.CommonMixin.waypoint().get_waypoints.call_count == 0
        assert mocked_api.Token.get.call_count == 0
        assert mocked_api.Token.get.return_value.get_lock.call_count == 0
        assert mocked_api.MongoThrottling.lock.call_count == 1
        assert mocked_api.MongoThrottling.lock.call_args == call(robot_id, dateutil.parser.parse(time))

    @pytest.mark.parametrize('current_mode', [
        '', 'standby', 'error',
    ])
    @pytest.mark.parametrize('current_state', [
        '', 'standby', 'picking', 'delivering',
    ])
    @pytest.mark.parametrize('d_value, d_name', [
        ('', None),
        ({'destination': 'd_id'}, {'name': {'value': 'd_name'}}),
        ({'destination': 'd_id'}, None),
    ])
    def test_not_moving_to_moving(self, app, mocked_api, current_mode, current_state, d_value, d_name):
        robot_id = 'robot_01'
        ui_id = 'ui_01'
        next_mode = 'navi'
        time = '2020-01-02T03:04:05.678+09:00'
        last_processed_time = '2020-01-02T03:04:05.000+09:00'

        data = {
            'id': robot_id,
            'mode': {
                'value': next_mode,
            },
            'time': {
                'value': time,
            },
        }

        notified_data = {
            'data': [data]
        }

        def get_entity(fs, fsp, t, id):
            if t == const.DELIVERY_ROBOT_TYPE:
                return {
                    'mode': {
                        'value': None,
                    },
                    'navigating_waypoints': {
                        'value': d_value,
                    },
                    'current_mode': {
                        'value': current_mode,
                    },
                    'current_state': {
                        'value': current_state,
                    },
                    'last_processed_time': {
                        'value': last_processed_time,
                    }
                }
            else:
                return d_name

        mocked_api.orion.get_entity.side_effect = get_entity
        mocked_api.orion.make_updatelastprocessedtime_command.return_value = 'make_updatelastprocessedtime_command_return_value'
        mocked_api.orion.make_updatemode_command.return_value = 'make_updatemode_command_return_value'
        mocked_api.orion.make_updatestate_command.return_value = 'make_updatestate_command_return_value'
        mocked_api.orion.make_robotui_sendstate_command.return_value = 'make_robotui_sendstate_command_return_value'

        response = app.test_client().post(f'/api/v1/robots/notifications/',
                                          content_type='application/json', data=json.dumps(notified_data))
        assert response.status_code == 200
        assert response.json == {
            'result': 'success',
            'processed_data': [data],
            'ignored_data': [],
        }
        if d_value == '':
            assert mocked_api.orion.get_entity.call_count == 2
            for i in range(2):
                assert mocked_api.orion.get_entity.call_args_list[i] == call(const.FIWARE_SERVICE,
                                                                             const.DELIVERY_ROBOT_SERVICEPATH,
                                                                             const.DELIVERY_ROBOT_TYPE,
                                                                             robot_id)
        else:
            assert mocked_api.orion.get_entity.call_count == 3
            for i in range(2):
                assert mocked_api.orion.get_entity.call_args_list[i] == call(const.FIWARE_SERVICE,
                                                                             const.DELIVERY_ROBOT_SERVICEPATH,
                                                                             const.DELIVERY_ROBOT_TYPE,
                                                                             robot_id)
            assert mocked_api.orion.get_entity.call_args_list[2] == call(const.FIWARE_SERVICE,
                                                                         const.DELIVERY_ROBOT_SERVICEPATH,
                                                                         const.PLACE_TYPE,
                                                                         d_value['destination'])
        assert mocked_api.orion.make_updatelastprocessedtime_command.call_count == 1
        assert mocked_api.orion.make_updatelastprocessedtime_command.call_args == call(dateutil.parser.parse(time))
        assert mocked_api.orion.make_updatemode_command.call_count == 1
        assert mocked_api.orion.make_updatemode_command.call_args == call(next_mode)
        assert mocked_api.orion.make_updatestate_command.call_count == 1
        assert mocked_api.orion.make_updatestate_command.call_args == call(const.STATE_MOVING)
        assert mocked_api.orion.send_command.call_count == 4
        assert mocked_api.orion.send_command.call_args_list[0] == call(const.FIWARE_SERVICE,
                                                                       const.DELIVERY_ROBOT_SERVICEPATH,
                                                                       const.DELIVERY_ROBOT_TYPE,
                                                                       robot_id,
                                                                       'make_updatelastprocessedtime_command_return_value')
        assert mocked_api.orion.send_command.call_args_list[1] == call(const.FIWARE_SERVICE,
                                                                       const.DELIVERY_ROBOT_SERVICEPATH,
                                                                       const.DELIVERY_ROBOT_TYPE,
                                                                       robot_id,
                                                                       'make_updatemode_command_return_value')
        assert mocked_api.orion.send_command.call_args_list[2] == call(const.FIWARE_SERVICE,
                                                                       const.DELIVERY_ROBOT_SERVICEPATH,
                                                                       const.DELIVERY_ROBOT_TYPE,
                                                                       robot_id,
                                                                       'make_updatestate_command_return_value')
        assert mocked_api.orion.send_command.call_args_list[3] == call(const.FIWARE_SERVICE,
                                                                       const.ROBOT_UI_SERVICEPATH,
                                                                       const.ROBOT_UI_TYPE,
                                                                       ui_id,
                                                                       'make_robotui_sendstate_command_return_value')
        assert mocked_api.orion.make_robotui_sendstate_command.call_count == 1
        assert mocked_api.orion.make_robotui_sendstate_command.call_args == call(
            const.STATE_MOVING, d_name['name']['value'] if d_name else '')
        assert mocked_api.orion.make_delivery_robot_command.call_count == 0
        assert mocked_api.orion.make_emergency_command.call_count == 0
        assert mocked_api.orion.make_robotui_sendtokeninfo_command.call_count == 0
        assert mocked_api.CommonMixin.waypoint().estimate_routes.call_count == 0
        assert mocked_api.CommonMixin.waypoint().get_places.call_count == 0
        assert mocked_api.CommonMixin.waypoint().get_waypoints.call_count == 0
        assert mocked_api.Token.get.call_count == 0
        assert mocked_api.Token.get.return_value.get_lock.call_count == 0
        assert mocked_api.MongoThrottling.lock.call_count == 1
        assert mocked_api.MongoThrottling.lock.call_args == call(robot_id, dateutil.parser.parse(time))

    @pytest.mark.parametrize('mode', [
        '', 'standby', 'error',
    ])
    @pytest.mark.parametrize('current_state', [
        '', 'moving', 'standby', 'picking', 'delivering',
    ])
    @pytest.mark.parametrize('nw_value, order', [
        (None, None),
        (
            {'destination': 'A_id', 'to': 'A_id'},
            {'source': 'A_id', 'via': [], 'destination': None},
        ),
        (
            {'to': 'A_id'},
            {'source': 'A_id', 'via': [], 'destination': None},
        ),
        (
            {'destination': 'A_id', 'to': 'A_id'},
            {'source': None, 'via': [], 'destination': 'A_id'},
        ),
        (
            {'to': 'A_id'},
            {'source': None, 'via': [], 'destination': 'A_id'},
        ),
        (
            {'destination': 'A_id', 'to': 'A_id'},
            {'source': None, 'via': ['A_id'], 'destination': None},
        ),
        (
            {'to': 'A_id'},
            {'source': None, 'via': ['A_id'], 'destination': None},
        ),
        (
            {'destination': 'A_id', 'to': 'A_id'},
            {'source': None, 'via': [], 'destination': None},
        ),
        (
            {'to': 'A_id'},
            {'source': None, 'via': [], 'destination': None},
        ),
    ])
    @pytest.mark.parametrize('c', [
        'ordering', 'warehouse', '', None
    ])
    def test_not_navi_to_standby(self, app, mocked_api, mode, current_state, nw_value, order, c):
        robot_id = 'robot_01'
        next_mode = mode
        time = '2020-01-02T03:04:05.678+09:00'
        current_mode = mode
        last_processed_time = '2020-01-02T03:04:05.000+09:00'

        data = {
            'id': robot_id,
            'mode': {
                'value': next_mode,
            },
            'time': {
                'value': time,
            },
        }

        notified_data = {
            'data': [data]
        }

        def get_entity(fs, fsp, t, id):
            return {
                'mode': {
                    'value': None,
                },
                'navigating_waypoints': {
                    'value': nw_value,
                },
                'current_mode': {
                    'value': current_mode,
                },
                'current_state': {
                    'value': current_state,
                },
                'last_processed_time': {
                    'value': last_processed_time,
                },
                'order': {
                    'value': order,
                },
                'caller': {
                    'value': c,
                }
            }
        mocked_api.orion.get_entity.side_effect = get_entity
        mocked_api.orion.make_updatelastprocessedtime_command.return_value = 'make_updatelastprocessedtime_command_return_value'

        response = app.test_client().post(f'/api/v1/robots/notifications/',
                                          content_type='application/json', data=json.dumps(notified_data))
        assert response.status_code == 200
        assert response.json == {
            'result': 'success',
            'processed_data': [],
            'ignored_data': [data],
        }
        assert mocked_api.orion.get_entity.call_count == 1
        assert mocked_api.orion.get_entity.call_args == call(const.FIWARE_SERVICE,
                                                             const.DELIVERY_ROBOT_SERVICEPATH,
                                                             const.DELIVERY_ROBOT_TYPE,
                                                             robot_id)
        assert mocked_api.orion.make_updatelastprocessedtime_command.call_count == 1
        assert mocked_api.orion.make_updatelastprocessedtime_command.call_args == call(dateutil.parser.parse(time))
        assert mocked_api.orion.make_updatemode_command.call_count == 0
        assert mocked_api.orion.send_command.call_count == 1
        assert mocked_api.orion.send_command.call_args == call(const.FIWARE_SERVICE,
                                                               const.DELIVERY_ROBOT_SERVICEPATH,
                                                               const.DELIVERY_ROBOT_TYPE,
                                                               robot_id,
                                                               'make_updatelastprocessedtime_command_return_value')
        assert mocked_api.orion.make_robotui_sendstate_command.call_count == 0
        assert mocked_api.orion.make_delivery_robot_command.call_count == 0
        assert mocked_api.orion.make_emergency_command.call_count == 0
        assert mocked_api.orion.make_robotui_sendtokeninfo_command.call_count == 0
        assert mocked_api.CommonMixin.waypoint().estimate_routes.call_count == 0
        assert mocked_api.CommonMixin.waypoint().get_places.call_count == 0
        assert mocked_api.CommonMixin.waypoint().get_waypoints.call_count == 0
        assert mocked_api.Token.get.call_count == 0
        assert mocked_api.Token.get.return_value.get_lock.call_count == 0
        assert mocked_api.MongoThrottling.lock.call_count == 1
        assert mocked_api.MongoThrottling.lock.call_args == call(robot_id, dateutil.parser.parse(time))

    @pytest.mark.parametrize('current_mode', [
        '', 'navi', 'error',
    ])
    @pytest.mark.parametrize('current_state', [
        '', 'standby', 'moving', 'picking', 'delivering',
    ])
    @pytest.mark.parametrize('nw_value, order, c, next_state', [
        (
            {'destination': 'A_id', 'to': 'A_id'},
            {'source': 'A_id', 'via': [], 'destination': None},
            'warehouse',
            'standby',
        ),
        (
            {'destination': 'A_id', 'to': 'A_id'},
            {'source': None, 'via': [], 'destination': 'A_id'},
            'ordering',
            'delivering',
        ),
        (
            {'destination': 'A_id', 'to': 'A_id'},
            {'source': None, 'via': [], 'destination': 'A_id'},
            'warehouse',
            'picking',
        ),
        (
            {'destination': 'A_id', 'to': 'A_id'},
            {'source': None, 'via': ['A_id'], 'destination': None},
            'warehouse',
            'picking',
        ),
        (
            {'destination': 'A_id', 'to': 'A_id'},
            {'source': None, 'via': [], 'destination': None},
            'warehouse',
            'moving',
        ),
        (
            {'destination': 'A_id', 'to': 'A_id', 'action': {}},
            {'source': 'A_id', 'via': [], 'destination': None},
            'warehouse',
            'standby',
        ),
        (
            {'destination': 'A_id', 'to': 'A_id', 'action': {'token': 'token_a', 'waiting_route': {}}},
            {'source': 'A_id', 'via': [], 'destination': None},
            'warehouse',
            'standby',
        ),
        (
            {'destination': 'A_id', 'to': 'A_id', 'action': {'func': 'lock', 'waiting_route': {}}},
            {'source': 'A_id', 'via': [], 'destination': None},
            'warehouse',
            'standby',
        ),
        (
            {'destination': 'A_id', 'to': 'A_id', 'action': {'func': 'lock', 'token': 'token_a'}},
            {'source': 'A_id', 'via': [], 'destination': None},
            'warehouse',
            'standby',
        ),
        (
            {'destination': 'A_id', 'to': 'A_id', 'action': {'func': None, 'token': 'token_a', 'waiting_route': {}}},
            {'source': 'A_id', 'via': [], 'destination': None},
            'warehouse',
            'standby',
        ),
        (
            {'destination': 'A_id', 'to': 'A_id', 'action': {'func': {}, 'token': 'token_a', 'waiting_route': {}}},
            {'source': 'A_id', 'via': [], 'destination': None},
            'warehouse',
            'standby',
        ),
        (
            {'destination': 'A_id', 'to': 'A_id', 'action': {'func': 'lock', 'token': None, 'waiting_route': {}}},
            {'source': 'A_id', 'via': [], 'destination': None},
            'warehouse',
            'standby',
        ),
        (
            {'destination': 'A_id', 'to': 'A_id', 'action': {'func': 'lock', 'token': '', 'waiting_route': {}}},
            {'source': 'A_id', 'via': [], 'destination': None},
            'warehouse',
            'standby',
        ),
        (
            {'destination': 'A_id', 'to': 'A_id', 'action': {'func': 'lock', 'token': {'a': 'A'}, 'waiting_route': {}}},
            {'source': 'A_id', 'via': [], 'destination': None},
            'warehouse',
            'standby',
        ),
    ])
    def test_not_standby_to_standby_invalid_action(self, app, mocked_api,
                                                   current_mode, current_state, nw_value, order, c, next_state):
        robot_id = 'robot_01'
        next_mode = 'standby'
        time = '2020-01-02T03:04:05.678+09:00'
        last_processed_time = '2020-01-02T03:04:05.000+09:00'
        ui_id = 'ui_01'
        dest_name = 'dest_name'

        data = {
            'id': robot_id,
            'mode': {
                'value': next_mode,
            },
            'time': {
                'value': time,
            },
        }

        notified_data = {
            'data': [data]
        }

        def get_entity(fs, fsp, t, id):
            if t == const.DELIVERY_ROBOT_TYPE:
                return {
                    'mode': {
                        'value': None,
                    },
                    'navigating_waypoints': {
                        'value': nw_value,
                    },
                    'current_mode': {
                        'value': current_mode,
                    },
                    'current_state': {
                        'value': current_state,
                    },
                    'last_processed_time': {
                        'value': last_processed_time,
                    },
                    'order': {
                        'value': order,
                    },
                    'caller': {
                        'value': c,
                    }
                }
            else:
                return {
                    'name': {
                        'value': dest_name
                    }
                }

        mocked_api.orion.get_entity.side_effect = get_entity
        mocked_api.orion.make_updatelastprocessedtime_command.return_value = 'make_updatelastprocessedtime_command_return_value'
        mocked_api.orion.make_updatemode_command.return_value = 'make_updatemode_command_return_value'
        mocked_api.orion.make_updatestate_command.return_value = 'make_updatestate_command_return_value'
        mocked_api.orion.make_robotui_sendstate_command.return_value = 'make_robotui_sendstate_command_return_value'

        response = app.test_client().post(f'/api/v1/robots/notifications/',
                                          content_type='application/json', data=json.dumps(notified_data))
        assert response.status_code == 200
        assert response.json == {
            'result': 'success',
            'processed_data': [data],
            'ignored_data': [],
        }

        if next_state == current_state:
            assert mocked_api.orion.get_entity.call_count == 1
            assert mocked_api.orion.get_entity.call_args_list[0] == call(const.FIWARE_SERVICE,
                                                                         const.DELIVERY_ROBOT_SERVICEPATH,
                                                                         const.DELIVERY_ROBOT_TYPE,
                                                                         robot_id)
        else:
            assert mocked_api.orion.get_entity.call_count == 3
            for i in range(2):
                assert mocked_api.orion.get_entity.call_args_list[i] == call(const.FIWARE_SERVICE,
                                                                             const.DELIVERY_ROBOT_SERVICEPATH,
                                                                             const.DELIVERY_ROBOT_TYPE,
                                                                             robot_id)
            assert mocked_api.orion.get_entity.call_args_list[2] == call(const.FIWARE_SERVICE,
                                                                         const.DELIVERY_ROBOT_SERVICEPATH,
                                                                         const.PLACE_TYPE,
                                                                         'A_id')
        assert mocked_api.orion.make_updatelastprocessedtime_command.call_count == 1
        assert mocked_api.orion.make_updatelastprocessedtime_command.call_args == call(dateutil.parser.parse(time))
        assert mocked_api.orion.make_updatemode_command.call_count == 1
        assert mocked_api.orion.make_updatemode_command.call_args == call(next_mode)
        if next_state == current_state:
            assert mocked_api.orion.make_updatestate_command.call_count == 0
            assert mocked_api.orion.send_command.call_count == 2
            assert mocked_api.orion.make_robotui_sendstate_command.call_count == 0
        else:
            assert mocked_api.orion.make_updatestate_command.call_count == 1
            assert mocked_api.orion.make_updatestate_command.call_args == call(next_state)
            assert mocked_api.orion.make_robotui_sendstate_command.call_count == 1
            assert mocked_api.orion.make_robotui_sendstate_command.call_args == call(next_state, dest_name)
            assert mocked_api.orion.send_command.call_count == 4
        assert mocked_api.orion.send_command.call_args_list[0] == call(const.FIWARE_SERVICE,
                                                                       const.DELIVERY_ROBOT_SERVICEPATH,
                                                                       const.DELIVERY_ROBOT_TYPE,
                                                                       robot_id,
                                                                       'make_updatelastprocessedtime_command_return_value')
        assert mocked_api.orion.send_command.call_args_list[1] == call(const.FIWARE_SERVICE,
                                                                       const.DELIVERY_ROBOT_SERVICEPATH,
                                                                       const.DELIVERY_ROBOT_TYPE,
                                                                       robot_id,
                                                                       'make_updatemode_command_return_value')
        if next_state != current_state:
            assert mocked_api.orion.send_command.call_args_list[2] == call(const.FIWARE_SERVICE,
                                                                           const.DELIVERY_ROBOT_SERVICEPATH,
                                                                           const.DELIVERY_ROBOT_TYPE,
                                                                           robot_id,
                                                                           'make_updatestate_command_return_value')
            assert mocked_api.orion.send_command.call_args_list[3] == call(const.FIWARE_SERVICE,
                                                                           const.ROBOT_UI_SERVICEPATH,
                                                                           const.ROBOT_UI_TYPE,
                                                                           ui_id,
                                                                           'make_robotui_sendstate_command_return_value')
        assert mocked_api.orion.make_robotui_sendtokeninfo_command.call_count == 0
        assert mocked_api.orion.make_delivery_robot_command.call_count == 0
        assert mocked_api.orion.make_emergency_command.call_count == 0
        assert mocked_api.CommonMixin.waypoint().estimate_routes.call_count == 0
        assert mocked_api.CommonMixin.waypoint().get_places.call_count == 0
        assert mocked_api.CommonMixin.waypoint().get_waypoints.call_count == 0
        assert mocked_api.Token.get.call_count == 0
        assert mocked_api.Token.get.return_value.get_lock.call_count == 0
        assert mocked_api.MongoThrottling.lock.call_count == 1
        assert mocked_api.MongoThrottling.lock.call_args == call(robot_id, dateutil.parser.parse(time))

    @pytest.mark.parametrize('current_mode', [
        '', 'navi', 'error',
    ])
    @pytest.mark.parametrize('current_state', [
        '', 'standby', 'moving', 'picking', 'delivering',
    ])
    @pytest.mark.parametrize('nw_value, order, c, next_state', [
        (
            {'destination': 'A_id', 'to': 'A_id', 'action': {'func': 'dummy', 'token': 'token_a', 'waiting_route': {}}},
            {'source': 'A_id', 'via': [], 'destination': None},
            'warehouse',
            'standby',
        ),
    ])
    def test_not_standby_to_standby_unknown_action(self, app, mocked_api,
                                                   current_mode, current_state, nw_value, order, c, next_state):
        robot_id = 'robot_01'
        next_mode = 'standby'
        time = '2020-01-02T03:04:05.678+09:00'
        last_processed_time = '2020-01-02T03:04:05.000+09:00'
        ui_id = 'ui_01'
        dest_name = 'dest_name'

        data = {
            'id': robot_id,
            'mode': {
                'value': next_mode,
            },
            'time': {
                'value': time,
            },
        }

        notified_data = {
            'data': [data]
        }

        def get_entity(fs, fsp, t, id):
            if t == const.DELIVERY_ROBOT_TYPE:
                return {
                    'mode': {
                        'value': None,
                    },
                    'navigating_waypoints': {
                        'value': nw_value,
                    },
                    'current_mode': {
                        'value': current_mode,
                    },
                    'current_state': {
                        'value': current_state,
                    },
                    'last_processed_time': {
                        'value': last_processed_time,
                    },
                    'order': {
                        'value': order,
                    },
                    'caller': {
                        'value': c,
                    }
                }
            else:
                return {
                    'name': {
                        'value': dest_name
                    }
                }

        mocked_api.orion.get_entity.side_effect = get_entity
        mocked_api.orion.make_updatelastprocessedtime_command.return_value = 'make_updatelastprocessedtime_command_return_value'
        mocked_api.orion.make_updatemode_command.return_value = 'make_updatemode_command_return_value'
        mocked_api.orion.make_updatestate_command.return_value = 'make_updatestate_command_return_value'
        mocked_api.orion.make_robotui_sendstate_command.return_value = 'make_robotui_sendstate_command_return_value'

        response = app.test_client().post(f'/api/v1/robots/notifications/',
                                          content_type='application/json', data=json.dumps(notified_data))
        assert response.status_code == 200
        assert response.json == {
            'result': 'success',
            'processed_data': [data],
            'ignored_data': [],
        }

        if next_state == current_state:
            assert mocked_api.orion.get_entity.call_count == 1
            assert mocked_api.orion.get_entity.call_args_list[0] == call(const.FIWARE_SERVICE,
                                                                         const.DELIVERY_ROBOT_SERVICEPATH,
                                                                         const.DELIVERY_ROBOT_TYPE,
                                                                         robot_id)
        else:
            assert mocked_api.orion.get_entity.call_count == 3
            for i in range(2):
                assert mocked_api.orion.get_entity.call_args_list[i] == call(const.FIWARE_SERVICE,
                                                                             const.DELIVERY_ROBOT_SERVICEPATH,
                                                                             const.DELIVERY_ROBOT_TYPE,
                                                                             robot_id)
            assert mocked_api.orion.get_entity.call_args_list[2] == call(const.FIWARE_SERVICE,
                                                                         const.DELIVERY_ROBOT_SERVICEPATH,
                                                                         const.PLACE_TYPE,
                                                                         'A_id')
        assert mocked_api.orion.make_updatelastprocessedtime_command.call_count == 1
        assert mocked_api.orion.make_updatelastprocessedtime_command.call_args == call(dateutil.parser.parse(time))
        assert mocked_api.orion.make_updatemode_command.call_count == 1
        assert mocked_api.orion.make_updatemode_command.call_args == call(next_mode)
        if next_state == current_state:
            assert mocked_api.orion.make_updatestate_command.call_count == 0
            assert mocked_api.orion.send_command.call_count == 2
            assert mocked_api.orion.make_robotui_sendstate_command.call_count == 0
        else:
            assert mocked_api.orion.make_updatestate_command.call_count == 1
            assert mocked_api.orion.make_updatestate_command.call_args == call(next_state)
            assert mocked_api.orion.make_robotui_sendstate_command.call_count == 1
            assert mocked_api.orion.make_robotui_sendstate_command.call_args == call(next_state, dest_name)
            assert mocked_api.orion.send_command.call_count == 4
        assert mocked_api.orion.send_command.call_args_list[0] == call(const.FIWARE_SERVICE,
                                                                       const.DELIVERY_ROBOT_SERVICEPATH,
                                                                       const.DELIVERY_ROBOT_TYPE,
                                                                       robot_id,
                                                                       'make_updatelastprocessedtime_command_return_value')
        assert mocked_api.orion.send_command.call_args_list[1] == call(const.FIWARE_SERVICE,
                                                                       const.DELIVERY_ROBOT_SERVICEPATH,
                                                                       const.DELIVERY_ROBOT_TYPE,
                                                                       robot_id,
                                                                       'make_updatemode_command_return_value')
        if next_state != current_state:
            assert mocked_api.orion.send_command.call_args_list[2] == call(const.FIWARE_SERVICE,
                                                                           const.DELIVERY_ROBOT_SERVICEPATH,
                                                                           const.DELIVERY_ROBOT_TYPE,
                                                                           robot_id,
                                                                           'make_updatestate_command_return_value')
            assert mocked_api.orion.send_command.call_args_list[3] == call(const.FIWARE_SERVICE,
                                                                           const.ROBOT_UI_SERVICEPATH,
                                                                           const.ROBOT_UI_TYPE,
                                                                           ui_id,
                                                                           'make_robotui_sendstate_command_return_value')
        assert mocked_api.Token.get.call_count == 1
        assert mocked_api.Token.get.call_args == call('token_a')
        assert mocked_api.Token.get.return_value.get_lock.call_count == 0
        assert mocked_api.orion.make_delivery_robot_command.call_count == 0
        assert mocked_api.orion.make_emergency_command.call_count == 0
        assert mocked_api.orion.make_robotui_sendtokeninfo_command.call_count == 0
        assert mocked_api.CommonMixin.waypoint().estimate_routes.call_count == 0
        assert mocked_api.CommonMixin.waypoint().get_places.call_count == 0
        assert mocked_api.CommonMixin.waypoint().get_waypoints.call_count == 0
        assert mocked_api.MongoThrottling.lock.call_count == 1
        assert mocked_api.MongoThrottling.lock.call_args == call(robot_id, dateutil.parser.parse(time))

    @pytest.mark.parametrize('waiting_route', [
        {}, {'via': ['A_id'], 'to': 'B_id'},
    ])
    def test_navi_to_standby_has_lock(self, app, mocked_api, waiting_route):
        robot_id = 'robot_01'
        next_mode = 'standby'
        time = '2020-01-02T03:04:05.678+09:00'
        current_mode = 'navi'
        current_state = const.STATE_MOVING
        last_processed_time = '2020-01-02T03:04:05.000+09:00'
        ui_id = 'ui_01'
        nw_value = {'destination': 'A_id', 'to': 'A_id', 'action': {'func': 'lock', 'token': 'token_a', 'waiting_route': ''}}
        order = {'source': None, 'via': ['A_id'], 'destination': None}
        nw_value['action']['waiting_route'] = waiting_route
        rwl = [
            {
                'to': 'E_id', 'destination': 'dest_id', 'action': 'action_0',
                'waypoints': [
                    {'point': 'pC', 'angle': None}, {'point': 'pD', 'angle': None}, {'point': 'pE', 'angle': 'aE'},
                ]
            },
        ]

        data = {
            'id': robot_id,
            'mode': {
                'value': next_mode,
            },
            'time': {
                'value': time,
            },
        }

        notified_data = {
            'data': [data]
        }

        def get_entity(fs, fsp, t, id):
            if t == const.DELIVERY_ROBOT_TYPE:
                return {
                    'mode': {
                        'value': None,
                    },
                    'navigating_waypoints': {
                        'value': nw_value,
                    },
                    'current_mode': {
                        'value': current_mode,
                    },
                    'current_state': {
                        'value': current_state,
                    },
                    'last_processed_time': {
                        'value': last_processed_time,
                    },
                    'order': {
                        'value': order,
                    },
                    'caller': {
                        'value': '',
                    },
                    'remaining_waypoints_list': {
                        'value': rwl,
                    },
                    'send_cmd_status': {
                        'value': 'OK',
                    },
                    'send_cmd_info': {
                        'value': {
                            'result': 'ack'
                        }
                    },
                }
            else:
                return {
                    'name': {
                        'value': 'dest_name'
                    }
                }

        mocked_api.orion.get_entity.side_effect = get_entity
        mocked_api.orion.make_delivery_robot_command.return_value = 'make_delivery_robot_command_return_value'
        mocked_api.orion.make_updatelastprocessedtime_command.return_value = 'make_updatelastprocessedtime_command_return_value'
        mocked_api.orion.make_updatemode_command.return_value = 'make_updatemode_command_return_value'
        mocked_api.orion.make_updatestate_command.return_value = 'make_updatestate_command_return_value'
        mocked_api.orion.make_robotui_sendstate_command.return_value = 'make_robotui_sendstate_command_return_value'
        mocked_api.orion.make_robotui_sendtokeninfo_command.return_value = 'make_robotui_sendtokeninfo_command_return_value'

        mocked_api.Token.get.return_value.get_lock.return_value = True

        response = app.test_client().post(f'/api/v1/robots/notifications/',
                                          content_type='application/json', data=json.dumps(notified_data))
        assert response.status_code == 200
        assert response.json == {
            'result': 'success',
            'processed_data': [data],
            'ignored_data': [],
        }
        assert mocked_api.orion.get_entity.call_count == 5
        for i in range(4):
            assert mocked_api.orion.get_entity.call_args_list[i] == call(const.FIWARE_SERVICE,
                                                                         const.DELIVERY_ROBOT_SERVICEPATH,
                                                                         const.DELIVERY_ROBOT_TYPE,
                                                                         robot_id)
        assert mocked_api.orion.get_entity.call_args_list[4] == call(const.FIWARE_SERVICE,
                                                                     const.DELIVERY_ROBOT_SERVICEPATH,
                                                                     const.PLACE_TYPE,
                                                                     'A_id')
        assert mocked_api.orion.make_delivery_robot_command.call_count == 1
        assert mocked_api.orion.make_delivery_robot_command.call_args == call('navi',
                                                                              rwl[0]['waypoints'],
                                                                              rwl[0],
                                                                              [],
                                                                              None,
                                                                              None,
                                                                              None)
        assert mocked_api.orion.make_updatelastprocessedtime_command.call_count == 1
        assert mocked_api.orion.make_updatelastprocessedtime_command.call_args == call(dateutil.parser.parse(time))
        assert mocked_api.orion.make_updatemode_command.call_count == 1
        assert mocked_api.orion.make_updatemode_command.call_args == call(next_mode)
        assert mocked_api.orion.make_updatestate_command.call_count == 1
        assert mocked_api.orion.make_updatestate_command.call_args == call(const.STATE_PICKING)
        assert mocked_api.orion.make_robotui_sendstate_command.call_count == 1
        assert mocked_api.orion.make_robotui_sendstate_command.call_args == call(const.STATE_PICKING, 'dest_name')
        assert mocked_api.orion.make_robotui_sendtokeninfo_command.call_count == 1
        assert mocked_api.orion.make_robotui_sendtokeninfo_command.call_args == call(mocked_api.Token.get.return_value,
                                                                                     api.TokenMode.LOCK)
        assert mocked_api.orion.send_command.call_count == 6
        assert mocked_api.orion.send_command.call_args_list[0] == call(const.FIWARE_SERVICE,
                                                                       const.DELIVERY_ROBOT_SERVICEPATH,
                                                                       const.DELIVERY_ROBOT_TYPE,
                                                                       robot_id,
                                                                       'make_updatelastprocessedtime_command_return_value')
        assert mocked_api.orion.send_command.call_args_list[1] == call(const.FIWARE_SERVICE,
                                                                       const.DELIVERY_ROBOT_SERVICEPATH,
                                                                       const.DELIVERY_ROBOT_TYPE,
                                                                       robot_id,
                                                                       'make_updatemode_command_return_value')
        assert mocked_api.orion.send_command.call_args_list[2] == call(const.FIWARE_SERVICE,
                                                                       const.DELIVERY_ROBOT_SERVICEPATH,
                                                                       const.DELIVERY_ROBOT_TYPE,
                                                                       robot_id,
                                                                       'make_delivery_robot_command_return_value')
        assert mocked_api.orion.send_command.call_args_list[3] == call(const.FIWARE_SERVICE,
                                                                       const.ROBOT_UI_SERVICEPATH,
                                                                       const.ROBOT_UI_TYPE,
                                                                       ui_id,
                                                                       'make_robotui_sendtokeninfo_command_return_value')
        assert mocked_api.orion.send_command.call_args_list[4] == call(const.FIWARE_SERVICE,
                                                                       const.DELIVERY_ROBOT_SERVICEPATH,
                                                                       const.DELIVERY_ROBOT_TYPE,
                                                                       robot_id,
                                                                       'make_updatestate_command_return_value')
        assert mocked_api.orion.send_command.call_args_list[5] == call(const.FIWARE_SERVICE,
                                                                       const.ROBOT_UI_SERVICEPATH,
                                                                       const.ROBOT_UI_TYPE,
                                                                       ui_id,
                                                                       'make_robotui_sendstate_command_return_value')
        assert mocked_api.Token.get.call_count == 1
        assert mocked_api.Token.get.call_args == call('token_a')
        assert mocked_api.Token.get.return_value.get_lock.call_count == 1
        assert mocked_api.Token.get.return_value.get_lock.call_args == call(robot_id,)
        assert mocked_api.orion.make_delivery_robot_command.call_count == 1
        assert mocked_api.orion.make_delivery_robot_command.call_args_list[0] == call('navi',
                                                                                      rwl[0]['waypoints'],
                                                                                      rwl[0],
                                                                                      [],
                                                                                      None,
                                                                                      None,
                                                                                      None)
        assert mocked_api.orion.make_emergency_command.call_count == 0
        assert mocked_api.CommonMixin.waypoint().estimate_routes.call_count == 0
        assert mocked_api.CommonMixin.waypoint().get_places.call_count == 0
        assert mocked_api.CommonMixin.waypoint().get_waypoints.call_count == 0
        assert mocked_api.MongoThrottling.lock.call_count == 1
        assert mocked_api.MongoThrottling.lock.call_args == call(robot_id, dateutil.parser.parse(time))

    @pytest.mark.parametrize('waiting_route', [
        {}, {'via': ['A_id'], 'to': 'B_id'},
    ])
    def test_navi_to_standby_has_not_lock(self, app, mocked_api, waiting_route):
        robot_id = 'robot_01'
        next_mode = 'standby'
        time = '2020-01-02T03:04:05.678+09:00'
        current_mode = 'navi'
        current_state = const.STATE_MOVING
        last_processed_time = '2020-01-02T03:04:05.000+09:00'
        ui_id = 'ui_01'
        nw_value = {'destination': 'A_id', 'to': 'A_id', 'action': {'func': 'lock', 'token': 'token_a', 'waiting_route': ''}}
        order = {'source': None, 'via': ['A_id'], 'destination': None}
        nw_value['action']['waiting_route'] = waiting_route
        rwl = [
            {
                'to': 'E_id', 'destination': 'dest_id', 'action': 'action_0',
                'waypoints': [
                    {'point': 'pC', 'angle': None}, {'point': 'pD', 'angle': None}, {'point': 'pE', 'angle': 'aE'},
                ]
            },
        ]

        data = {
            'id': robot_id,
            'mode': {
                'value': next_mode,
            },
            'time': {
                'value': time,
            },
        }

        notified_data = {
            'data': [data]
        }

        def get_entity(fs, fsp, t, id):
            if t == const.DELIVERY_ROBOT_TYPE:
                return {
                    'mode': {
                        'value': None,
                    },
                    'navigating_waypoints': {
                        'value': nw_value,
                    },
                    'current_mode': {
                        'value': current_mode,
                    },
                    'current_state': {
                        'value': current_state,
                    },
                    'last_processed_time': {
                        'value': last_processed_time,
                    },
                    'order': {
                        'value': order,
                    },
                    'caller': {
                        'value': '',
                    },
                    'remaining_waypoints_list': {
                        'value': rwl,
                    },
                    'send_cmd_status': {
                        'value': 'OK',
                    },
                    'send_cmd_info': {
                        'value': {
                            'result': 'ack'
                        }
                    },
                }
            else:
                return {
                    'name': {
                        'value': 'dest_name'
                    }
                }

        mocked_api.orion.get_entity.side_effect = get_entity
        mocked_api.orion.make_delivery_robot_command.return_value = 'make_delivery_robot_command_return_value'
        mocked_api.orion.make_updatelastprocessedtime_command.return_value = 'make_updatelastprocessedtime_command_return_value'
        mocked_api.orion.make_updatemode_command.return_value = 'make_updatemode_command_return_value'
        mocked_api.orion.make_updatestate_command.return_value = 'make_updatestate_command_return_value'
        mocked_api.orion.make_robotui_sendstate_command.return_value = 'make_robotui_sendstate_command_return_value'
        mocked_api.orion.make_robotui_sendtokeninfo_command.return_value = 'make_robotui_sendtokeninfo_command_return_value'

        refuge_waypoints = [{'point': 'pB', 'angle': 'aB'}]
        mocked_api.Token.get.return_value.get_lock.return_value = False
        mocked_api.Waypoint.return_value.get_places.return_value = {'A_id': 'place_A', 'B_id': 'place_B'}
        mocked_api.Waypoint.return_value.get_waypoints.return_value = refuge_waypoints
        response = app.test_client().post(f'/api/v1/robots/notifications/',
                                          content_type='application/json', data=json.dumps(notified_data))
        assert response.status_code == 200
        assert response.json == {
            'result': 'success',
            'processed_data': [data],
            'ignored_data': [],
        }
        if waiting_route:
            assert mocked_api.orion.get_entity.call_count == 5
            lo = 4
        else:
            assert mocked_api.orion.get_entity.call_count == 3
            lo = 2

        for i in range(lo):
            assert mocked_api.orion.get_entity.call_args_list[i] == call(const.FIWARE_SERVICE,
                                                                         const.DELIVERY_ROBOT_SERVICEPATH,
                                                                         const.DELIVERY_ROBOT_TYPE,
                                                                         robot_id)
        assert mocked_api.orion.get_entity.call_args_list[lo] == call(const.FIWARE_SERVICE,
                                                                      const.DELIVERY_ROBOT_SERVICEPATH,
                                                                      const.PLACE_TYPE,
                                                                      'A_id')

        assert mocked_api.orion.make_updatelastprocessedtime_command.call_count == 1
        assert mocked_api.orion.make_updatelastprocessedtime_command.call_args == call(dateutil.parser.parse(time))
        assert mocked_api.orion.make_updatemode_command.call_count == 1
        assert mocked_api.orion.make_updatemode_command.call_args == call(next_mode)
        assert mocked_api.orion.make_updatestate_command.call_count == 1
        assert mocked_api.orion.make_updatestate_command.call_args == call(const.STATE_PICKING)
        assert mocked_api.orion.make_robotui_sendstate_command.call_count == 1
        assert mocked_api.orion.make_robotui_sendstate_command.call_args == call(const.STATE_PICKING, 'dest_name')

        if waiting_route:
            assert mocked_api.orion.make_delivery_robot_command.call_count == 1
            assert mocked_api.orion.make_delivery_robot_command.call_args == call('navi',
                                                                                  refuge_waypoints,
                                                                                  {
                                                                                      'to': 'B_id',
                                                                                      'destination': 'A_id',
                                                                                      'action': {
                                                                                          'func': '',
                                                                                          'token': '',
                                                                                          'waiting_route': {}
                                                                                      },
                                                                                      'waypoints': refuge_waypoints,
                                                                                  },
                                                                                  None,
                                                                                  None,
                                                                                  None,
                                                                                  None)
        else:
            assert mocked_api.orion.make_delivery_robot_command.call_count == 0

        assert mocked_api.orion.make_robotui_sendtokeninfo_command.call_count == 1
        assert mocked_api.orion.make_robotui_sendtokeninfo_command.call_args == call(mocked_api.Token.get.return_value,
                                                                                     api.TokenMode.SUSPEND)

        if waiting_route:
            assert mocked_api.orion.send_command.call_count == 6
        else:
            assert mocked_api.orion.send_command.call_count == 5

        assert mocked_api.orion.send_command.call_args_list[0] == call(const.FIWARE_SERVICE,
                                                                       const.DELIVERY_ROBOT_SERVICEPATH,
                                                                       const.DELIVERY_ROBOT_TYPE,
                                                                       robot_id,
                                                                       'make_updatelastprocessedtime_command_return_value')
        assert mocked_api.orion.send_command.call_args_list[1] == call(const.FIWARE_SERVICE,
                                                                       const.DELIVERY_ROBOT_SERVICEPATH,
                                                                       const.DELIVERY_ROBOT_TYPE,
                                                                       robot_id,
                                                                       'make_updatemode_command_return_value')
        assert mocked_api.orion.send_command.call_args_list[-3] == call(const.FIWARE_SERVICE,
                                                                        const.ROBOT_UI_SERVICEPATH,
                                                                        const.ROBOT_UI_TYPE,
                                                                        ui_id,
                                                                        'make_robotui_sendtokeninfo_command_return_value')
        assert mocked_api.orion.send_command.call_args_list[-2] == call(const.FIWARE_SERVICE,
                                                                        const.DELIVERY_ROBOT_SERVICEPATH,
                                                                        const.DELIVERY_ROBOT_TYPE,
                                                                        robot_id,
                                                                        'make_updatestate_command_return_value')
        assert mocked_api.orion.send_command.call_args_list[-1] == call(const.FIWARE_SERVICE,
                                                                        const.ROBOT_UI_SERVICEPATH,
                                                                        const.ROBOT_UI_TYPE,
                                                                        ui_id,
                                                                        'make_robotui_sendstate_command_return_value')
        if waiting_route:
            assert mocked_api.orion.send_command.call_args_list[2] == call(const.FIWARE_SERVICE,
                                                                           const.DELIVERY_ROBOT_SERVICEPATH,
                                                                           const.DELIVERY_ROBOT_TYPE,
                                                                           robot_id,
                                                                           'make_delivery_robot_command_return_value')
        assert mocked_api.Token.get.call_count == 1
        assert mocked_api.Token.get.call_args == call('token_a')
        assert mocked_api.orion.make_emergency_command.call_count == 0
        assert mocked_api.CommonMixin.waypoint().estimate_routes.call_count == 0
        if waiting_route:
            assert mocked_api.CommonMixin.waypoint().get_places.call_count == 1
            assert mocked_api.CommonMixin.waypoint().get_places.call_args == call([['A_id', 'B_id']])
            assert mocked_api.CommonMixin.waypoint().get_waypoints.call_count == 1
            assert mocked_api.CommonMixin.waypoint().get_waypoints.call_args == call(['place_A'], ['place_B'])
        else:
            assert mocked_api.CommonMixin.waypoint().get_places.call_count == 0
            assert mocked_api.CommonMixin.waypoint().get_waypoints.call_count == 0
        assert mocked_api.MongoThrottling.lock.call_count == 1
        assert mocked_api.MongoThrottling.lock.call_args == call(robot_id, dateutil.parser.parse(time))

    @pytest.mark.parametrize('new_owner_id, new_ui_id', [
        (None, None),
        ('robot_02', 'ui_02'),
    ])
    def test_navi_to_standby_release(self, app, mocked_api, new_owner_id, new_ui_id):
        robot_id = 'robot_01'
        next_mode = 'standby'
        time = '2020-01-02T03:04:05.678+09:00'
        current_mode = 'navi'
        current_state = const.STATE_MOVING
        last_processed_time = '2020-01-02T03:04:05.000+09:00'
        ui_id = 'ui_01'
        nw_value = {'destination': 'A_id', 'to': 'A_id', 'action': {'func': 'release', 'token': 'token_a', 'waiting_route': {}}}
        order = {'source': None, 'via': ['A_id'], 'destination': None}
        rwl = [
            {
                'to': 'E_id', 'destination': 'dest_id', 'action': 'action_0',
                'waypoints': [
                    {'point': 'pC', 'angle': None}, {'point': 'pD', 'angle': None}, {'point': 'pE', 'angle': 'aE'},
                ]
            },
        ]

        data = {
            'id': robot_id,
            'mode': {
                'value': next_mode,
            },
            'time': {
                'value': time,
            },
        }

        notified_data = {
            'data': [data]
        }

        def get_entity(fs, fsp, t, id):
            if t == const.DELIVERY_ROBOT_TYPE:
                return {
                    'mode': {
                        'value': None,
                    },
                    'navigating_waypoints': {
                        'value': nw_value,
                    },
                    'current_mode': {
                        'value': current_mode,
                    },
                    'current_state': {
                        'value': current_state,
                    },
                    'last_processed_time': {
                        'value': last_processed_time,
                    },
                    'order': {
                        'value': order,
                    },
                    'caller': {
                        'value': '',
                    },
                    'remaining_waypoints_list': {
                        'value': rwl,
                    },
                    'send_cmd_status': {
                        'value': 'OK',
                    },
                    'send_cmd_info': {
                        'value': {
                            'result': 'ack'
                        }
                    },
                }
            else:
                return {
                    'name': {
                        'value': 'dest_name'
                    }
                }

        mocked_api.orion.get_entity.side_effect = get_entity
        mocked_api.orion.make_delivery_robot_command.return_value = 'make_delivery_robot_command_return_value'
        mocked_api.orion.make_updatelastprocessedtime_command.return_value = 'make_updatelastprocessedtime_command_return_value'
        mocked_api.orion.make_updatemode_command.return_value = 'make_updatemode_command_return_value'
        mocked_api.orion.make_updatestate_command.return_value = 'make_updatestate_command_return_value'
        mocked_api.orion.make_robotui_sendstate_command.return_value = 'make_robotui_sendstate_command_return_value'
        mocked_api.orion.make_robotui_sendtokeninfo_command.return_value = 'make_robotui_sendtokeninfo_command_return_value'

        mocked_api.Token.get.return_value.release_lock.return_value = new_owner_id

        response = app.test_client().post(f'/api/v1/robots/notifications/',
                                          content_type='application/json', data=json.dumps(notified_data))
        assert response.status_code == 200
        assert response.json == {
            'result': 'success',
            'processed_data': [data],
            'ignored_data': [],
        }

        if new_owner_id:
            assert mocked_api.orion.get_entity.call_count == 7
            for i in range(2):
                assert mocked_api.orion.get_entity.call_args_list[i+3] == call(const.FIWARE_SERVICE,
                                                                               const.DELIVERY_ROBOT_SERVICEPATH,
                                                                               const.DELIVERY_ROBOT_TYPE,
                                                                               new_owner_id)
        else:
            assert mocked_api.orion.get_entity.call_count == 5

        for i in range(2):
            assert mocked_api.orion.get_entity.call_args_list[i] == call(const.FIWARE_SERVICE,
                                                                         const.DELIVERY_ROBOT_SERVICEPATH,
                                                                         const.DELIVERY_ROBOT_TYPE,
                                                                         robot_id)
        assert mocked_api.orion.get_entity.call_args_list[-2] == call(const.FIWARE_SERVICE,
                                                                      const.DELIVERY_ROBOT_SERVICEPATH,
                                                                      const.DELIVERY_ROBOT_TYPE,
                                                                      robot_id)
        assert mocked_api.orion.get_entity.call_args_list[-1] == call(const.FIWARE_SERVICE,
                                                                      const.DELIVERY_ROBOT_SERVICEPATH,
                                                                      const.PLACE_TYPE,
                                                                      'A_id')

        assert mocked_api.orion.make_updatelastprocessedtime_command.call_count == 1
        assert mocked_api.orion.make_updatelastprocessedtime_command.call_args == call(dateutil.parser.parse(time))
        assert mocked_api.orion.make_updatemode_command.call_count == 1
        assert mocked_api.orion.make_updatemode_command.call_args == call(next_mode)
        assert mocked_api.orion.make_updatestate_command.call_count == 1
        assert mocked_api.orion.make_updatestate_command.call_args == call(const.STATE_PICKING)
        assert mocked_api.orion.make_robotui_sendstate_command.call_count == 1
        assert mocked_api.orion.make_robotui_sendstate_command.call_args == call(const.STATE_PICKING, 'dest_name')

        if new_owner_id:
            assert mocked_api.orion.make_delivery_robot_command.call_count == 2
            assert mocked_api.orion.make_delivery_robot_command.call_args_list[0] == call('navi',
                                                                                          rwl[0]['waypoints'],
                                                                                          rwl[0],
                                                                                          [],
                                                                                          None,
                                                                                          None,
                                                                                          None)
        else:
            assert mocked_api.orion.make_delivery_robot_command.call_count == 1
        assert mocked_api.orion.make_delivery_robot_command.call_args_list[0] == call('navi',
                                                                                      rwl[0]['waypoints'],
                                                                                      rwl[0],
                                                                                      [],
                                                                                      None,
                                                                                      None,
                                                                                      None)

        if new_owner_id:
            assert mocked_api.orion.make_robotui_sendtokeninfo_command.call_count == 3
            assert mocked_api.orion.make_robotui_sendtokeninfo_command.call_args_list[1] == call(
                mocked_api.Token.get.return_value, api.TokenMode.RESUME)
            assert mocked_api.orion.make_robotui_sendtokeninfo_command.call_args_list[2] == call(
                mocked_api.Token.get.return_value, api.TokenMode.LOCK)
        else:
            assert mocked_api.orion.make_robotui_sendtokeninfo_command.call_count == 1
        assert mocked_api.orion.make_robotui_sendtokeninfo_command.call_args_list[0] == call(mocked_api.Token.get.return_value,
                                                                                             api.TokenMode.RELEASE)

        if new_owner_id:
            assert mocked_api.orion.send_command.call_count == 9
            assert mocked_api.orion.send_command.call_args_list[4] == call(const.FIWARE_SERVICE,
                                                                           const.DELIVERY_ROBOT_SERVICEPATH,
                                                                           const.DELIVERY_ROBOT_TYPE,
                                                                           new_owner_id,
                                                                           'make_delivery_robot_command_return_value')
            assert mocked_api.orion.send_command.call_args_list[5] == call(const.FIWARE_SERVICE,
                                                                           const.ROBOT_UI_SERVICEPATH,
                                                                           const.ROBOT_UI_TYPE,
                                                                           new_ui_id,
                                                                           'make_robotui_sendtokeninfo_command_return_value')
            assert mocked_api.orion.send_command.call_args_list[6] == call(const.FIWARE_SERVICE,
                                                                           const.ROBOT_UI_SERVICEPATH,
                                                                           const.ROBOT_UI_TYPE,
                                                                           new_ui_id,
                                                                           'make_robotui_sendtokeninfo_command_return_value')
        else:
            assert mocked_api.orion.send_command.call_count == 6

        assert mocked_api.orion.send_command.call_args_list[0] == call(const.FIWARE_SERVICE,
                                                                       const.DELIVERY_ROBOT_SERVICEPATH,
                                                                       const.DELIVERY_ROBOT_TYPE,
                                                                       robot_id,
                                                                       'make_updatelastprocessedtime_command_return_value')
        assert mocked_api.orion.send_command.call_args_list[1] == call(const.FIWARE_SERVICE,
                                                                       const.DELIVERY_ROBOT_SERVICEPATH,
                                                                       const.DELIVERY_ROBOT_TYPE,
                                                                       robot_id,
                                                                       'make_updatemode_command_return_value')
        assert mocked_api.orion.send_command.call_args_list[2] == call(const.FIWARE_SERVICE,
                                                                       const.DELIVERY_ROBOT_SERVICEPATH,
                                                                       const.DELIVERY_ROBOT_TYPE,
                                                                       robot_id,
                                                                       'make_delivery_robot_command_return_value')
        assert mocked_api.orion.send_command.call_args_list[3] == call(const.FIWARE_SERVICE,
                                                                       const.ROBOT_UI_SERVICEPATH,
                                                                       const.ROBOT_UI_TYPE,
                                                                       ui_id,
                                                                       'make_robotui_sendtokeninfo_command_return_value')
        assert mocked_api.orion.send_command.call_args_list[-2] == call(const.FIWARE_SERVICE,
                                                                        const.DELIVERY_ROBOT_SERVICEPATH,
                                                                        const.DELIVERY_ROBOT_TYPE,
                                                                        robot_id,
                                                                        'make_updatestate_command_return_value')
        assert mocked_api.orion.send_command.call_args_list[-1] == call(const.FIWARE_SERVICE,
                                                                        const.ROBOT_UI_SERVICEPATH,
                                                                        const.ROBOT_UI_TYPE,
                                                                        ui_id,
                                                                        'make_robotui_sendstate_command_return_value')
        assert mocked_api.orion.make_emergency_command.call_count == 0
        assert mocked_api.CommonMixin.waypoint().estimate_routes.call_count == 0
        assert mocked_api.CommonMixin.waypoint().get_places.call_count == 0
        assert mocked_api.CommonMixin.waypoint().get_waypoints.call_count == 0
        assert mocked_api.MongoThrottling.lock.call_count == 1
        assert mocked_api.MongoThrottling.lock.call_args == call(robot_id, dateutil.parser.parse(time))

    def test_mongo_lock_error(self, app, mocked_api):
        robot_id = 'robot_01'
        next_mode = 'standby'
        time = '2020-01-02T03:04:05.678+09:00'

        data = {
            'id': robot_id,
            'mode': {
                'value': next_mode,
            },
            'time': {
                'value': time,
            },
        }

        notified_data = {
            'data': [data]
        }

        mocked_api.MongoThrottling.lock.side_effect = api.MongoLockError
        response = app.test_client().post(f'/api/v1/robots/notifications/',
                                          content_type='application/json', data=json.dumps(notified_data))
        assert response.status_code == 200
        assert response.json == {
            'result': 'success',
            'processed_data': [],
            'ignored_data': [data],
        }

        assert mocked_api.orion.get_entity.call_count == 0
        assert mocked_api.orion.make_delivery_robot_command.call_count == 0
        assert mocked_api.orion.make_emergency_command.call_count == 0
        assert mocked_api.orion.make_updatelastprocessedtime_command.call_count == 0
        assert mocked_api.orion.make_updatemode_command.call_count == 0
        assert mocked_api.orion.make_updatestate_command.call_count == 0
        assert mocked_api.orion.make_robotui_sendstate_command.call_count == 0
        assert mocked_api.orion.make_robotui_sendtokeninfo_command.call_count == 0
        assert mocked_api.orion.send_command.call_count == 0
        assert mocked_api.CommonMixin.waypoint().estimate_routes.call_count == 0
        assert mocked_api.CommonMixin.waypoint().get_places.call_count == 0
        assert mocked_api.CommonMixin.waypoint().get_waypoints.call_count == 0
        assert mocked_api.Token.get.call_count == 0
        assert mocked_api.Token.get.return_value.get_lock.call_count == 0
        assert mocked_api.MongoThrottling.lock.call_count == 1
        assert mocked_api.MongoThrottling.lock.call_args == call(robot_id, dateutil.parser.parse(time))
