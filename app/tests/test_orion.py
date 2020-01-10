import os
import json
import datetime as dt
import importlib
from unittest.mock import call

import requests
import dateutil.parser
from werkzeug.exceptions import InternalServerError, NotFound, BadRequest

import pytest
import freezegun
import lazy_import
orion = lazy_import.lazy_module('src.orion')
const = lazy_import.lazy_module('src.const')
caller = lazy_import.lazy_module('src.caller')
token = lazy_import.lazy_module('src.token')


@pytest.fixture
def mocked_requests(mocker):
    orion.requests = mocker.MagicMock()
    yield orion.requests


@pytest.fixture
def mocked_response(mocker):
    return mocker.MagicMock(spec=requests.Response)


@pytest.fixture
def reload_module():
    importlib.reload(const)
    importlib.reload(orion)
    yield


@pytest.mark.usefixtures('setup_environments', 'reload_module')
class TestSendCommand:

    @pytest.mark.parametrize('payload', [
        {'msg': 'dummy'},
        {'test': {'nested': [1, 2.0, '3']}},
        {},
        [1, 1.2e-2, 'a', True, {'a': 'b'}, None],
        [],
        'dummy',
        1,
        0.5,
        True,
        None,
        tuple([1, 2]),
    ])
    @pytest.mark.parametrize('env_token, expected_token', [
        ('orion_token', 'bearer orion_token'),
        (None, None),
    ])
    def test_success(self, mocker, mocked_response, payload, env_token, expected_token):
        if env_token is not None:
            os.environ['ORION_TOKEN'] = env_token
            importlib.reload(const)
            importlib.reload(orion)
        mocked_requests = mocker.MagicMock()
        orion.requests = mocked_requests

        fiware_service = 'dummy_service'
        fiware_servicepath = 'dummy_servicepath'
        entity_type = 'dummy_type'
        entity_id = 'dummy_id'

        mocked_response.status_code = 200
        mocked_response.text = 'test'

        mocked_requests.patch.return_value = mocked_response

        result = orion.send_command(fiware_service, fiware_servicepath, entity_type, entity_id, payload)

        assert result.status_code == 200
        assert result.text == 'test'
        assert mocked_requests.get.call_count == 0
        assert mocked_requests.post.call_count == 0
        assert mocked_requests.put.call_count == 0
        assert mocked_requests.patch.call_count == 1
        assert mocked_requests.delete.call_count == 0

        endpoint = f'{const.ORION_ENDPOINT}/v2/entities/{entity_id}/attrs?type={entity_type}'
        headers = {
            'Content-Type': 'application/json',
            'FIWARE-SERVICE': fiware_service,
            'FIWARE-SERVICEPATH': fiware_servicepath,
        }
        if expected_token is not None:
            headers['Authorization'] = expected_token
        assert mocked_requests.patch.call_args == call(endpoint, headers=headers, json=payload)

    @pytest.mark.parametrize('response_code, expected_exception, expected_value', [
        (300, InternalServerError, '500 Internal Server Error'),
        (400, InternalServerError, '500 Internal Server Error'),
        (404, NotFound, '404 Not Found'),
    ])
    @pytest.mark.parametrize('response_text, expected_text', [
        ('root_cause', 'root_cause'),
        (None, ''),
        ('', ''),
    ])
    def test_response_error(self, mocked_requests,
                            response_code, expected_exception, expected_value, response_text, expected_text):
        fiware_service = 'dummy_service'
        fiware_servicepath = 'dummy_servicepath'
        entity_type = 'dummy_type'
        entity_id = 'dummy_id'
        payload = {
            'msg': 'dummy'
        }

        class MockResponse:
            pass

        mocked_response = MockResponse()
        mocked_response.status_code = response_code
        if response_text is not None:
            mocked_response.text = response_text

        mocked_requests.patch.return_value = mocked_response

        with pytest.raises(expected_exception) as e:
            orion.send_command(fiware_service, fiware_servicepath, entity_type, entity_id, payload)

        result = {
            'message': 'can not send command to orion',
            'root_cause': expected_text,
        }
        assert str(e.value) == f'{expected_value}: {result}'

        assert mocked_requests.get.call_count == 0
        assert mocked_requests.post.call_count == 0
        assert mocked_requests.put.call_count == 0
        assert mocked_requests.patch.call_count == 1
        assert mocked_requests.delete.call_count == 0

        endpoint = f'{const.ORION_ENDPOINT}/v2/entities/{entity_id}/attrs?type={entity_type}'
        headers = {
            'Content-Type': 'application/json',
            'FIWARE-SERVICE': fiware_service,
            'FIWARE-SERVICEPATH': fiware_servicepath,
        }
        assert mocked_requests.patch.call_args == call(endpoint, headers=headers, json=payload)

    @pytest.mark.parametrize(
        'fiware_service, fiware_servicepath, entity_type, entity_id', [
            ('dummy', 0, 1e-1, True),
            (0, 1e-1, True, None),
            (1e-1, True, None, []),
            (True, None, [], {}),
            (None, [], {}, tuple(['a', 1])),
            ([], {}, tuple(['a', 1]), set([1, 2, 1])),
            ({}, tuple(['a', 1]), set([1, 2, 1]), dt.datetime.utcnow()),
            (tuple(['a', 1]), set([1, 2, 1]), dt.datetime.utcnow(), 'dummy'),
            (set([1, 2, 1]), dt.datetime.utcnow(), 'dummy', 0),
            (dt.datetime.utcnow(), 'dummy', 0, 1e-1),
        ]
    )
    def test_invalid_args(self, mocked_requests, mocked_response,
                          fiware_service, fiware_servicepath, entity_type, entity_id):
        payload = {
            'msg': 'dummy'
        }
        with pytest.raises(TypeError) as e:
            orion.send_command(fiware_service, fiware_servicepath, entity_type, entity_id, payload)

        assert mocked_requests.get.call_count == 0
        assert mocked_requests.post.call_count == 0
        assert mocked_requests.put.call_count == 0
        assert mocked_requests.patch.call_count == 0
        assert mocked_requests.delete.call_count == 0
        assert str(e.value) == 'fiware_service, fiware_servicepath, entity_type and entity_id must be "str"'

    @pytest.mark.parametrize('payload', [
        dt.datetime.utcnow(),
        set([1, 2, 1]),
    ])
    def test_invalid_payload(self, mocked_requests, mocked_response, payload):
        fiware_service = 'dummy_service'
        fiware_servicepath = 'dummy_servicepath'
        entity_type = 'dummy_type'
        entity_id = 'dummy_id'

        with pytest.raises(TypeError) as e:
            orion.send_command(fiware_service, fiware_servicepath, entity_type, entity_id, payload)

        assert mocked_requests.get.call_count == 0
        assert mocked_requests.post.call_count == 0
        assert mocked_requests.put.call_count == 0
        assert mocked_requests.patch.call_count == 0
        assert mocked_requests.delete.call_count == 0
        assert str(e.value) == 'payload must be json serializable'


@pytest.mark.usefixtures('setup_environments', 'reload_module')
class TestQueryEntity:

    @pytest.mark.parametrize('env_token, expected_token', [
        ('orion_token', 'bearer orion_token'),
        (None, None),
    ])
    def test_success(self, mocker, mocked_response, env_token, expected_token):
        if env_token is not None:
            os.environ['ORION_TOKEN'] = env_token
            importlib.reload(const)
            importlib.reload(orion)
        mocked_requests = mocker.MagicMock()
        orion.requests = mocked_requests

        fiware_service = 'dummy_service'
        fiware_servicepath = 'dummy_servicepath'
        entity_type = 'dummy_type'
        query = 'foo==dummy_query'

        mocked_response.status_code = 200
        mocked_response.json.return_value = [{'result': 'test'}]

        mocked_requests.get.return_value = mocked_response

        result = orion.query_entity(fiware_service, fiware_servicepath, entity_type, query)

        assert result == {'result': 'test'}
        assert mocked_requests.get.call_count == 1
        assert mocked_requests.post.call_count == 0
        assert mocked_requests.put.call_count == 0
        assert mocked_requests.patch.call_count == 0
        assert mocked_requests.delete.call_count == 0

        endpoint = f'{const.ORION_ENDPOINT}/v2/entities/'
        headers = {
            'FIWARE-SERVICE': fiware_service,
            'FIWARE-SERVICEPATH': fiware_servicepath,
        }
        if expected_token is not None:
            headers['Authorization'] = expected_token

        params = {
            'type': entity_type,
            'limit': const.ORION_LIST_NUM_LIMIT,
            'q': query,
        }
        assert mocked_requests.get.call_args == call(endpoint, headers=headers, params=params)

    @pytest.mark.parametrize('response_code, expected_exception, expected_value', [
        (300, InternalServerError, '500 Internal Server Error'),
        (400, InternalServerError, '500 Internal Server Error'),
        (404, NotFound, '404 Not Found'),
    ])
    @pytest.mark.parametrize('response_text, expected_text', [
        ('root_cause', 'root_cause'),
        (None, ''),
        ('', ''),
    ])
    def test_response_error(self, mocked_requests,
                            response_code, expected_exception, expected_value, response_text, expected_text):
        fiware_service = 'dummy_service'
        fiware_servicepath = 'dummy_servicepath'
        entity_type = 'dummy_type'
        query = 'foo==dummy_query'

        class MockResponse:
            pass

        mocked_response = MockResponse()
        mocked_response.status_code = response_code
        if response_text is not None:
            mocked_response.text = response_text

        mocked_requests.get.return_value = mocked_response

        with pytest.raises(expected_exception) as e:
            orion.query_entity(fiware_service, fiware_servicepath, entity_type, query)

        result = {
            'message': 'can not get entities from orion',
            'root_cause': expected_text,
        }
        assert str(e.value) == f'{expected_value}: {result}'

        assert mocked_requests.get.call_count == 1
        assert mocked_requests.post.call_count == 0
        assert mocked_requests.put.call_count == 0
        assert mocked_requests.patch.call_count == 0
        assert mocked_requests.delete.call_count == 0

        endpoint = f'{const.ORION_ENDPOINT}/v2/entities/'
        headers = {
            'FIWARE-SERVICE': fiware_service,
            'FIWARE-SERVICEPATH': fiware_servicepath,
        }
        params = {
            'type': entity_type,
            'limit': const.ORION_LIST_NUM_LIMIT,
            'q': query,
        }
        assert mocked_requests.get.call_args == call(endpoint, headers=headers, params=params)

    def test_json_decodeerror(self, mocked_requests, mocked_response):
        fiware_service = 'dummy_service'
        fiware_servicepath = 'dummy_servicepath'
        entity_type = 'dummy_type'
        query = 'foo==dummy_query'

        mocked_response.status_code = 200
        mocked_response.json.side_effect = json.decoder.JSONDecodeError('test error', doc='doc', pos=1)

        mocked_requests.get.return_value = mocked_response

        with pytest.raises(BadRequest) as e:
            orion.query_entity(fiware_service, fiware_servicepath, entity_type, query)

        result = {
            'message': 'can not parse result',
            'root_cause': 'test error: line 1 column 2 (char 1)',
        }
        assert str(e.value) == f'400 Bad Request: {result}'

        assert mocked_requests.get.call_count == 1
        assert mocked_requests.post.call_count == 0
        assert mocked_requests.put.call_count == 0
        assert mocked_requests.patch.call_count == 0
        assert mocked_requests.delete.call_count == 0

        endpoint = f'{const.ORION_ENDPOINT}/v2/entities/'
        headers = {
            'FIWARE-SERVICE': fiware_service,
            'FIWARE-SERVICEPATH': fiware_servicepath,
        }
        params = {
            'type': entity_type,
            'limit': const.ORION_LIST_NUM_LIMIT,
            'q': query,
        }
        assert mocked_requests.get.call_args == call(endpoint, headers=headers, params=params)

    @pytest.mark.parametrize('response_json', [
        'dummy', 0, 1e-1, True, [], ['a', 1], {}, {'a': 1}, tuple(['a', 1]), set([1, 2]), dt.datetime.utcnow(), None
    ])
    def test_invalid_json(self, mocked_requests, mocked_response, response_json):
        fiware_service = 'dummy_service'
        fiware_servicepath = 'dummy_servicepath'
        entity_type = 'dummy_type'
        query = 'foo==dummy_query'

        expected_msg = {'message': f'can not retrieve an entity, entity_type={entity_type}, query={query}'}

        mocked_response.status_code = 200
        mocked_response.json.return_value = response_json

        mocked_requests.get.return_value = mocked_response

        with pytest.raises(BadRequest) as e:
            orion.query_entity(fiware_service, fiware_servicepath, entity_type, query)

        assert str(e.value) == f'400 Bad Request: {expected_msg}'

        assert mocked_requests.get.call_count == 1
        assert mocked_requests.post.call_count == 0
        assert mocked_requests.put.call_count == 0
        assert mocked_requests.patch.call_count == 0
        assert mocked_requests.delete.call_count == 0

        endpoint = f'{const.ORION_ENDPOINT}/v2/entities/'
        headers = {
            'FIWARE-SERVICE': fiware_service,
            'FIWARE-SERVICEPATH': fiware_servicepath,
        }
        params = {
            'type': entity_type,
            'limit': const.ORION_LIST_NUM_LIMIT,
            'q': query,
        }
        assert mocked_requests.get.call_args == call(endpoint, headers=headers, params=params)

    @pytest.mark.parametrize(
        'fiware_service, fiware_servicepath, entity_type, query', [
            ('dummy', 0, 1e-1, True),
            (0, 1e-1, True, None),
            (1e-1, True, None, []),
            (True, None, [], {}),
            (None, [], {}, tuple(['a', 1])),
            ([], {}, tuple(['a', 1]), set([1, 2, 1])),
            ({}, tuple(['a', 1]), set([1, 2, 1]), dt.datetime.utcnow()),
            (tuple(['a', 1]), set([1, 2, 1]), dt.datetime.utcnow(), 'dummy'),
            (set([1, 2, 1]), dt.datetime.utcnow(), 'dummy', 0),
            (dt.datetime.utcnow(), 'dummy', 0, 1e-1),
        ]
    )
    def test_invalid_args(self, mocked_requests, mocked_response,
                          fiware_service, fiware_servicepath, entity_type, query):

        with pytest.raises(TypeError) as e:
            orion.query_entity(fiware_service, fiware_servicepath, entity_type, query)

        assert mocked_requests.get.call_count == 0
        assert mocked_requests.post.call_count == 0
        assert mocked_requests.put.call_count == 0
        assert mocked_requests.patch.call_count == 0
        assert mocked_requests.delete.call_count == 0
        assert str(e.value) == 'fiware_service, fiware_servicepath, entity_type and query must be "str"'


@pytest.mark.usefixtures('setup_environments', 'reload_module')
class TestGetEntities:

    @pytest.mark.parametrize('env_token, expected_token', [
        ('orion_token', 'bearer orion_token'),
        (None, None),
    ])
    def test_success(self, mocker, mocked_response, env_token, expected_token):
        if env_token is not None:
            os.environ['ORION_TOKEN'] = env_token
            importlib.reload(const)
            importlib.reload(orion)
        mocked_requests = mocker.MagicMock()
        orion.requests = mocked_requests

        fiware_service = 'dummy_service'
        fiware_servicepath = 'dummy_servicepath'
        entity_type = 'dummy_type'

        response_json = [{'result': 'test1'}, {'result': 'test2'}]

        mocked_response.status_code = 200
        mocked_response.json.return_value = response_json

        mocked_requests.get.return_value = mocked_response

        result = orion.get_entities(fiware_service, fiware_servicepath, entity_type)

        assert result == response_json
        assert mocked_requests.get.call_count == 1
        assert mocked_requests.post.call_count == 0
        assert mocked_requests.put.call_count == 0
        assert mocked_requests.patch.call_count == 0
        assert mocked_requests.delete.call_count == 0

        endpoint = f'{const.ORION_ENDPOINT}/v2/entities/'
        headers = {
            'FIWARE-SERVICE': fiware_service,
            'FIWARE-SERVICEPATH': fiware_servicepath,
        }
        if expected_token is not None:
            headers['Authorization'] = expected_token

        params = {
            'type': entity_type,
            'limit': const.ORION_LIST_NUM_LIMIT,
        }
        assert mocked_requests.get.call_args == call(endpoint, headers=headers, params=params)

    @pytest.mark.parametrize('response_code, expected_exception, expected_value', [
        (300, InternalServerError, '500 Internal Server Error'),
        (400, InternalServerError, '500 Internal Server Error'),
        (404, NotFound, '404 Not Found'),
    ])
    @pytest.mark.parametrize('response_text, expected_text', [
        ('root_cause', 'root_cause'),
        (None, ''),
        ('', ''),
    ])
    def test_response_error(self, mocked_requests,
                            response_code, expected_exception, expected_value, response_text, expected_text):
        fiware_service = 'dummy_service'
        fiware_servicepath = 'dummy_servicepath'
        entity_type = 'dummy_type'

        class MockResponse:
            pass

        mocked_response = MockResponse()
        mocked_response.status_code = response_code
        if response_text is not None:
            mocked_response.text = response_text

        mocked_requests.get.return_value = mocked_response

        with pytest.raises(expected_exception) as e:
            orion.get_entities(fiware_service, fiware_servicepath, entity_type)

        result = {
            'message': 'can not get entities from orion',
            'root_cause': expected_text,
        }
        assert str(e.value) == f'{expected_value}: {result}'

        assert mocked_requests.get.call_count == 1
        assert mocked_requests.post.call_count == 0
        assert mocked_requests.put.call_count == 0
        assert mocked_requests.patch.call_count == 0
        assert mocked_requests.delete.call_count == 0

        endpoint = f'{const.ORION_ENDPOINT}/v2/entities/'
        headers = {
            'FIWARE-SERVICE': fiware_service,
            'FIWARE-SERVICEPATH': fiware_servicepath,
        }
        params = {
            'type': entity_type,
            'limit': const.ORION_LIST_NUM_LIMIT,
        }
        assert mocked_requests.get.call_args == call(endpoint, headers=headers, params=params)

    def test_json_decodeerror(self, mocked_requests, mocked_response):
        fiware_service = 'dummy_service'
        fiware_servicepath = 'dummy_servicepath'
        entity_type = 'dummy_type'

        mocked_response.status_code = 200
        mocked_response.json.side_effect = json.decoder.JSONDecodeError('test error', doc='doc', pos=1)

        mocked_requests.get.return_value = mocked_response

        with pytest.raises(BadRequest) as e:
            orion.get_entities(fiware_service, fiware_servicepath, entity_type)

        result = {
            'message': 'can not parse result',
            'root_cause': 'test error: line 1 column 2 (char 1)',
        }
        assert str(e.value) == f'400 Bad Request: {result}'

        assert mocked_requests.get.call_count == 1
        assert mocked_requests.post.call_count == 0
        assert mocked_requests.put.call_count == 0
        assert mocked_requests.patch.call_count == 0
        assert mocked_requests.delete.call_count == 0

        endpoint = f'{const.ORION_ENDPOINT}/v2/entities/'
        headers = {
            'FIWARE-SERVICE': fiware_service,
            'FIWARE-SERVICEPATH': fiware_servicepath,
        }
        params = {
            'type': entity_type,
            'limit': const.ORION_LIST_NUM_LIMIT,
        }
        assert mocked_requests.get.call_args == call(endpoint, headers=headers, params=params)

    @pytest.mark.parametrize('fiware_service, fiware_servicepath, entity_type', [
        ('dummy', 0, 1e-1),
        (0, 1e-1, True),
        (1e-1, True, None),
        (True, None, []),
        (None, [], {}),
        ([], {}, tuple(['a', 1])),
        ({}, tuple(['a', 1]), set([1, 2, 1])),
        (tuple(['a', 1]), set([1, 2, 1]), dt.datetime.utcnow()),
        (set([1, 2, 1]), dt.datetime.utcnow(), 'dummy'),
        (dt.datetime.utcnow(), 'dummy', 0),
    ])
    def test_invalid_args(self, mocked_requests, mocked_response,
                          fiware_service, fiware_servicepath, entity_type):

        with pytest.raises(TypeError) as e:
            orion.get_entities(fiware_service, fiware_servicepath, entity_type)

        assert mocked_requests.get.call_count == 0
        assert mocked_requests.post.call_count == 0
        assert mocked_requests.put.call_count == 0
        assert mocked_requests.patch.call_count == 0
        assert mocked_requests.delete.call_count == 0
        assert str(e.value) == 'fiware_service, fiware_servicepath and entity_type must be "str"'


@pytest.mark.usefixtures('setup_environments', 'reload_module')
class TestGetEntity:

    @pytest.mark.parametrize('env_token, expected_token', [
        ('orion_token', 'bearer orion_token'),
        (None, None),
    ])
    def test_success(self, mocker, mocked_response, env_token, expected_token):
        if env_token is not None:
            os.environ['ORION_TOKEN'] = env_token
            importlib.reload(const)
            importlib.reload(orion)
        mocked_requests = mocker.MagicMock()
        orion.requests = mocked_requests

        fiware_service = 'dummy_service'
        fiware_servicepath = 'dummy_servicepath'
        entity_type = 'dummy_type'
        entity_id = 'dummy_id'

        response_json = {'result': 'test1'}

        mocked_response.status_code = 200
        mocked_response.json.return_value = response_json

        mocked_requests.get.return_value = mocked_response

        result = orion.get_entity(fiware_service, fiware_servicepath, entity_type, entity_id)

        assert result == response_json
        assert mocked_requests.get.call_count == 1
        assert mocked_requests.post.call_count == 0
        assert mocked_requests.put.call_count == 0
        assert mocked_requests.patch.call_count == 0
        assert mocked_requests.delete.call_count == 0

        endpoint = f'{const.ORION_ENDPOINT}/v2/entities/{entity_id}'
        headers = {
            'FIWARE-SERVICE': fiware_service,
            'FIWARE-SERVICEPATH': fiware_servicepath,
        }
        if expected_token is not None:
            headers['Authorization'] = expected_token

        params = {
            'type': entity_type,
        }
        assert mocked_requests.get.call_args == call(endpoint, headers=headers, params=params)

    @pytest.mark.parametrize('response_code, expected_exception, expected_value', [
        (300, InternalServerError, '500 Internal Server Error'),
        (400, InternalServerError, '500 Internal Server Error'),
        (404, NotFound, '404 Not Found'),
    ])
    @pytest.mark.parametrize('response_text, expected_text', [
        ('root_cause', 'root_cause'),
        (None, ''),
        ('', ''),
    ])
    def test_response_error(self, mocked_requests,
                            response_code, expected_exception, expected_value, response_text, expected_text):
        fiware_service = 'dummy_service'
        fiware_servicepath = 'dummy_servicepath'
        entity_type = 'dummy_type'
        entity_id = 'dummy_id'

        class MockResponse:
            pass

        mocked_response = MockResponse()
        mocked_response.status_code = response_code
        if response_text is not None:
            mocked_response.text = response_text

        mocked_requests.get.return_value = mocked_response

        with pytest.raises(expected_exception) as e:
            orion.get_entity(fiware_service, fiware_servicepath, entity_type, entity_id)

        result = {
            'message': 'can not get an entity from orion',
            'root_cause': expected_text,
        }
        assert str(e.value) == f'{expected_value}: {result}'

        assert mocked_requests.get.call_count == 1
        assert mocked_requests.post.call_count == 0
        assert mocked_requests.put.call_count == 0
        assert mocked_requests.patch.call_count == 0
        assert mocked_requests.delete.call_count == 0

        endpoint = f'{const.ORION_ENDPOINT}/v2/entities/{entity_id}'
        headers = {
            'FIWARE-SERVICE': fiware_service,
            'FIWARE-SERVICEPATH': fiware_servicepath,
        }
        params = {
            'type': entity_type,
        }
        assert mocked_requests.get.call_args == call(endpoint, headers=headers, params=params)

    def test_json_decodeerror(self, mocked_requests, mocked_response):
        fiware_service = 'dummy_service'
        fiware_servicepath = 'dummy_servicepath'
        entity_type = 'dummy_type'
        entity_id = 'dummy_id'

        mocked_response.status_code = 200
        mocked_response.json.side_effect = json.decoder.JSONDecodeError('test error', doc='doc', pos=1)

        mocked_requests.get.return_value = mocked_response

        with pytest.raises(BadRequest) as e:
            orion.get_entity(fiware_service, fiware_servicepath, entity_type, entity_id)

        result = {
            'message': 'can not parse result',
            'root_cause': 'test error: line 1 column 2 (char 1)',
        }
        assert str(e.value) == f'400 Bad Request: {result}'

        assert mocked_requests.get.call_count == 1
        assert mocked_requests.post.call_count == 0
        assert mocked_requests.put.call_count == 0
        assert mocked_requests.patch.call_count == 0
        assert mocked_requests.delete.call_count == 0

        endpoint = f'{const.ORION_ENDPOINT}/v2/entities/{entity_id}'
        headers = {
            'FIWARE-SERVICE': fiware_service,
            'FIWARE-SERVICEPATH': fiware_servicepath,
        }
        params = {
            'type': entity_type,
        }
        assert mocked_requests.get.call_args == call(endpoint, headers=headers, params=params)

    @pytest.mark.parametrize('fiware_service, fiware_servicepath, entity_type, entity_id', [
        ('dummy', 0, 1e-1, True),
        (0, 1e-1, True, None),
        (1e-1, True, None, []),
        (True, None, [], {}),
        (None, [], {}, tuple(['a', 1])),
        ([], {}, tuple(['a', 1]), set([1, 2, 1])),
        ({}, tuple(['a', 1]), set([1, 2, 1]), dt.datetime.utcnow()),
        (tuple(['a', 1]), set([1, 2, 1]), dt.datetime.utcnow(), 'dummy'),
        (set([1, 2, 1]), dt.datetime.utcnow(), 'dummy', 0),
        (dt.datetime.utcnow(), 'dummy', 0, 1e-1),
    ])
    def test_invalid_args(self, mocked_requests, mocked_response,
                          fiware_service, fiware_servicepath, entity_type, entity_id):

        with pytest.raises(TypeError) as e:
            orion.get_entity(fiware_service, fiware_servicepath, entity_type, entity_id)

        assert mocked_requests.get.call_count == 0
        assert mocked_requests.post.call_count == 0
        assert mocked_requests.put.call_count == 0
        assert mocked_requests.patch.call_count == 0
        assert mocked_requests.delete.call_count == 0
        assert str(e.value) == 'fiware_service, fiware_servicepath, entity_type and entity_id must be "str"'


@pytest.mark.usefixtures('setup_environments', 'reload_module')
class TestMakeDeliveryRobotCommand:

    @pytest.mark.parametrize('timezone, expected_datetime', [
        (None, '2020-01-01T18:04:05.000+00:00'),
        ('UTC', '2020-01-01T18:04:05.000+00:00'),
        ('Asia/Tokyo', '2020-01-02T03:04:05.000+09:00'),
    ])
    def test_timezone(self, timezone, expected_datetime):
        time = '2020-01-02T03:04:05+09:00'
        if timezone is not None:
            os.environ['TIMEZONE'] = timezone
            importlib.reload(const)
            importlib.reload(orion)

        cmd = 'test'
        cmd_waypoints = [{'from': 'place_1', 'to': 'place_2'}, {'from': 'place_2', 'to': 'place_3'}]
        navigating_waypoints = [{'x': 1.0, 'y': -1.5}, {'x': 2.0, 'y': -1.5}]

        with freezegun.freeze_time(time):
            payload = orion.make_delivery_robot_command(cmd, cmd_waypoints, navigating_waypoints)

        assert payload == {
            'send_cmd': {
                'value': {
                    'time': expected_datetime,
                    'cmd': cmd,
                    'waypoints': cmd_waypoints
                }
            },
            'navigating_waypoints': {
                'type': 'object',
                'value': navigating_waypoints,
                'metadata': {
                    'TimeInstant': {
                        'type': 'datetime',
                        'value': expected_datetime,
                    }
                }
            }
        }

    @pytest.mark.parametrize('c, cw, nw, rwl, cr, o, ca', [
        ('dummy', 0, 1e-1, True, [], ['a', 1], {}),
        (0, 1e-1, True, [], ['a', 1], {}, {'a': 1}),
        (1e-1, True, [], ['a', 1], {}, {'a': 1}, tuple(['a', 1])),
        (True, [], ['a', 1], {}, {'a': 1}, tuple(['a', 1]), set([1, 2])),
        ([], ['a', 1], {}, {'a': 1}, tuple(['a', 1]), set([1, 2]), dt.datetime.utcnow()),
        (['a', 1], {}, {'a': 1}, tuple(['a', 1]), set([1, 2]), dt.datetime.utcnow(), caller.Caller.WAREHOUSE),
        ({}, {'a': 1}, tuple(['a', 1]), set([1, 2]), dt.datetime.utcnow(), caller.Caller.WAREHOUSE, caller.Caller.ORDERING),
        ({'a': 1}, tuple(['a', 1]), set([1, 2]), dt.datetime.utcnow(), caller.Caller.WAREHOUSE, caller.Caller.ORDERING, None),
        (tuple(['a', 1]), set([1, 2]), dt.datetime.utcnow(), caller.Caller.WAREHOUSE, caller.Caller.ORDERING, None, 'dummy'),
        (set([1, 2]), dt.datetime.utcnow(), caller.Caller.WAREHOUSE, caller.Caller.ORDERING, None, 'dummy', 0),
        (dt.datetime.utcnow(), caller.Caller.WAREHOUSE, caller.Caller.ORDERING, None, 'dummy', 0, 1e-1),
        (caller.Caller.WAREHOUSE, caller.Caller.ORDERING, None, 'dummy', 0, 1e-1, True),
        (caller.Caller.ORDERING, None, 'dummy', 0, 1e-1, True, []),
        (None, 'dummy', 0, 1e-1, True, [], ['a', 1]),
    ])
    def test_args(self, c, cw, nw, rwl, cr, o, ca):
        time = '2020-01-02T03:04:05.000+00:00'

        with freezegun.freeze_time(time):
            payload = orion.make_delivery_robot_command(c, cw, nw, rwl, cr, o, ca)

        result = {
            'send_cmd': {
                'value': {
                    'time': time,
                    'cmd': c,
                    'waypoints': cw,
                }
            },
            'navigating_waypoints': {
                'type': 'object',
                'value': nw,
                'metadata': {
                    'TimeInstant': {
                        'type': 'datetime',
                        'value': time,
                    }
                }
            },
            'remaining_waypoints_list': {
                'type': 'array',
                'value': rwl,
                'metadata': {
                    'TimeInstant': {
                        'type': 'datetime',
                        'value': time,
                    }
                }
            },
            'current_routes': {
                'type': 'array',
                'value': cr,
                'metadata': {
                    'TimeInstant': {
                        'type': 'datetime',
                        'value': time,
                    }
                }
            },
            'order': {
                'type': 'object',
                'value': o,
                'metadata': {
                    'TimeInstant': {
                        'type': 'datetime',
                        'value': time,
                    }
                }
            },
            'caller': {
                'type': 'string',
                'value': ca.value if isinstance(ca, caller.Caller) else None,
                'metadata': {
                    'TimeInstant': {
                        'type': 'datetime',
                        'value': time,
                    }
                }
            }
        }

        assert payload == {k: v for k, v in result.items()
                           if v['value'] is not None or k == 'navigating_waypoints'}


@pytest.mark.usefixtures('setup_environments', 'reload_module')
class TestMakeEmergencyCommand:

    @pytest.mark.parametrize('timezone, expected_datetime', [
        (None, '2020-01-01T18:04:05.000+00:00'),
        ('UTC', '2020-01-01T18:04:05.000+00:00'),
        ('Asia/Tokyo', '2020-01-02T03:04:05.000+09:00'),
    ])
    def test_timezone(self, timezone, expected_datetime):
        time = '2020-01-02T03:04:05+09:00'
        if timezone is not None:
            os.environ['TIMEZONE'] = timezone
            importlib.reload(const)
            importlib.reload(orion)

        cmd = 'test'

        with freezegun.freeze_time(time):
            payload = orion.make_emergency_command(cmd)

        result = {
            'send_emg': {
                'value': {
                    'time': expected_datetime,
                    'emergency_cmd': cmd,
                }
            }
        }

        assert payload == result

    @pytest.mark.parametrize('cmd', [
        'dummy', 0, 1e-1, True, [], ['a', 1], {}, {'a': 1}, tuple(['a', 1]), set([1, 2]), dt.datetime.utcnow(), None
    ])
    def test_args(self, cmd):
        time = '2020-01-02T03:04:05.000+00:00'

        with freezegun.freeze_time(time):
            payload = orion.make_emergency_command(cmd)

        assert payload == {
            'send_emg': {
                'value': {
                    'time': time,
                    'emergency_cmd': cmd,
                }
            }
        }


@pytest.mark.usefixtures('setup_environments', 'reload_module')
class TestMakeUpdateModeCommmand:

    @pytest.mark.parametrize('timezone, expected_datetime', [
        (None, '2020-01-01T18:04:05.000+00:00'),
        ('UTC', '2020-01-01T18:04:05.000+00:00'),
        ('Asia/Tokyo', '2020-01-02T03:04:05.000+09:00'),
    ])
    def test_timezone(self, timezone, expected_datetime):
        time = '2020-01-02T03:04:05+09:00'
        if timezone is not None:
            os.environ['TIMEZONE'] = timezone
            importlib.reload(const)
            importlib.reload(orion)

        next_mode = 'navi'

        with freezegun.freeze_time(time):
            payload = orion.make_updatemode_command(next_mode)

        assert payload == {
            'current_mode': {
                'type': 'string',
                'value': next_mode,
                'metadata': {
                    'TimeInstant': {
                        'type': 'datetime',
                        'value': expected_datetime,
                    }
                }
            },
        }

    @pytest.mark.parametrize('next_mode', [
        'dummy', 0, 1e-1, True, [], ['a', 1], {}, {'a': 1}, tuple(['a', 1]), set([1, 2]), dt.datetime.utcnow(), None
    ])
    def test_args(self, next_mode):
        time = '2020-01-02T03:04:05.000+00:00'

        with freezegun.freeze_time(time):
            payload = orion.make_updatemode_command(next_mode)

        assert payload == {
            'current_mode': {
                'type': 'string',
                'value': next_mode,
                'metadata': {
                    'TimeInstant': {
                        'type': 'datetime',
                        'value': time,
                    }
                }
            },
        }


@pytest.mark.usefixtures('setup_environments', 'reload_module')
class TestMakeUpdateStateCommmand:

    @pytest.mark.parametrize('timezone, expected_datetime', [
        (None, '2020-01-01T18:04:05.000+00:00'),
        ('UTC', '2020-01-01T18:04:05.000+00:00'),
        ('Asia/Tokyo', '2020-01-02T03:04:05.000+09:00'),
    ])
    def test_timezone(self, timezone, expected_datetime):
        time = '2020-01-02T03:04:05+09:00'
        if timezone is not None:
            os.environ['TIMEZONE'] = timezone
            importlib.reload(const)
            importlib.reload(orion)

        next_state = 'navi'

        with freezegun.freeze_time(time):
            payload = orion.make_updatestate_command(next_state)

        assert payload == {
            'current_state': {
                'type': 'string',
                'value': next_state,
                'metadata': {
                    'TimeInstant': {
                        'type': 'datetime',
                        'value': expected_datetime,
                    }
                }
            },
        }

    @pytest.mark.parametrize('next_state', [
        'dummy', 0, 1e-1, True, [], ['a', 1], {}, {'a': 1}, tuple(['a', 1]), set([1, 2]), dt.datetime.utcnow(), None
    ])
    def test_args(self, next_state):
        time = '2020-01-02T03:04:05.000+00:00'

        with freezegun.freeze_time(time):
            payload = orion.make_updatestate_command(next_state)

        assert payload == {
            'current_state': {
                'type': 'string',
                'value': next_state,
                'metadata': {
                    'TimeInstant': {
                        'type': 'datetime',
                        'value': time,
                    }
                }
            },
        }


@pytest.mark.usefixtures('setup_environments', 'reload_module')
class TestMakeRobotuiSendstateCommand:

    @pytest.mark.parametrize('timezone, expected_datetime', [
        (None, '2020-01-01T18:04:05.000+00:00'),
        ('UTC', '2020-01-01T18:04:05.000+00:00'),
        ('Asia/Tokyo', '2020-01-02T03:04:05.000+09:00'),
    ])
    def test_timezone(self, timezone, expected_datetime):
        time = '2020-01-02T03:04:05+09:00'
        if timezone is not None:
            os.environ['TIMEZONE'] = timezone
            importlib.reload(const)
            importlib.reload(orion)

        next_state = 'standby'
        destination = 'dest'

        with freezegun.freeze_time(time):
            payload = orion.make_robotui_sendstate_command(next_state, destination)

        assert payload == {
            'send_state': {
                'value': {
                    'time': expected_datetime,
                    'state': next_state,
                    'destination': destination,
                }
            },
        }

    @pytest.mark.parametrize('next_state, destination', [
        ('dummy', 0),
        (0, 1e-1),
        (1e-1, True),
        (True, []),
        ([], ['a', 1]),
        (['a', 1], {}),
        ({}, {'a': 1}),
        ({'a': 1}, tuple(['a', 1])),
        (tuple(['a', 1]), set([1, 2])),
        (set([1, 2]), dt.datetime.utcnow()),
        (dt.datetime.utcnow(), None),
        (None, 'dummy'),
    ])
    def test_args(self, next_state, destination):
        time = '2020-01-02T03:04:05.000+00:00'

        with freezegun.freeze_time(time):
            payload = orion.make_robotui_sendstate_command(next_state, destination)

        assert payload == {
            'send_state': {
                'value': {
                    'time': time,
                    'state': next_state,
                    'destination': destination,
                }
            },
        }


@pytest.mark.usefixtures('setup_environments', 'reload_module')
class TestMakeRobotuiSendtokeninfoCommand:

    @pytest.mark.parametrize('timezone, expected_datetime', [
        (None, '2020-01-01T18:04:05.000+00:00'),
        ('UTC', '2020-01-01T18:04:05.000+00:00'),
        ('Asia/Tokyo', '2020-01-02T03:04:05.000+09:00'),
    ])
    def test_timezone(self, timezone, expected_datetime):
        time = '2020-01-02T03:04:05+09:00'
        if timezone is not None:
            os.environ['TIMEZONE'] = timezone
            importlib.reload(const)
            importlib.reload(orion)

        tkn = token.Token.get('test')
        tkn.lock_owner_id = 'lock_owner_id'
        tkn.prev_owner_id = 'prev_owner_id'
        mode = token.TokenMode.LOCK

        with freezegun.freeze_time(time):
            payload = orion.make_robotui_sendtokeninfo_command(tkn, mode)

        assert payload == {
            'send_token_info': {
                'value': {
                    'time': expected_datetime,
                    'token': str(tkn),
                    'mode': str(mode),
                    'lock_owner_id': 'lock_owner_id',
                    'prev_owner_id': 'prev_owner_id',
                }
            },
        }

    @pytest.mark.parametrize('tkn, mode, loi, poi', [
        (token.Token(''), token.TokenMode.LOCK, 'dummy', 0),
        (token.Token('abc'), token.TokenMode.RELEASE, 0, 1e-1),
        (token.Token(''), token.TokenMode.SUSPEND, 1e-1, True),
        (token.Token('abc'), token.TokenMode.RESUME, True, []),
        (token.Token(''), token.TokenMode.LOCK, [], ['a', 1]),
        (token.Token('abc'), token.TokenMode.RELEASE, ['a', 1], {}),
        (token.Token(''), token.TokenMode.SUSPEND, {}, {'a': 1}),
        (token.Token('abc'), token.TokenMode.RESUME, {'a': 1}, tuple(['a', 1])),
        (token.Token(''), token.TokenMode.LOCK, tuple(['a', 1]), set([1, 2])),
        (token.Token('abc'), token.TokenMode.RELEASE, set([1, 2]), dt.datetime.utcnow()),
        (token.Token(''), token.TokenMode.SUSPEND, dt.datetime.utcnow(), None),
        (token.Token('abc'), token.TokenMode.RESUME, None, 'dummy'),

    ])
    def test_args(self, tkn, mode, loi, poi):
        time = '2020-01-02T03:04:05.000+00:00'
        tkn.lock_owner_id = loi
        tkn.prev_owner_id = poi

        with freezegun.freeze_time(time):
            payload = orion.make_robotui_sendtokeninfo_command(tkn, mode)

        assert payload == {
            'send_token_info': {
                'value': {
                    'time': time,
                    'token': str(tkn),
                    'mode': str(mode),
                    'lock_owner_id': loi,
                    'prev_owner_id': poi,
                }
            },
        }

    @pytest.mark.parametrize('tkn, mode', [
        ('dummy', 0),
        (0, 1e-1),
        (1e-1, True),
        (True, []),
        ([], ['a', 1]),
        (['a', 1], {}),
        ({}, {'a': 1}),
        ({'a': 1}, tuple(['a', 1])),
        (tuple(['a', 1]), set([1, 2])),
        (set([1, 2]), dt.datetime.utcnow()),
        (dt.datetime.utcnow(), None),
    ])
    def test_invalid_args(self, tkn, mode):

        with pytest.raises(TypeError) as e:
            orion.make_robotui_sendtokeninfo_command(tkn, mode)

        assert str(e.value) == 'invalid token or mode'


@pytest.mark.usefixtures('setup_environments', 'reload_module')
class TestMakeTokenInfoCommand:

    @pytest.mark.parametrize('timezone, expected_datetime', [
        (None, '2020-01-01T18:04:05.000+00:00'),
        ('UTC', '2020-01-01T18:04:05.000+00:00'),
        ('Asia/Tokyo', '2020-01-02T03:04:05.000+09:00'),
    ])
    def test_timezone(self, timezone, expected_datetime):
        time = '2020-01-02T03:04:05+09:00'
        if timezone is not None:
            os.environ['TIMEZONE'] = timezone
            importlib.reload(const)
            importlib.reload(orion)

        is_locked = True
        robot_id = 'robot_01'
        waitings = ['robot_02']

        with freezegun.freeze_time(time):
            payload = orion.make_token_info_command(is_locked, robot_id, waitings)

        assert payload == {
            'is_locked': {
                'type': 'boolean',
                'value': is_locked,
                'metadata': {
                    'TimeInstant': {
                        'type': 'datetime',
                        'value': expected_datetime,
                    }
                }
            },
            'lock_owner_id': {
                'type': 'string',
                'value': robot_id,
                'metadata': {
                    'TimeInstant': {
                        'type': 'datetime',
                        'value': expected_datetime,
                    }
                }
            },
            'waitings': {
                'type': 'array',
                'value': waitings,
                'metadata': {
                    'TimeInstant': {
                        'type': 'datetime',
                        'value': expected_datetime,
                    }
                }
            },
        }

    @pytest.mark.parametrize('is_locked, robot_id, waitings', [
        ('dummy', 0, 1e-1),
        (0, 1e-1, True),
        (1e-1, True, []),
        (True, [], ['a', 1]),
        ([], ['a', 1], {}),
        (['a', 1], {}, {'a': 1}),
        ({}, {'a': 1}, tuple(['a', 1])),
        ({'a': 1}, tuple(['a', 1]), set([1, 2])),
        (tuple(['a', 1]), set([1, 2]), dt.datetime.utcnow()),
        (set([1, 2]), dt.datetime.utcnow(), None),
        (dt.datetime.utcnow(), None, 'dummy'),
        (None, 'dummy', 0),
    ])
    def test_args(self, is_locked, robot_id, waitings):
        time = '2020-01-02T03:04:05.000+00:00'

        with freezegun.freeze_time(time):
            payload = orion.make_token_info_command(is_locked, robot_id, waitings)

        assert payload == {
            'is_locked': {
                'type': 'boolean',
                'value': is_locked,
                'metadata': {
                    'TimeInstant': {
                        'type': 'datetime',
                        'value': time,
                    }
                }
            },
            'lock_owner_id': {
                'type': 'string',
                'value': robot_id,
                'metadata': {
                    'TimeInstant': {
                        'type': 'datetime',
                        'value': time,
                    }
                }
            },
            'waitings': {
                'type': 'array',
                'value': waitings,
                'metadata': {
                    'TimeInstant': {
                        'type': 'datetime',
                        'value': time,
                    }
                }
            },
        }


@pytest.mark.usefixtures('setup_environments', 'reload_module')
class TestMakeUpdatelastprocessedtimeCommand:

    @pytest.mark.parametrize('timezone, expected_datetime', [
        (None, '2020-01-01T18:04:05.000+00:00'),
        ('UTC', '2020-01-01T18:04:05.000+00:00'),
        ('Asia/Tokyo', '2020-01-02T03:04:05.000+09:00'),
    ])
    def test_timezone(self, timezone, expected_datetime):
        time = '2020-01-02T03:04:05+09:00'
        if timezone is not None:
            os.environ['TIMEZONE'] = timezone
            importlib.reload(const)
            importlib.reload(orion)

        lpt_time = '2020-02-03T04:05:06.789+09:00'
        lpt = dateutil.parser.parse(lpt_time)

        with freezegun.freeze_time(time):
            payload = orion.make_updatelastprocessedtime_command(lpt)

        assert payload == {
            'last_processed_time': {
                'type': 'ISO8601',
                'value': lpt.isoformat(timespec='milliseconds'),
                'metadata': {
                    'TimeInstant': {
                        'type': 'datetime',
                        'value': expected_datetime,
                    }
                }
            },
        }

    @pytest.mark.parametrize('lpt', [
        'dummy', 0, 1e-1, True, [], ['a', 1], {}, {'a': 1}, tuple(['a', 1]), set([1, 2]), token.Token(''), None
    ])
    def test_invalid_args(self, lpt):

        with pytest.raises(TypeError) as e:
            orion.make_updatelastprocessedtime_command(lpt)

        assert str(e.value) == 'last_processed_time is must be "datetime"'
