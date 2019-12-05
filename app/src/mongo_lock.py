import datetime
from logging import getLogger

from pymongo import MongoClient

from src import const

logger = getLogger(__name__)


class MongoLockError(Exception):
    pass


class MongoThrottling:
    _throttling_msec = None
    _collection = None

    @classmethod
    def _throttling(cls):
        if cls._throttling_msec is None:
            cls._throttling_msec = datetime.timedelta(milliseconds=const.NOTIFICATION_THROTTLING_MSEC)
        return cls._throttling_msec

    @classmethod
    def _get_mongo_collection(cls):
        if cls._collection is None:
            mongo_client = MongoClient(
                const.MONGODB_HOST,
                const.MONGODB_PORT,
                replicaset=const.MONGODB_REPLICASET)
            cls._collection = mongo_client[const.MONGODB_DB_NAME][const.MONGODB_COLLECTION_NAME]
            for robot_id in const.ID_TABLE.keys():
                cls._collection.replace_one(
                    {'robot_id': robot_id},
                    {'robot_id': robot_id, 'time': datetime.datetime.utcnow()},
                    upsert=True)
        return cls._collection

    @classmethod
    def lock(cls, robot_id, time):
        # lock = cls._get_mongo_collection().find_one_and_update(
        #     {
        #         'robot_id': robot_id,
        #         'time': {
        #             '$lte': time - cls._throttling()
        #         },
        #     },
        #     {
        #         '$set': {
        #             'time': time
        #         }
        #     }
        # )
        # if lock is None:
        #     msg = f'ignore notification, robot_id={robot_id}, time={time.isoformat()}, ' \
        #         f'timedelta lower than the throttling={cls._throttling()}'
        #     raise MongoLockError(msg)
        #
        # logger.debug(f'update last_processed_time, robot_id={robot_id}, old={lock["time"].isoformat()}, new={time.isoformat()}')
        # return lock
        return None
