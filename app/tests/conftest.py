import os
import importlib

import pytest
import lazy_import

ORION_ENDPOINT = 'ORION_ENDPOINT'
FIWARE_SERVICE = 'FIWARE_SERVICE'
DELIVERY_ROBOT_SERVICEPATH = 'DELIVERY_ROBOT_SERVICEPATH'
DELIVERY_ROBOT_TYPE = 'DELIVERY_ROBOT_TYPE'
DELIVERY_ROBOT_LIST = 'DELIVERY_ROBOT_LIST'
ROBOT_UI_SERVICEPATH = 'ROBOT_UI_SERVICEPATH'
ROBOT_UI_TYPE = 'ROBOT_UI_TYPE'
ID_TABLE = 'ID_TABLE'
TOKEN_SERVICEPATH = 'TOKEN_SERVICEPATH'
TOKEN_TYPE = 'TOKEN_TYPE'
MONGODB_HOST = 'MONGODB_HOST'
MONGODB_PORT = 'MONGODB_PORT'
MONGODB_REPLICASET = 'MONGODB_REPLICASET'
MONGODB_DB_NAME = 'MONGODB_DB_NAME'
MONGODB_COLLECTION_NAME = 'MONGODB_COLLECTION_NAME'


@pytest.fixture(scope='function')
def setup_environments():
    os.environ[ORION_ENDPOINT] = 'ORION_ENDPOINT'
    os.environ[FIWARE_SERVICE] = 'FIWARE_SERVICE'
    os.environ[DELIVERY_ROBOT_SERVICEPATH] = 'DELIVERY_ROBOT_SERVICEPATH'
    os.environ[DELIVERY_ROBOT_TYPE] = 'DELIVERY_ROBOT_TYPE'
    os.environ[DELIVERY_ROBOT_LIST] = '["robot_01", "robot_02"]'
    os.environ[ROBOT_UI_SERVICEPATH] = 'ROBOT_UI_SERVICEPATH'
    os.environ[ROBOT_UI_TYPE] = 'ROBOT_UI_TYPE'
    os.environ[ID_TABLE] = '{"robot_01": "ui_01", "robot_02": "ui_02"}'
    os.environ[TOKEN_SERVICEPATH] = 'TOKEN_SERVICEPATH'
    os.environ[TOKEN_TYPE] = 'TOKEN_TYPE'
    os.environ[MONGODB_HOST] = 'MONGODB_HOST'
    os.environ[MONGODB_PORT] = '27017'
    os.environ[MONGODB_REPLICASET] = 'MONGODB_REPLICASET'
    os.environ[MONGODB_DB_NAME] = 'MONGODB_DB_NAME'
    os.environ[MONGODB_COLLECTION_NAME] = 'MONGODB_COLLECTION_NAME'


@pytest.fixture(scope='function', autouse=True)
def teardown_enviroments():
    yield

    if ORION_ENDPOINT in os.environ:
        del os.environ[ORION_ENDPOINT]
    if FIWARE_SERVICE in os.environ:
        del os.environ[FIWARE_SERVICE]
    if DELIVERY_ROBOT_SERVICEPATH in os.environ:
        del os.environ[DELIVERY_ROBOT_SERVICEPATH]
    if DELIVERY_ROBOT_TYPE in os.environ:
        del os.environ[DELIVERY_ROBOT_TYPE]
    if DELIVERY_ROBOT_LIST in os.environ:
        del os.environ[DELIVERY_ROBOT_LIST]
    if ROBOT_UI_SERVICEPATH in os.environ:
        del os.environ[ROBOT_UI_SERVICEPATH]
    if ROBOT_UI_TYPE in os.environ:
        del os.environ[ROBOT_UI_TYPE]
    if ID_TABLE in os.environ:
        del os.environ[ID_TABLE]
    if TOKEN_SERVICEPATH in os.environ:
        del os.environ[TOKEN_SERVICEPATH]
    if TOKEN_TYPE in os.environ:
        del os.environ[TOKEN_TYPE]
    if MONGODB_HOST in os.environ:
        del os.environ[MONGODB_HOST]
    if MONGODB_PORT in os.environ:
        del os.environ[MONGODB_PORT]
    if MONGODB_REPLICASET in os.environ:
        del os.environ[MONGODB_REPLICASET]
    if MONGODB_DB_NAME in os.environ:
        del os.environ[MONGODB_DB_NAME]
    if MONGODB_COLLECTION_NAME in os.environ:
        del os.environ[MONGODB_COLLECTION_NAME]


@pytest.fixture
def app():
    main = lazy_import.lazy_module('main')
    yield main.app
    importlib.reload(main)


@pytest.fixture
def const():
    const = lazy_import.lazy_module('src.const')
    return const
