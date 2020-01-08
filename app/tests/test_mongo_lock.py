import datetime
import importlib
from unittest.mock import call

import pytest
import freezegun
import lazy_import
mongo_lock = lazy_import.lazy_module('src.mongo_lock')


@pytest.fixture
def MongoThrottling():
    yield mongo_lock.MongoThrottling
    importlib.reload(mongo_lock)


@pytest.fixture
def MongoClient(mocker):
    mongo_lock.MongoClient = mocker.MagicMock()
    yield mongo_lock.MongoClient


@pytest.mark.usefixtures('setup_environments')
class TestMongoThrottlingLock:

    def _prepare(self, mocker, const, MongoClient):
        robot_id = 'robot_01'
        time = datetime.datetime.fromisoformat('2020-01-02T03:04:05+09:00')
        collection = mocker.MagicMock()
        MongoClient.return_value = {
            const.MONGODB_DB_NAME: {
                const.MONGODB_COLLECTION_NAME: collection
            }
        }
        return robot_id, time, collection.find_one_and_update

    def test_lock_success(self, mocker, const, MongoThrottling, MongoClient):
        robot_id, time, find_one_and_update = self._prepare(mocker, const, MongoClient)
        result = {
            'time': datetime.datetime.fromisoformat('2020-02-03T04:05:06+09:00')
        }
        find_one_and_update.return_value = result

        lock = MongoThrottling.lock(robot_id, time)

        assert MongoClient.call_count == 1
        assert MongoClient.call_args == call(const.MONGODB_HOST, int(const.MONGODB_PORT), replicaset=const.MONGODB_REPLICASET)
        assert find_one_and_update.call_count == 1
        assert find_one_and_update.call_args == call(
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

    def test_lock_error(self, mocker, const, MongoThrottling, MongoClient):
        robot_id, time, find_one_and_update = self._prepare(mocker, const, MongoClient)
        find_one_and_update.return_value = None

        with pytest.raises(mongo_lock.MongoLockError) as e:
            MongoThrottling.lock(robot_id, time)

        assert MongoClient.call_count == 1
        assert MongoClient.call_args == call(const.MONGODB_HOST, int(const.MONGODB_PORT), replicaset=const.MONGODB_REPLICASET)
        assert find_one_and_update.call_count == 1
        assert find_one_and_update.call_args == call(
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
    def test_lock_robotid_exception(self, mocker, const, MongoThrottling, MongoClient, robot_id, exception):
        _, time, find_one_and_update = self._prepare(mocker, const, MongoClient)

        result = {
            'time': datetime.datetime.fromisoformat('2020-02-03T04:05:06+09:00')
        }
        find_one_and_update.return_value = result

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
    def test_lock_time_exception(self, mocker, const, MongoThrottling, MongoClient, time, exception):
        robot_id, _, find_one_and_update = self._prepare(mocker, const, MongoClient)

        result = {
            'time': datetime.datetime.fromisoformat('2020-02-03T04:05:06+09:00')
        }
        find_one_and_update.return_value = result

        with pytest.raises(exception):
            MongoThrottling.lock(robot_id, time)


@pytest.mark.usefixtures('setup_environments')
class TestMongoThrottlingGetMongoCollection:

    def _prepare(self, mocker, const, MongoClient):
        collection = mocker.MagicMock()
        MongoClient.return_value = {
            const.MONGODB_DB_NAME: {
                const.MONGODB_COLLECTION_NAME: collection
            }
        }
        return collection

    @freezegun.freeze_time('2020-03-04T05:06:07')
    def test_get_collection(self, mocker, const, MongoThrottling, MongoClient):
        collection = self._prepare(mocker, const, MongoClient)

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


@pytest.mark.usefixtures('setup_environments')
class TestMongoThrottlingMsec:

    def test_throttling(self, const, MongoThrottling):
        assert MongoThrottling._throttling() == datetime.timedelta(milliseconds=const.NOTIFICATION_THROTTLING_MSEC)
