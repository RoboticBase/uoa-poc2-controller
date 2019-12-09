import datetime
from dataclasses import dataclass
from enum import Enum

from logging import getLogger

import pytz

from pymongo import MongoClient

from src import const

TZ = pytz.timezone(const.TIMEZONE)
logger = getLogger(__name__)


class StateMessage:
    id = '01'
    ac = 'ロボットの状態'


class DestinationMessage:
    id = '02'
    ac = 'ロボットの目的地'


class TokenMessage:
    id = '03'
    ac = 'トークンの状態'


class MessageType(Enum):
    State = StateMessage
    Destination = DestinationMessage
    Token = TokenMessage


class MongoMessage:
    _collection = None

    @classmethod
    def _get_mongo_collection(cls):
        if cls._collection is None:
            mongo_client = MongoClient(
                const.MONGODB_HOST,
                const.MONGODB_PORT,
                replicaset=const.MONGODB_REPLICASET)
            cls._collection = mongo_client[const.MONGODB_DB_NAME]['messages']
        return cls._collection

    @classmethod
    def write(cls, robot_id, message_type, message):
        collection = cls._get_mongo_collection()
        t = datetime.datetime.now(TZ).isoformat(timespec='milliseconds')
        data = {
            'time': t,
            'robot_id': robot_id,
            'message_id': message_type.value.id,
            'message': f'[{t}] {message}',
        }
        inserted_id = collection.insert_one(data)
        logger.info(f'write mongodb data={data}')
        return inserted_id
