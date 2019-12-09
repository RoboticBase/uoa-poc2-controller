import os
import json

# environment variables
LOG_LEVEL = 'LOG_LEVEL'
LISTEN_PORT = 'LISTEN_PORT'
TIMEZONE = os.environ.get('TIMEZONE', 'UTC')
ORION_ENDPOINT = os.environ['ORION_ENDPOINT']
ORION_TOKEN = os.environ.get('ORION_TOKEN', None)
FIWARE_SERVICE = os.environ['FIWARE_SERVICE']
DELIVERY_ROBOT_SERVICEPATH = os.environ['DELIVERY_ROBOT_SERVICEPATH']
DELIVERY_ROBOT_TYPE = os.environ['DELIVERY_ROBOT_TYPE']
DELIVERY_ROBOT_LIST = json.loads(os.environ['DELIVERY_ROBOT_LIST'])
ROBOT_UI_SERVICEPATH = os.environ['ROBOT_UI_SERVICEPATH']
ROBOT_UI_TYPE = os.environ['ROBOT_UI_TYPE']
ID_TABLE = json.loads(os.environ['ID_TABLE'])
CORS_ORIGINS = os.environ.get('CORS_ORIGINS', None)
TOKEN_SERVICEPATH = os.environ['TOKEN_SERVICEPATH']
TOKEN_TYPE = os.environ['TOKEN_TYPE']
MOVENEXT_WAIT_MSEC = int(os.environ.get('MOVENEXT_WAIT_MSEC', '200'))
MOVENEXT_WAIT_MAX_NUM = int(os.environ.get('MOVENEXT_WAIT_MAX_NUM', '25'))
NOTIFICATION_THROTTLING_MSEC = int(os.environ.get('NOTIFICATION_THROTTLING_MSEC', '500'))
MONGODB_HOST = os.environ['MONGODB_HOST']
MONGODB_PORT = int(os.environ['MONGODB_PORT'])
MONGODB_REPLICASET = os.environ['MONGODB_REPLICASET']
MONGODB_DB_NAME = os.environ['MONGODB_DB_NAME']
MONGODB_COLLECTION_NAME = os.environ['MONGODB_COLLECTION_NAME']

# constants
ORION_BASE_PATH = '/v2/entities/'
PLACE_TYPE = 'place'
ROUTE_PLAN_TYPE = 'route_plan'
VIA_SEPARATOR = '|'
ORION_LIST_NUM_LIMIT = 1000

# Robot mode
MODE_INIT = ' '
MODE_NAVI = 'navi'
MODE_STANDBY = 'standby'
MODE_ERROR = 'error'

# Robot state
STATE_MOVING = 'moving'
STATE_STANDBY = 'standby'
STATE_PICKING = 'picking'
STATE_DELIVERING = 'delivering'

# caller
ORDERING_LIST = ['zaico-extensions', ]

# logging
LOGGING_JSON = 'logging.json'
TARGET_HANDLERS = ['console', ]

# etcd_lock
DEFAULT_LOCK_TIMEOUT_SEC = 600

REVERSE_ID_TABLE = {v: k for k, v in ID_TABLE.items()}
