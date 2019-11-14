import os
import json
from enum import Enum

from src import const, orion

FIWARE_SERVICE = os.environ[const.FIWARE_SERVICE]
TOKEN_SERVICEPATH = os.environ[const.TOKEN_SERVICEPATH]
TOKEN_TYPE = os.environ[const.TOKEN_TYPE]


class Token:
    _tokens = {}

    @classmethod
    def get(cls, token):
        if token not in cls._tokens:
            cls._tokens[token] = cls(token)
        return cls._tokens[token]

    def __init__(self, token):
        self._token = token

    def get_lock(self, robot_id):
        token_entity = orion.get_entity(
            FIWARE_SERVICE,
            TOKEN_SERVICEPATH,
            TOKEN_TYPE,
            self._token)
        is_locked = token_entity['is_locked']['value']
        waitings = token_entity['waitings']['value']

        if not is_locked:
            payload = orion.make_token_lock_command(robot_id, [])
            orion.send_command(
                FIWARE_SERVICE,
                TOKEN_SERVICEPATH,
                TOKEN_TYPE,
                self._token,
                payload)
            print(f'lock token ({self._token}) by {robot_id}')
            return True
        else:
            if robot_id not in waitings:
                payload = orion.make_token_wait_command(waitings, robot_id)
                orion.send_command(
                    FIWARE_SERVICE,
                    TOKEN_SERVICEPATH,
                    TOKEN_TYPE,
                    self._token,
                    payload)
                print(f'wait token ({self._token}) by {robot_id}')
            return False

    def release_lock(self, robot_id):
        token_entity = orion.get_entity(
            FIWARE_SERVICE,
            TOKEN_SERVICEPATH,
            TOKEN_TYPE,
            self._token)

        waitings = token_entity['waitings']['value']
        if len(waitings) == 0:
            payload = orion.make_token_release_command()
            orion.send_command(
                FIWARE_SERVICE,
                TOKEN_SERVICEPATH,
                TOKEN_TYPE,
                self._token,
                payload)
            print(f'release token ({self._token}) by {robot_id}')
            return None
        else:
            new_owner, *new_waitings = waitings
            payload = orion.make_token_lock_command(new_owner, new_waitings)
            orion.send_command(
                FIWARE_SERVICE,
                TOKEN_SERVICEPATH,
                TOKEN_TYPE,
                self._token,
                payload)
            print(f'switch token ({self._token}) from {robot_id} to {new_owner}')
            return new_owner

    def __str__(self):
        return self._token


class TokenMode(Enum):
    LOCK = 'lock'
    RELEASE = 'release'
    SUSPEND = 'suspend'
    RESUME = 'resume'

    def __str__(self):
        return self.value
