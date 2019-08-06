import datetime
import os

from flask import abort

import pytz

import requests

from src import const

ORION_ENDPOINT = os.environ[const.ORION_ENDPOINT]
TZ = pytz.timezone(os.environ.get(const.TIMEZONE, 'UTC'))


def send_command(fiware_service, fiware_servicepath, entity_type, entity_id, payload):
    headers = {
        'Content-Type': 'application/json',
        'FIWARE-SERVICE': fiware_service,
        'FIWARE-SERVICEPATH': fiware_servicepath,
    }
    if const.ORION_TOKEN in os.environ:
        headers['Authorization'] = f'bearer {os.environ[const.ORION_TOKEN]}'
    path = os.path.join(const.ORION_BAAE_PATH, entity_id, 'attrs')
    endpoint = f'{ORION_ENDPOINT}{path}?type={entity_type}'

    result = requests.patch(endpoint, headers=headers, json=payload)
    if not (200 <= result.status_code < 300):
        code = result.status_code if result.status_code in (404, ) else 500
        abort(code, {
            'message': 'can not put stock detail to zaico',
            'root_cause': result.text if hasattr(result, 'text') else ''
        })

    return result


def make_delivery_robot_command(cmd, waypoints):
    return {
        'send_cmd': {
            'value': {
                'time': datetime.datetime.now(TZ).isoformat(),
                'cmd': cmd,
                'waypoints': waypoints
            },
        },
    }
