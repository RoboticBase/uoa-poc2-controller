import datetime
import json
import os

from flask import abort

import pytz

import requests

from src import const
from src.utils import is_jsonable
from src.caller import Caller

TZ = pytz.timezone(const.TIMEZONE)


def send_command(fiware_service, fiware_servicepath, entity_type, entity_id, payload):
    if not (isinstance(fiware_service, str) and isinstance(fiware_servicepath, str)
            and isinstance(entity_type, str) and isinstance(entity_id, str)):
        raise TypeError('fiware_service, fiware_servicepath, entity_type and entity_id must be "str"')
    if not is_jsonable(payload):
        raise TypeError('payload must be json serializable')

    headers = __make_headers(fiware_service, fiware_servicepath, True)
    path = os.path.join(const.ORION_BASE_PATH, entity_id, 'attrs')
    endpoint = f'{const.ORION_ENDPOINT}{path}?type={entity_type}'

    result = requests.patch(endpoint, headers=headers, json=payload)
    if not (200 <= result.status_code < 300):
        code = result.status_code if result.status_code in (404, ) else 500
        abort(code, {
            'message': 'can not send command to orion',
            'root_cause': result.text if hasattr(result, 'text') else ''
        })

    return result


def query_entity(fiware_service, fiware_servicepath, entity_type, query):
    if not (isinstance(fiware_service, str) and isinstance(fiware_servicepath, str)
            and isinstance(entity_type, str) and isinstance(query, str)):
        raise TypeError('fiware_service, fiware_servicepath, entity_type and query must be "str"')

    headers = __make_headers(fiware_service, fiware_servicepath)
    endpoint = f'{const.ORION_ENDPOINT}{const.ORION_BASE_PATH}'
    params = {
        'type': entity_type,
        'limit': const.ORION_LIST_NUM_LIMIT,
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


def get_entities(fiware_service, fiware_servicepath, entity_type):
    if not (isinstance(fiware_service, str) and isinstance(fiware_servicepath, str) and isinstance(entity_type, str)):
        raise TypeError('fiware_service, fiware_servicepath and entity_type must be "str"')


    headers = __make_headers(fiware_service, fiware_servicepath)
    endpoint = f'{const.ORION_ENDPOINT}{const.ORION_BASE_PATH}'
    params = {
        'type': entity_type,
        'limit': const.ORION_LIST_NUM_LIMIT,
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
    return result_json


def get_entity(fiware_service, fiware_servicepath, entity_type, entity_id):
    if not (isinstance(fiware_service, str) and isinstance(fiware_servicepath, str)
            and isinstance(entity_type, str) and isinstance(entity_id, str)):
        raise TypeError('fiware_service, fiware_servicepath, entity_type and entity_id must be "str"')

    headers = __make_headers(fiware_service, fiware_servicepath)
    endpoint = f'{const.ORION_ENDPOINT}{const.ORION_BASE_PATH}{entity_id}'
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
    if const.ORION_TOKEN:
        headers['Authorization'] = f'bearer {const.ORION_TOKEN}'
    if require_contenttype:
        headers['Content-Type'] = 'application/json'

    return headers


def make_delivery_robot_command(cmd, cmd_waypoints, navigating_waypoints,
                                remaining_waypoints_list=None, current_routes=None, order=None, caller=None):
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
    }
    if remaining_waypoints_list is not None:
        payload['remaining_waypoints_list'] = {
            'type': 'array',
            'value': remaining_waypoints_list,
            'metadata': {
                'TimeInstant': {
                    'type': 'datetime',
                    'value': t,
                }
            }
        }
    if current_routes is not None:
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
    if order is not None:
        payload['order'] = {
            'type': 'object',
            'value': order,
            'metadata': {
                'TimeInstant': {
                    'type': 'datetime',
                    'value': t,
                }
            }
        }
    if caller is not None and isinstance(caller, Caller):
        payload['caller'] = {
            'type': 'string',
            'value': caller.value,
            'metadata': {
                'TimeInstant': {
                    'type': 'datetime',
                    'value': t,
                }
            }
        }
    return payload


def make_emergency_command(cmd):
    t = datetime.datetime.now(TZ).isoformat(timespec='milliseconds')
    payload = {
        'send_emg': {
            'value': {
                'time': t,
                'emergency_cmd': cmd,
            }
        }
    }
    return payload


def make_updatemode_command(next_mode):
    t = datetime.datetime.now(TZ).isoformat(timespec='milliseconds')
    payload = {
        'current_mode': {
            'type': 'string',
            'value': next_mode,
            'metadata': {
                'TimeInstant': {
                    'type': 'datetime',
                    'value': t,
                }
            }
        },
    }
    return payload


def make_updatestate_command(next_state):
    t = datetime.datetime.now(TZ).isoformat(timespec='milliseconds')
    payload = {
        'current_state': {
            'type': 'string',
            'value': next_state,
            'metadata': {
                'TimeInstant': {
                    'type': 'datetime',
                    'value': t,
                }
            }
        },
    }
    return payload


def make_robotui_sendstate_command(next_state, destination):
    t = datetime.datetime.now(TZ).isoformat(timespec='milliseconds')
    payload = {
        'send_state': {
            'value': {
                'time': t,
                'state': next_state,
                'destination': destination,
            }
        },
    }
    return payload


def make_robotui_sendtokeninfo_command(token, mode):
    import src.token
    if not (isinstance(token, src.token.Token) and isinstance(mode, src.token.TokenMode)):
        raise TypeError('invalid token or mode')

    t = datetime.datetime.now(TZ).isoformat(timespec='milliseconds')
    payload = {
        'send_token_info': {
            'value': {
                'time': t,
                'token': str(token),
                'mode': str(mode),
                'lock_owner_id': token.lock_owner_id,
                'prev_owner_id': token.prev_owner_id,
            }
        },
    }
    return payload


def make_token_info_command(is_locked, robot_id, waitings):
    t = datetime.datetime.now(TZ).isoformat(timespec='milliseconds')
    payload = {
        'is_locked': {
            'type': 'boolean',
            'value': is_locked,
            'metadata': {
                'TimeInstant': {
                    'type': 'datetime',
                    'value': t,
                }
            }
        },
        'lock_owner_id': {
            'type': 'string',
            'value': robot_id,
            'metadata': {
                'TimeInstant': {
                    'type': 'datetime',
                    'value': t,
                }
            }
        },
        'waitings': {
            'type': 'array',
            'value': waitings,
            'metadata': {
                'TimeInstant': {
                    'type': 'datetime',
                    'value': t,
                }
            }
        },
    }
    return payload


def make_updatelastprocessedtime_command(last_processed_time):
    if not isinstance(last_processed_time, datetime.datetime):
        raise TypeError('last_processed_time is must be "datetime"')

    t = datetime.datetime.now(TZ).isoformat(timespec='milliseconds')
    payload = {
        'last_processed_time': {
            'type': 'ISO8601',
            'value': last_processed_time.isoformat(timespec='milliseconds'),
            'metadata': {
                'TimeInstant': {
                    'type': 'datetime',
                    'value': t,
                }
            }
        },
    }
    return payload
