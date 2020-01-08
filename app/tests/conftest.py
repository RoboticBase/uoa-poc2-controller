import os

import pytest

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
    os.environ[ORION_ENDPOINT] = 'dummy'
    os.environ[FIWARE_SERVICE] = 'dummy'
    os.environ[DELIVERY_ROBOT_SERVICEPATH] = 'dummy'
    os.environ[DELIVERY_ROBOT_TYPE] = 'dummy'
    os.environ[DELIVERY_ROBOT_LIST] = '[]'
    os.environ[ROBOT_UI_SERVICEPATH] = 'dummy'
    os.environ[ROBOT_UI_TYPE] = 'dummy'
    os.environ[ID_TABLE] = '{}'
    os.environ[TOKEN_SERVICEPATH] = 'dummy'
    os.environ[TOKEN_TYPE] = 'dummy'
    os.environ[MONGODB_HOST] = 'dummy'
    os.environ[MONGODB_PORT] = '0'
    os.environ[MONGODB_REPLICASET] = 'dummy'
    os.environ[MONGODB_DB_NAME] = 'dummy'
    os.environ[MONGODB_COLLECTION_NAME] = 'dummy'


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
