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
ETCD_HOST = os.environ['ETCD_HOST']
ETCD_PORT = int(os.environ['ETCD_PORT'])
ETCD_LOCK_TTL_SEC = int(os.environ.get('ETCD_LOCK_TTL_SEC', '60'))
SHIPMENTAPI_LOCK_TIMEOUT_SEC = int(os.environ.get('SHIPMENTAPI_LOCK_TIMEOUT_SEC', '10'))
MOVENEXTAPI_LOCK_TIMEOUT_SEC = int(os.environ.get('MOVENEXTAPI_LOCK_TIMEOUT_SEC', '10'))

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

# move_next
WAIT_MSEC = 500
WAIT_MAX_NUM = 10

# notification
THROTTLING_MSEC = 500

# etcd_lock
DEFAULT_LOCK_TIMEOUT_SEC = 10
