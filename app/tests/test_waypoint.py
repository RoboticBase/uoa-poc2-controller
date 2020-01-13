import datetime as dt

from unittest.mock import call

import pytest
import lazy_import

const = lazy_import.lazy_module('src.const')
waypoint = lazy_import.lazy_module('src.waypoint')


@pytest.fixture
def mocked_waypoint(mocker):
    waypoint.orion = mocker.MagicMock()
    yield waypoint


@pytest.mark.usefixtures('setup_environments')
class TestEstimateRoute:
    def return_value_of_query_entity(self, result_places, result_routes, result_source, qc):
        def _result(fs, fsp, t, q):
            if t == const.PLACE_TYPE:
                nonlocal qc
                v = result_places[qc]
                qc += 1
                return v
            else:
                return {
                    'routes': {
                        'value': result_routes,
                    },
                    'source': {
                        'value': result_source,
                    },
                }
        return _result

    def return_value_of_get_entities(self):
        return [
            {'id': 'dest_id', 'pose': {'value': {'point': 'pdest', 'angle': 'adest'}}},
            {'id': 'A_id', 'pose': {'value': {'point': 'pA', 'angle': 'aA'}}},
            {'id': 'B_id', 'pose': {'value': {'point': 'pB', 'angle': 'aB'}}},
            {'id': 'C_id', 'pose': {'value': {'point': 'pC', 'angle': 'aC'}}},
            {'id': 'D_id', 'pose': {'value': {'point': 'pD', 'angle': 'aD'}}},
            {'id': 'E_id', 'pose': {'value': {'point': 'pE', 'angle': 'aE'}}},
            {'id': 'F_id', 'pose': {'value': {'point': 'pF', 'angle': 'aF'}}},
            {'id': 'G_id', 'pose': {'value': {'point': 'pG', 'angle': 'aG'}}},
            {'id': 'H_id', 'pose': {'value': {'point': 'pH', 'angle': 'aH'}}},
            {'id': 'Z_id', 'pose': {'value': {'point': 'pZ', 'angle': 'aZ'}}},
        ]

    @pytest.mark.parametrize('updated', [
        [{'place': 'place_A'}], [{'place': 'place_A'}, {'place': 'place_A'}],
    ])
    @pytest.mark.parametrize('result_routes', [
        [{'from': 'B_id', 'via': ['C_id', 'D_id'], 'to': 'E_id', 'destination': 'dest_id', 'action': 'action_0'}],
        [{'from': 'Z_id', 'via': ['C_id', 'D_id'], 'to': 'E_id', 'destination': 'dest_id', 'action': 'action_0'}],
    ])
    def test_single_via_single_route(self, mocked_waypoint, updated, result_routes):
        robot_id = 'robot_01'
        shipment_list = {
            'destination': {
                'name': 'place_dest',
            },
            'updated': updated,
        }

        result_places = [{'id': 'dest_id'}, {'id': 'A_id'}]
        result_source = 'src'

        mocked_waypoint.orion.query_entity.side_effect = self.return_value_of_query_entity(result_places,
                                                                                           result_routes,
                                                                                           result_source,
                                                                                           0)
        mocked_waypoint.orion.get_entities.return_value = self.return_value_of_get_entities()
        routes, waypoints_list, order = mocked_waypoint.Waypoint().estimate_routes(shipment_list, robot_id)

        assert routes == result_routes
        assert waypoints_list == [
            {
                'to': 'E_id', 'destination': 'dest_id', 'action': 'action_0',
                'waypoints': [
                    {'point': 'pC', 'angle': None}, {'point': 'pD', 'angle': None}, {'point': 'pE', 'angle': 'aE'},
                ]
            },
        ]
        assert order == {'source': 'src', 'via': ['A_id'], 'destination': 'dest_id'}

        assert mocked_waypoint.orion.query_entity.call_count == 3
        assert mocked_waypoint.orion.query_entity.call_args_list[0] == call(
            const.FIWARE_SERVICE, const.DELIVERY_ROBOT_SERVICEPATH, const.PLACE_TYPE, 'name==place_dest')
        assert mocked_waypoint.orion.query_entity.call_args_list[1] == call(
            const.FIWARE_SERVICE, const.DELIVERY_ROBOT_SERVICEPATH, const.PLACE_TYPE, 'name==place_A')
        assert mocked_waypoint.orion.query_entity.call_args_list[2] == call(
            const.FIWARE_SERVICE, const.DELIVERY_ROBOT_SERVICEPATH, const.ROUTE_PLAN_TYPE,
            'destination==dest_id;via==A_id;robot_id==robot_01')
        assert mocked_waypoint.orion.get_entities.call_count == 1
        assert mocked_waypoint.orion.get_entities.call_args == call(
            const.FIWARE_SERVICE, const.DELIVERY_ROBOT_SERVICEPATH, const.PLACE_TYPE)

    @pytest.mark.parametrize('updated', [
        [{'place': 'place_A'}], [{'place': 'place_A'}, {'place': 'place_A'}],
    ])
    @pytest.mark.parametrize('result_routes', [
        [
            {'from': 'B_id', 'via': ['C_id', 'D_id'], 'to': 'E_id', 'destination': 'dest_id', 'action': 'action_0'},
            {'from': 'E_id', 'via': ['F_id'], 'to': 'G_id', 'destination': 'dest_id', 'action': 'action_1'},
            {'from': 'G_id', 'via': [], 'to': 'H_id', 'destination': 'dest_id', 'action': 'action_2'},
        ],
        [
            {'from': 'Z_id', 'via': ['C_id', 'D_id'], 'to': 'E_id', 'destination': 'dest_id', 'action': 'action_0'},
            {'from': 'Z_id', 'via': ['F_id'], 'to': 'G_id', 'destination': 'dest_id', 'action': 'action_1'},
            {'from': 'Z_id', 'via': [], 'to': 'H_id', 'destination': 'dest_id', 'action': 'action_2'},
        ],
    ])
    def test_single_via_multi_routes(self, mocked_waypoint, updated, result_routes):
        robot_id = 'robot_01'
        shipment_list = {
            'destination': {
                'name': 'place_dest',
            },
            'updated': updated,
        }

        result_places = [{'id': 'dest_id'}, {'id': 'A_id'}]
        result_source = 'src'

        mocked_waypoint.orion.query_entity.side_effect = self.return_value_of_query_entity(result_places,
                                                                                           result_routes,
                                                                                           result_source,
                                                                                           0)
        mocked_waypoint.orion.get_entities.return_value = self.return_value_of_get_entities()
        routes, waypoints_list, order = mocked_waypoint.Waypoint().estimate_routes(shipment_list, robot_id)

        assert routes == result_routes
        assert waypoints_list == [
            {
                'to': 'E_id', 'destination': 'dest_id', 'action': 'action_0',
                'waypoints': [
                    {'point': 'pC', 'angle': None}, {'point': 'pD', 'angle': None}, {'point': 'pE', 'angle': 'aE'},
                ]
            },
            {
                'to': 'G_id', 'destination': 'dest_id', 'action': 'action_1',
                'waypoints': [
                    {'point': 'pF', 'angle': None}, {'point': 'pG', 'angle': 'aG'},
                ]
            },
            {
                'to': 'H_id', 'destination': 'dest_id', 'action': 'action_2',
                'waypoints': [
                    {'point': 'pH', 'angle': 'aH'},
                ]
            },
        ]
        assert order == {'source': 'src', 'via': ['A_id'], 'destination': 'dest_id'}

        assert mocked_waypoint.orion.query_entity.call_count == 3
        assert mocked_waypoint.orion.query_entity.call_args_list[0] == call(
            const.FIWARE_SERVICE, const.DELIVERY_ROBOT_SERVICEPATH, const.PLACE_TYPE, 'name==place_dest')
        assert mocked_waypoint.orion.query_entity.call_args_list[1] == call(
            const.FIWARE_SERVICE, const.DELIVERY_ROBOT_SERVICEPATH, const.PLACE_TYPE, 'name==place_A')
        assert mocked_waypoint.orion.query_entity.call_args_list[2] == call(
            const.FIWARE_SERVICE, const.DELIVERY_ROBOT_SERVICEPATH, const.ROUTE_PLAN_TYPE,
            'destination==dest_id;via==A_id;robot_id==robot_01')
        assert mocked_waypoint.orion.get_entities.call_count == 1
        assert mocked_waypoint.orion.get_entities.call_args == call(
            const.FIWARE_SERVICE, const.DELIVERY_ROBOT_SERVICEPATH, const.PLACE_TYPE)

    @pytest.mark.parametrize('updated', [
        [{'place': 'place_A'}, {'place': 'place_B'}], [{'place': 'place_A'}, {'place': 'place_B'}, {'place': 'place_A'}],
    ])
    @pytest.mark.parametrize('result_routes', [
        [{'from': 'B_id', 'via': ['C_id', 'D_id'], 'to': 'E_id', 'destination': 'dest_id', 'action': 'action_0'}],
        [{'from': 'Z_id', 'via': ['C_id', 'D_id'], 'to': 'E_id', 'destination': 'dest_id', 'action': 'action_0'}],
    ])
    def test_multi_via_single_route(self, mocked_waypoint, updated, result_routes):
        robot_id = 'robot_01'
        shipment_list = {
            'destination': {
                'name': 'place_dest',
            },
            'updated': updated,
        }

        result_places = [{'id': 'dest_id'}, {'id': 'A_id'}, {'id': 'B_id'}]
        result_source = 'src'

        mocked_waypoint.orion.query_entity.side_effect = self.return_value_of_query_entity(result_places,
                                                                                           result_routes,
                                                                                           result_source,
                                                                                           0)
        mocked_waypoint.orion.get_entities.return_value = self.return_value_of_get_entities()
        routes, waypoints_list, order = mocked_waypoint.Waypoint().estimate_routes(shipment_list, robot_id)

        assert routes == result_routes
        assert waypoints_list == [
            {
                'to': 'E_id', 'destination': 'dest_id', 'action': 'action_0',
                'waypoints': [
                    {'point': 'pC', 'angle': None}, {'point': 'pD', 'angle': None}, {'point': 'pE', 'angle': 'aE'},
                ]
            },
        ]
        assert order == {'source': 'src', 'via': ['A_id', 'B_id'], 'destination': 'dest_id'}

        assert mocked_waypoint.orion.query_entity.call_count == 4
        assert mocked_waypoint.orion.query_entity.call_args_list[0] == call(
            const.FIWARE_SERVICE, const.DELIVERY_ROBOT_SERVICEPATH, const.PLACE_TYPE, 'name==place_dest')
        assert mocked_waypoint.orion.query_entity.call_args_list[1] == call(
            const.FIWARE_SERVICE, const.DELIVERY_ROBOT_SERVICEPATH, const.PLACE_TYPE, 'name==place_A')
        assert mocked_waypoint.orion.query_entity.call_args_list[2] == call(
            const.FIWARE_SERVICE, const.DELIVERY_ROBOT_SERVICEPATH, const.PLACE_TYPE, 'name==place_B')
        assert mocked_waypoint.orion.query_entity.call_args_list[3] == call(
            const.FIWARE_SERVICE, const.DELIVERY_ROBOT_SERVICEPATH, const.ROUTE_PLAN_TYPE,
            'destination==dest_id;via==A_id|B_id;robot_id==robot_01')
        assert mocked_waypoint.orion.get_entities.call_count == 1
        assert mocked_waypoint.orion.get_entities.call_args == call(
            const.FIWARE_SERVICE, const.DELIVERY_ROBOT_SERVICEPATH, const.PLACE_TYPE)

    @pytest.mark.parametrize('updated', [
        [{'place': 'place_A'}, {'place': 'place_B'}], [{'place': 'place_A'}, {'place': 'place_B'}, {'place': 'place_A'}],
    ])
    @pytest.mark.parametrize('result_routes', [
        [
            {'from': 'B_id', 'via': ['C_id', 'D_id'], 'to': 'E_id', 'destination': 'dest_id', 'action': 'action_0'},
            {'from': 'E_id', 'via': ['F_id'], 'to': 'G_id', 'destination': 'dest_id', 'action': 'action_1'},
            {'from': 'G_id', 'via': [], 'to': 'H_id', 'destination': 'dest_id', 'action': 'action_2'},
        ],
        [
            {'from': 'Z_id', 'via': ['C_id', 'D_id'], 'to': 'E_id', 'destination': 'dest_id', 'action': 'action_0'},
            {'from': 'Z_id', 'via': ['F_id'], 'to': 'G_id', 'destination': 'dest_id', 'action': 'action_1'},
            {'from': 'Z_id', 'via': [], 'to': 'H_id', 'destination': 'dest_id', 'action': 'action_2'},
        ],
    ])
    def test_multi_via_multi_routes(self, mocked_waypoint, updated, result_routes):
        robot_id = 'robot_01'
        shipment_list = {
            'destination': {
                'name': 'place_dest',
            },
            'updated': updated,
        }

        result_places = [{'id': 'dest_id'}, {'id': 'A_id'}, {'id': 'B_id'}]
        result_source = 'src'

        mocked_waypoint.orion.query_entity.side_effect = self.return_value_of_query_entity(result_places,
                                                                                           result_routes,
                                                                                           result_source,
                                                                                           0)
        mocked_waypoint.orion.get_entities.return_value = self.return_value_of_get_entities()
        routes, waypoints_list, order = mocked_waypoint.Waypoint().estimate_routes(shipment_list, robot_id)

        assert routes == result_routes
        assert waypoints_list == [
            {
                'to': 'E_id', 'destination': 'dest_id', 'action': 'action_0',
                'waypoints': [
                    {'point': 'pC', 'angle': None}, {'point': 'pD', 'angle': None}, {'point': 'pE', 'angle': 'aE'},
                ]
            },
            {
                'to': 'G_id', 'destination': 'dest_id', 'action': 'action_1',
                'waypoints': [
                    {'point': 'pF', 'angle': None}, {'point': 'pG', 'angle': 'aG'},
                ]
            },
            {
                'to': 'H_id', 'destination': 'dest_id', 'action': 'action_2',
                'waypoints': [
                    {'point': 'pH', 'angle': 'aH'},
                ]
            },
        ]
        assert order == {'source': 'src', 'via': ['A_id', 'B_id'], 'destination': 'dest_id'}

        assert mocked_waypoint.orion.query_entity.call_count == 4
        assert mocked_waypoint.orion.query_entity.call_args_list[0] == call(
            const.FIWARE_SERVICE, const.DELIVERY_ROBOT_SERVICEPATH, const.PLACE_TYPE, 'name==place_dest')
        assert mocked_waypoint.orion.query_entity.call_args_list[1] == call(
            const.FIWARE_SERVICE, const.DELIVERY_ROBOT_SERVICEPATH, const.PLACE_TYPE, 'name==place_A')
        assert mocked_waypoint.orion.query_entity.call_args_list[2] == call(
            const.FIWARE_SERVICE, const.DELIVERY_ROBOT_SERVICEPATH, const.PLACE_TYPE, 'name==place_B')
        assert mocked_waypoint.orion.query_entity.call_args_list[3] == call(
            const.FIWARE_SERVICE, const.DELIVERY_ROBOT_SERVICEPATH, const.ROUTE_PLAN_TYPE,
            'destination==dest_id;via==A_id|B_id;robot_id==robot_01')
        assert mocked_waypoint.orion.get_entities.call_count == 1
        assert mocked_waypoint.orion.get_entities.call_args == call(
            const.FIWARE_SERVICE, const.DELIVERY_ROBOT_SERVICEPATH, const.PLACE_TYPE)

    @pytest.mark.parametrize('updated', [
        [],
    ])
    @pytest.mark.parametrize('result_routes', [
        [{'from': 'A_id', 'via': [], 'to': 'dest_id', 'destination': 'dest_id', 'action': ''}],
        [{'from': 'Z_id', 'via': [], 'to': 'dest_id', 'destination': 'dest_id', 'action': ''}],
    ])
    def test_no_via_single_route(self, mocked_waypoint, updated, result_routes):
        robot_id = 'robot_01'
        shipment_list = {
            'destination': {
                'name': 'place_dest',
            },
            'updated': updated,
        }

        result_places = [{'id': 'dest_id'}]
        result_source = 'src'

        mocked_waypoint.orion.query_entity.side_effect = self.return_value_of_query_entity(result_places,
                                                                                           result_routes,
                                                                                           result_source,
                                                                                           0)
        mocked_waypoint.orion.get_entities.return_value = self.return_value_of_get_entities()
        routes, waypoints_list, order = mocked_waypoint.Waypoint().estimate_routes(shipment_list, robot_id)

        assert routes == result_routes
        assert waypoints_list == [
            {
                'to': 'dest_id', 'destination': 'dest_id', 'action': '',
                'waypoints': [
                    {'point': 'pdest', 'angle': 'adest'},
                ]
            },
        ]
        assert order == {'source': 'src', 'via': [], 'destination': 'dest_id'}

        assert mocked_waypoint.orion.query_entity.call_count == 2
        assert mocked_waypoint.orion.query_entity.call_args_list[0] == call(
            const.FIWARE_SERVICE, const.DELIVERY_ROBOT_SERVICEPATH, const.PLACE_TYPE, 'name==place_dest')
        assert mocked_waypoint.orion.query_entity.call_args_list[1] == call(
            const.FIWARE_SERVICE, const.DELIVERY_ROBOT_SERVICEPATH, const.ROUTE_PLAN_TYPE,
            'destination==dest_id;via==;robot_id==robot_01')
        assert mocked_waypoint.orion.get_entities.call_count == 1
        assert mocked_waypoint.orion.get_entities.call_args == call(
            const.FIWARE_SERVICE, const.DELIVERY_ROBOT_SERVICEPATH, const.PLACE_TYPE)

    @pytest.mark.parametrize('updated', [
        [{'place': 'place_A'}], [{'place': 'place_A'}, {'place': 'place_A'}],
    ])
    @pytest.mark.parametrize('result_routes', [
        [],
    ])
    def test_single_via_no_route(self, mocked_waypoint, updated, result_routes):
        robot_id = 'robot_01'
        shipment_list = {
            'destination': {
                'name': 'place_dest',
            },
            'updated': updated,
        }

        result_places = [{'id': 'dest_id'}, {'id': 'A_id'}]
        result_source = 'src'

        mocked_waypoint.orion.query_entity.side_effect = self.return_value_of_query_entity(result_places,
                                                                                           result_routes,
                                                                                           result_source,
                                                                                           0)
        mocked_waypoint.orion.get_entities.return_value = self.return_value_of_get_entities()
        routes, waypoints_list, order = mocked_waypoint.Waypoint().estimate_routes(shipment_list, robot_id)

        assert routes == result_routes
        assert waypoints_list == []
        assert order == {'source': 'src', 'via': ['A_id'], 'destination': 'dest_id'}

        assert mocked_waypoint.orion.query_entity.call_count == 3
        assert mocked_waypoint.orion.query_entity.call_args_list[0] == call(
            const.FIWARE_SERVICE, const.DELIVERY_ROBOT_SERVICEPATH, const.PLACE_TYPE, 'name==place_dest')
        assert mocked_waypoint.orion.query_entity.call_args_list[1] == call(
            const.FIWARE_SERVICE, const.DELIVERY_ROBOT_SERVICEPATH, const.PLACE_TYPE, 'name==place_A')
        assert mocked_waypoint.orion.query_entity.call_args_list[2] == call(
            const.FIWARE_SERVICE, const.DELIVERY_ROBOT_SERVICEPATH, const.ROUTE_PLAN_TYPE,
            'destination==dest_id;via==A_id;robot_id==robot_01')
        assert mocked_waypoint.orion.get_entities.call_count == 1
        assert mocked_waypoint.orion.get_entities.call_args == call(
            const.FIWARE_SERVICE, const.DELIVERY_ROBOT_SERVICEPATH, const.PLACE_TYPE)

    @pytest.mark.parametrize('shipment_list, msg', [
        ({'destination': {'name': 0}, 'updated': [{'place': 'dummy'}]}, 'invalid shipment_list'),
        ({'destination': {'name': 1e-1}, 'updated': [{'place': 'dummy'}]}, 'invalid shipment_list'),
        ({'destination': {'name': True}, 'updated': [{'place': 'dummy'}]}, 'invalid shipment_list'),
        ({'destination': {'name': []}, 'updated': [{'place': 'dummy'}]}, 'invalid shipment_list'),
        ({'destination': {'name': ['a', 1]}, 'updated': [{'place': 'dummy'}]}, 'invalid shipment_list'),
        ({'destination': {'name': {}}, 'updated': [{'place': 'dummy'}]}, 'invalid shipment_list'),
        ({'destination': {'name': {'a': 1}}, 'updated': [{'place': 'dummy'}]}, 'invalid shipment_list'),
        ({'destination': {'name': tuple(['a', 1])}, 'updated': [{'place': 'dummy'}]}, 'invalid shipment_list'),
        ({'destination': {'name': set(['a', 1])}, 'updated': [{'place': 'dummy'}]}, 'invalid shipment_list'),
        ({'destination': {'name': dt.datetime.utcnow()}, 'updated': [{'place': 'dummy'}]}, 'invalid shipment_list'),
        ({'destination': {'name': None}, 'updated': [{'place': 'dummy'}]}, 'invalid shipment_list'),
        ({'destination': 0, 'updated': [{'place': 'dummy'}]}, "argument of type 'int' is not iterable"),
        ({'destination': 1e-1, 'updated': [{'place': 'dummy'}]}, "argument of type 'float' is not iterable"),
        ({'destination': True, 'updated': [{'place': 'dummy'}]}, "argument of type 'bool' is not iterable"),
        ({'destination': [], 'updated': [{'place': 'dummy'}]}, 'invalid shipment_list'),
        ({'destination': ['a', 1], 'updated': [{'place': 'dummy'}]}, 'invalid shipment_list'),
        ({'destination': {}, 'updated': [{'place': 'dummy'}]}, 'invalid shipment_list'),
        ({'destination': {'a': 1}, 'updated': [{'place': 'dummy'}]}, 'invalid shipment_list'),
        ({'destination': tuple(['a', 1]), 'updated': [{'place': 'dummy'}]}, 'invalid shipment_list'),
        ({'destination': set(['a', 1]), 'updated': [{'place': 'dummy'}]}, 'invalid shipment_list'),
        ({'destination': dt.datetime.utcnow(), 'updated': [{'place': 'dummy'}]},
         "argument of type 'datetime.datetime' is not iterable"),
        ({'destination': None, 'updated': [{'place': 'dummy'}]}, "argument of type 'NoneType' is not iterable"),
        ({'updated': [{'place': 'dummy'}]}, 'invalid shipment_list'),
        ({'destination': {'name': 'dummy'}, 'updated': [{'place': 0}]}, 'invalid shipment_list'),
        ({'destination': {'name': 'dummy'}, 'updated': [{'place': 1e-1}]}, 'invalid shipment_list'),
        ({'destination': {'name': 'dummy'}, 'updated': [{'place': True}]}, 'invalid shipment_list'),
        ({'destination': {'name': 'dummy'}, 'updated': [{'place': []}]}, 'invalid shipment_list'),
        ({'destination': {'name': 'dummy'}, 'updated': [{'place': ['a', 1]}]}, 'invalid shipment_list'),
        ({'destination': {'name': 'dummy'}, 'updated': [{'place': {}}]}, 'invalid shipment_list'),
        ({'destination': {'name': 'dummy'}, 'updated': [{'place': {'a': 1}}]}, 'invalid shipment_list'),
        ({'destination': {'name': 'dummy'}, 'updated': [{'place': list(['a', 1])}]}, 'invalid shipment_list'),
        ({'destination': {'name': 'dummy'}, 'updated': [{'place': set(['a', 1])}]}, 'invalid shipment_list'),
        ({'destination': {'name': 'dummy'}, 'updated': [{'place': dt.datetime.utcnow()}]}, 'invalid shipment_list'),
        ({'destination': {'name': 'dummy'}, 'updated': [{'place': None}]}, 'invalid shipment_list'),
        ({'destination': {'name': 'dummy'}, 'updated': 0}, 'invalid shipment_list'),
        ({'destination': {'name': 'dummy'}, 'updated': 1e-1}, 'invalid shipment_list'),
        ({'destination': {'name': 'dummy'}, 'updated': True}, 'invalid shipment_list'),
        ({'destination': {'name': 'dummy'}, 'updated': ['a', 1]}, 'invalid shipment_list'),
        ({'destination': {'name': 'dummy'}, 'updated': {}}, 'invalid shipment_list'),
        ({'destination': {'name': 'dummy'}, 'updated': {'a': 1}}, 'invalid shipment_list'),
        ({'destination': {'name': 'dummy'}, 'updated': tuple(['a', 1])}, 'invalid shipment_list'),
        ({'destination': {'name': 'dummy'}, 'updated': set(['a', 1])}, 'invalid shipment_list'),
        ({'destination': {'name': 'dummy'}, 'updated': dt.datetime.utcnow()}, 'invalid shipment_list'),
        ({'destination': {'name': 'dummy'}, 'updated': None}, 'invalid shipment_list'),
        ({'destination': {'name': 'dummy'}}, 'invalid shipment_list'),
        (0, "argument of type 'int' is not iterable"),
        (1e-1, "argument of type 'float' is not iterable"),
        (True, "argument of type 'bool' is not iterable"),
        ([], 'invalid shipment_list'),
        (['a', 1], 'invalid shipment_list'),
        ({}, 'invalid shipment_list'),
        ({'a': 1}, 'invalid shipment_list'),
        (tuple(['a', 1]), 'invalid shipment_list'),
        (set(['a', 1]), 'invalid shipment_list'),
        (dt.datetime.utcnow(), "argument of type 'datetime.datetime' is not iterable"),
        (None, "argument of type 'NoneType' is not iterable"),
    ])
    def test_invalid_shipment(self, mocked_waypoint, shipment_list, msg):
        robot_id = 'robot_01'

        result_places = [{'id': 'dest_id'}, {'id': 'A_id'}]
        result_routes = []
        result_source = 'src'

        mocked_waypoint.orion.query_entity.side_effect = self.return_value_of_query_entity(result_places,
                                                                                           result_routes,
                                                                                           result_source,
                                                                                           0)
        mocked_waypoint.orion.get_entities.return_value = self.return_value_of_get_entities()
        with pytest.raises(TypeError) as e:
            mocked_waypoint.Waypoint().estimate_routes(shipment_list, robot_id)

        assert str(e.value) == msg

        assert mocked_waypoint.orion.query_entity.call_count == 0
        assert mocked_waypoint.orion.get_entities.call_count == 0

    @pytest.mark.parametrize('robot_id, msg', [
        (0, 'invalid robot_id'),
        (1e-1, 'invalid robot_id'),
        (True, 'invalid robot_id'),
        ([], 'invalid robot_id'),
        (['a', 1], 'invalid robot_id'),
        ({}, 'invalid robot_id'),
        ({'a': 1}, 'invalid robot_id'),
        (tuple(['a', 1]), 'invalid robot_id'),
        (set(['a', 1]), 'invalid robot_id'),
        (dt.datetime.utcnow(), 'invalid robot_id'),
        (None, 'invalid robot_id'),
    ])
    def test_invalid_robotid(self, mocked_waypoint, robot_id, msg):
        shipment_list = {
            'destination': {
                'name': 'place_dest',
            },
            'updated': [{'place': 'place_A'}],
        }

        result_places = [{'id': 'dest_id'}, {'id': 'A_id'}]
        result_routes = []
        result_source = 'src'

        mocked_waypoint.orion.query_entity.side_effect = self.return_value_of_query_entity(result_places,
                                                                                           result_routes,
                                                                                           result_source,
                                                                                           0)
        mocked_waypoint.orion.get_entities.return_value = self.return_value_of_get_entities()
        with pytest.raises(TypeError) as e:
            mocked_waypoint.Waypoint().estimate_routes(shipment_list, robot_id)

        assert str(e.value) == msg

        assert mocked_waypoint.orion.query_entity.call_count == 0
        assert mocked_waypoint.orion.get_entities.call_count == 0
