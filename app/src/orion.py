import datetime
import json
import os

from flask import abort

import pytz

import requests

from src import const

TZ = pytz.timezone(const.TIMEZONE)


def send_command(fiware_service, fiware_servicepath, entity_type, entity_id, payload):
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
    if caller is not None:
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


def query_entity(fiware_service, fiware_servicepath, entity_type, query):
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
