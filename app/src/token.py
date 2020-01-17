from enum import Enum
from logging import getLogger

from src import const, orion

logger = getLogger(__name__)


class Token:
    _tokens = {}

    @classmethod
    def get(cls, token):
        if not isinstance(token, str):
            raise TypeError('token must be "str"')
        if token not in cls._tokens:
            cls._tokens[token] = cls(token)
        return cls._tokens[token]

    def __init__(self, token):
        if not isinstance(token, str):
            raise TypeError('token must be "str"')
        self._token = token
        self._entity = None
        self.is_locked = False
        self.lock_owner_id = ""
        self.prev_owner_id = ""
        self.waitings = []

    def _renew_entity(self):
        self._entity = orion.get_entity(
            const.FIWARE_SERVICE,
            const.TOKEN_SERVICEPATH,
            const.TOKEN_TYPE,
            self._token)
        self.is_locked = self._entity['is_locked']['value']
        self.lock_owner_id = self._entity['lock_owner_id']['value']
        self.waitings = self._entity['waitings']['value']

    def get_lock(self, robot_id):
        self._renew_entity()
        if not self.is_locked:
            self.is_locked = True
            self.prev_owner_id = self.lock_owner_id
            self.lock_owner_id = robot_id
            self.waitings = []

            payload = orion.make_token_info_command(self.is_locked, self.lock_owner_id, self.waitings)
            orion.send_command(
                const.FIWARE_SERVICE,
                const.TOKEN_SERVICEPATH,
                const.TOKEN_TYPE,
                self._token,
                payload)
            logger.info(f'lock token ({self._token}) by {robot_id}')
            return True
        else:
            if robot_id not in self.waitings:
                self.waitings = self.waitings + [robot_id]

                payload = orion.make_token_info_command(self.is_locked, self.lock_owner_id, self.waitings)
                orion.send_command(
                    const.FIWARE_SERVICE,
                    const.TOKEN_SERVICEPATH,
                    const.TOKEN_TYPE,
                    self._token,
                    payload)
                logger.info(f'wait token ({self._token}) by {robot_id}')
            return False

    def release_lock(self, robot_id):
        self._renew_entity()
        if len(self.waitings) == 0:
            self.is_locked = False
            self.prev_owner_id = self.lock_owner_id
            self.lock_owner_id = ''
            self.waitings = []

            payload = orion.make_token_info_command(self.is_locked, self.lock_owner_id, self.waitings)
            orion.send_command(
                const.FIWARE_SERVICE,
                const.TOKEN_SERVICEPATH,
                const.TOKEN_TYPE,
                self._token,
                payload)
            logger.info(f'release token ({self._token}) by {robot_id}')
            return None
        else:
            new_owner, *new_waitings = self.waitings
            self.is_locked = True
            self.prev_owner_id = self.lock_owner_id
            self.lock_owner_id = new_owner
            self.waitings = new_waitings

            payload = orion.make_token_info_command(self.is_locked, self.lock_owner_id, self.waitings)
            orion.send_command(
                const.FIWARE_SERVICE,
                const.TOKEN_SERVICEPATH,
                const.TOKEN_TYPE,
                self._token,
                payload)
            logger.info(f'switch token ({self._token}) from {robot_id} to {new_owner}')
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
