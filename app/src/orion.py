import datetime
import json
import os

from flask import abort

import pytz

import requests

from src import const

ORION_ENDPOINT = os.environ[const.ORION_ENDPOINT]
TZ = pytz.timezone(os.environ.get(const.TIMEZONE, 'UTC'))
ORION_TOKEN = os.environ.get(const.ORION_TOKEN)


def send_command(fiware_service, fiware_servicepath, entity_type, entity_id, payload):
    headers = __make_headers(fiware_service, fiware_servicepath, True)
    path = os.path.join(const.ORION_BASE_PATH, entity_id, 'attrs')
    endpoint = f'{ORION_ENDPOINT}{path}?type={entity_type}'

    result = requests.patch(endpoint, headers=headers, json=payload)
    print(result)
    print(result.text)
    if not (200 <= result.status_code < 300):
        code = result.status_code if result.status_code in (404, ) else 500
        abort(code, {
            'message': 'can not send command to orion',
            'root_cause': result.text if hasattr(result, 'text') else ''
        })

    return result


def make_delivery_robot_command(cmd, cmd_waypoints, navigating_waypoints, remaining_waypoints_list, current_routes=None):
    t = datetime.datetime.now(TZ).isoformat(timespec='milliseconds')
    payload = {
        'send_cmd': {
            'value': {
                'time': t,
                'cmd': cmd,
                'waypoints': cmd_waypoints,
            },
        },
        'navigating_waypoints': {
            'type': 'object',
            'value': navigating_waypoints,
            'metadata': {
                'TimeInstant': {
                    'type': 'datetime',
                    'value': t,
                }
            }
        },
        'remaining_waypoints_list': {
            'type': 'array',
            'value': remaining_waypoints_list,
            'metadata': {
                'TimeInstant': {
                    'type': 'datetime',
                    'value': t,
                }
            }
        }
    }
    if current_routes:
        payload['current_routes'] = {
            'type': 'array',
            'value': current_routes,
            'metadata': {
                'TimeInstant': {
                    'type': 'datetime',
                    'value': t,
                }
            }
        }
    return payload


def query_entity(fiware_service, fiware_servicepath, entity_type, query):
    headers = __make_headers(fiware_service, fiware_servicepath)
    endpoint = f'{ORION_ENDPOINT}{const.ORION_BASE_PATH}'
    params = {
        'type': entity_type,
        'q': query,
    }
    result = requests.get(endpoint, headers=headers, params=params)
    if not (200 <= result.status_code < 300):
        code = result.status_code if result.status_code in (404, ) else 500
        abort(code, {
            'message': 'can not get entities from orion',
            'root_cause': result.text if hasattr(result, 'text') else ''
        })
    try:
        result_json = result.json()
    except json.decoder.JSONDecodeError as e:
        abort(400, {
            'message': 'can not parse result',
            'root_cause': str(e)
        })
    if not (result_json and isinstance(result_json, list) and len(result_json) == 1):
        abort(400, {
            'message': f'can not retrieve an entity, entity_type={entity_type}, query={query}',
        })

    return result_json[0]


def get_entity(fiware_service, fiware_servicepath, entity_type, entity_id):
    headers = __make_headers(fiware_service, fiware_servicepath)
    endpoint = f'{ORION_ENDPOINT}{const.ORION_BASE_PATH}{entity_id}'
    params = {
        'type': entity_type
    }
    result = requests.get(endpoint, headers=headers, params=params)
    if not (200 <= result.status_code < 300):
        code = result.status_code if result.status_code in (404, ) else 500
        abort(code, {
            'message': 'can not get an entity from orion',
            'root_cause': result.text if hasattr(result, 'text') else ''
        })
    try:
        result_json = result.json()
    except json.decoder.JSONDecodeError as e:
        abort(400, {
            'message': 'can not parse result',
            'root_cause': str(e)
        })
    return result_json


def __make_headers(fiware_service, fiware_servicepath, require_contenttype=False):
    headers = {
        'FIWARE-SERVICE': fiware_service,
        'FIWARE-SERVICEPATH': fiware_servicepath,
    }
    if ORION_TOKEN:
        headers['Authorization'] = f'bearer {ORION_TOKEN}'
    if require_contenttype:
        headers['Content-Type'] = 'application/json'

    return headers
