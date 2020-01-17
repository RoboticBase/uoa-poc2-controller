import datetime
import importlib
from unittest.mock import call

import pytest
import freezegun
import lazy_import
mongo_lock = lazy_import.lazy_module('src.mongo_lock')
const = lazy_import.lazy_module('src.const')


@pytest.fixture
def MongoThrottling():
    yield mongo_lock.MongoThrottling
    importlib.reload(mongo_lock)


@pytest.fixture
def mocked_mongo(mocker):
    mongo_lock.MongoClient = mocker.MagicMock()
    collection = mocker.MagicMock()
    mongo_lock.MongoClient.return_value = {
        const.MONGODB_DB_NAME: {
            const.MONGODB_COLLECTION_NAME: collection
        }
    }
    yield mongo_lock.MongoClient, collection


class TestMongoThrottlingLock:

    def test_lock_success(self, mocker, MongoThrottling, mocked_mongo):
        robot_id = 'robot_01'
        MongoClient, collection = mocked_mongo
        time = datetime.datetime.fromisoformat('2020-01-02T03:04:05+09:00')
        result = {
            'time': datetime.datetime.fromisoformat('2020-02-03T04:05:06+09:00')
        }
        collection.find_one_and_update.return_value = result

        lock = MongoThrottling.lock(robot_id, time)

        assert MongoClient.call_count == 1
        assert MongoClient.call_args == call(const.MONGODB_HOST, int(const.MONGODB_PORT), replicaset=const.MONGODB_REPLICASET)
        assert MongoThrottling._collection.find_one_and_update.call_count == 1
        assert MongoThrottling._collection.find_one_and_update.call_args == call(
            {
                'robot_id': robot_id,
                'time': {
                    '$lte': datetime.datetime.fromisoformat('2020-01-02 03:04:04.500000+09:00')
                }
            },
            {
                '$set': {
                    'time': time
                }
            }
        )
        assert lock == result

    def test_lock_error(self, mocker, MongoThrottling, mocked_mongo):
        robot_id = 'robot_01'
        MongoClient, collection = mocked_mongo
        time = datetime.datetime.fromisoformat('2020-01-02T03:04:05+09:00')
        collection.find_one_and_update.return_value = None

        with pytest.raises(mongo_lock.MongoLockError) as e:
            MongoThrottling.lock(robot_id, time)

        assert MongoClient.call_count == 1
        assert MongoClient.call_args == call(const.MONGODB_HOST, int(const.MONGODB_PORT), replicaset=const.MONGODB_REPLICASET)
        assert collection.find_one_and_update.call_count == 1
        assert collection.find_one_and_update.call_args == call(
            {
                'robot_id': robot_id,
                'time': {
                    '$lte': datetime.datetime.fromisoformat('2020-01-02 03:04:04.500000+09:00')
                }
            },
            {
                '$set': {
                    'time': time
                }
            }
        )
        assert str(e.value) == f'ignore notification, robot_id={robot_id}, time={time.isoformat()}, ' \
            f'timedelta lower than the throttling={MongoThrottling._throttling()}'

    @pytest.mark.parametrize('robot_id, exception', [
        (None, TypeError),
        (1, TypeError),
        (True, TypeError),
        ({}, TypeError),
        ([], TypeError),
    ])
    def test_lock_robotid_exception(self, mocker, MongoThrottling, mocked_mongo, robot_id, exception):
        _, collection = mocked_mongo
        time = datetime.datetime.fromisoformat('2020-01-02T03:04:05+09:00')

        result = {
            'time': datetime.datetime.fromisoformat('2020-02-03T04:05:06+09:00')
        }
        collection.find_one_and_update.return_value = result

        with pytest.raises(exception):
            MongoThrottling.lock(robot_id, time)

    @pytest.mark.parametrize('time, exception', [
        (None, TypeError),
        (1, TypeError),
        ('a', TypeError),
        (True, TypeError),
        ({}, TypeError),
        ([], TypeError),
    ])
    def test_lock_time_exception(self, mocker, MongoThrottling, mocked_mongo, time, exception):
        robot_id = 'robot_01'
        _, collection = mocked_mongo

        result = {
            'time': datetime.datetime.fromisoformat('2020-02-03T04:05:06+09:00')
        }
        collection.find_one_and_update.return_value = result

        with pytest.raises(exception):
            MongoThrottling.lock(robot_id, time)


class TestMongoThrottlingGetMongoCollection:

    @freezegun.freeze_time('2020-03-04T05:06:07')
    def test_get_collection(self, mocker, MongoThrottling, mocked_mongo):
        MongoClient, collection = mocked_mongo

        c1 = MongoThrottling._get_mongo_collection()
        c2 = MongoThrottling._get_mongo_collection()

        assert id(collection) == id(c1)
        assert id(collection) == id(c2)
        assert MongoClient.call_count == 1
        assert MongoClient.call_args == call(const.MONGODB_HOST, int(const.MONGODB_PORT), replicaset=const.MONGODB_REPLICASET)
        assert collection.replace_one.call_count == 2
        assert collection.replace_one.call_args_list == [
            call({'robot_id': 'robot_01'},
                 {'robot_id': 'robot_01', 'time': datetime.datetime.fromisoformat('2020-03-04T05:06:07')},
                 upsert=True),
            call({'robot_id': 'robot_02'},
                 {'robot_id': 'robot_02', 'time': datetime.datetime.fromisoformat('2020-03-04T05:06:07')},
                 upsert=True),
        ]


class TestMongoThrottlingMsec:

    def test_throttling(self, MongoThrottling):
        assert MongoThrottling._throttling() == datetime.timedelta(milliseconds=const.NOTIFICATION_THROTTLING_MSEC)
