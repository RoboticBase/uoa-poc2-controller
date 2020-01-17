import datetime as dt

import importlib
from unittest.mock import call

import pytest
import lazy_import

const = lazy_import.lazy_module('src.const')


@pytest.fixture
def mocked_token(mocker):
    token = lazy_import.lazy_module('src.token')
    token.orion = mocker.MagicMock()
    yield token
    importlib.reload(token)


class TestInit:

    def test_init(self, mocked_token):
        tkn_str = 'token_a'
        token1 = mocked_token.Token(tkn_str)
        assert token1 is not None
        assert isinstance(token1, mocked_token.Token)
        assert token1._token == tkn_str
        assert token1._entity is None
        assert token1.is_locked is False
        assert token1.lock_owner_id == ''
        assert token1.prev_owner_id == ''
        assert token1.waitings == []
        assert tkn_str not in mocked_token.Token._tokens

        token2 = mocked_token.Token(tkn_str)
        assert token2 is not None
        assert isinstance(token2, mocked_token.Token)
        assert token2._token == tkn_str
        assert token2._entity is None
        assert token2.is_locked is False
        assert token2.lock_owner_id == ''
        assert token2.prev_owner_id == ''
        assert token2.waitings == []
        assert tkn_str not in mocked_token.Token._tokens

        tkn_str2 = 'token_b'
        token3 = mocked_token.Token(tkn_str2)
        assert token3 is not None
        assert isinstance(token3, mocked_token.Token)
        assert token3._token == tkn_str2
        assert token3._entity is None
        assert token3.is_locked is False
        assert token3.lock_owner_id == ''
        assert token3.prev_owner_id == ''
        assert token3.waitings == []
        assert tkn_str2 not in mocked_token.Token._tokens

        assert token1 != token2
        assert token1 != token3
        assert token2 != token3

        assert mocked_token.orion.get_entity.call_count == 0
        assert mocked_token.orion.make_token_info_command.call_count == 0
        assert mocked_token.orion.send_command.call_count == 0

    def test_get(self, mocked_token):
        tkn_str = 'token_a'
        token1 = mocked_token.Token.get(tkn_str)
        assert token1 is not None
        assert isinstance(token1, mocked_token.Token)
        assert token1._token == tkn_str
        assert token1._entity is None
        assert token1.is_locked is False
        assert token1.lock_owner_id == ''
        assert token1.prev_owner_id == ''
        assert token1.waitings == []
        assert tkn_str in mocked_token.Token._tokens
        assert mocked_token.Token._tokens[tkn_str] == token1

        token2 = mocked_token.Token.get(tkn_str)
        assert token2 is not None
        assert isinstance(token2, mocked_token.Token)
        assert token2._token == tkn_str
        assert token2._entity is None
        assert token2.is_locked is False
        assert token2.lock_owner_id == ''
        assert token2.prev_owner_id == ''
        assert token2.waitings == []
        assert tkn_str in mocked_token.Token._tokens
        assert mocked_token.Token._tokens[tkn_str] == token2

        tkn_str2 = 'token_b'
        token3 = mocked_token.Token.get(tkn_str2)
        assert token3 is not None
        assert isinstance(token3, mocked_token.Token)
        assert token3._token == tkn_str2
        assert token3._entity is None
        assert token3.is_locked is False
        assert token3.lock_owner_id == ''
        assert token3.prev_owner_id == ''
        assert token3.waitings == []
        assert tkn_str2 in mocked_token.Token._tokens
        assert mocked_token.Token._tokens[tkn_str2] == token3

        assert token1 == token2
        assert token1 != token3
        assert token2 != token3

        assert mocked_token.orion.get_entity.call_count == 0
        assert mocked_token.orion.make_token_info_command.call_count == 0
        assert mocked_token.orion.send_command.call_count == 0

    @pytest.mark.parametrize('tkn_str', [
        0, 1e-1, True, [], ['a', 1], {}, {'a': 1}, tuple(['a', 1]), set([1, 2]), dt.datetime.utcnow(), None
    ])
    def test_typeerror(self, mocked_token, tkn_str):

        with pytest.raises(TypeError) as e1:
            mocked_token.Token(tkn_str)

        assert str(e1.value) == 'token must be "str"'

        with pytest.raises(TypeError) as e2:
            mocked_token.Token.get(tkn_str)

        assert str(e2.value) == 'token must be "str"'
        assert mocked_token.orion.get_entity.call_count == 0
        assert mocked_token.orion.make_token_info_command.call_count == 0
        assert mocked_token.orion.send_command.call_count == 0


class TestGetLock:

    @pytest.mark.parametrize('loi, w, robot_id', [
        ('', [], 'robot_01'),
        ('', ['robot_01'], 'robot_01'),
        ('', ['robot_03'], 'robot_01'),
        ('robot_02', [], 'robot_01'),
        ('robot_02', ['robot_01'], 'robot_01'),
        ('robot_02', ['robot_03'], 'robot_01'),
    ])
    def test_isnot_locked(self, mocked_token, loi, w, robot_id):
        mocked_entity = {
            'is_locked': {
                'value': False,
            },
            'lock_owner_id': {
                'value': loi,
            },
            'waitings': {
                'value': w,
            },
        }
        mocked_token.orion.get_entity.return_value = mocked_entity

        mocked_payload = {
            'result': 'dummy',
        }
        mocked_token.orion.make_token_info_command.return_value = mocked_payload

        tkn_str = 'token_a'
        token = mocked_token.Token(tkn_str)
        result = token.get_lock(robot_id)

        assert result is True
        assert token._token == tkn_str
        assert token._entity == mocked_entity
        assert token.is_locked is True
        assert token.prev_owner_id == loi
        assert token.lock_owner_id == robot_id
        assert token.waitings == []

        assert mocked_token.orion.get_entity.call_count == 1
        assert mocked_token.orion.get_entity.call_args == call(
            const.FIWARE_SERVICE, const.TOKEN_SERVICEPATH, const.TOKEN_TYPE, tkn_str)

        assert mocked_token.orion.make_token_info_command.call_count == 1
        assert mocked_token.orion.make_token_info_command.call_args == call(True, robot_id, [])

        assert mocked_token.orion.send_command.call_count == 1
        assert mocked_token.orion.send_command.call_args == call(
            const.FIWARE_SERVICE, const.TOKEN_SERVICEPATH, const.TOKEN_TYPE, tkn_str, mocked_payload)

    @pytest.mark.parametrize('loi, poi, w, robot_id, update_waitings', [
        ('', None, [], 'robot_01', True),
        ('', 'robot_00', [], 'robot_01', True),
        ('', None, ['robot_01'], 'robot_01', False),
        ('', 'robot_00', ['robot_01'], 'robot_01', False),
        ('', None, ['robot_03'], 'robot_01', True),
        ('', 'robot_00', ['robot_03'], 'robot_01', True),
        ('robot_02', None, [], 'robot_01', True),
        ('robot_02', 'robot_00', [], 'robot_01', True),
        ('robot_02', None, ['robot_01'], 'robot_01', False),
        ('robot_02', 'robot_00', ['robot_01'], 'robot_01', False),
        ('robot_02', None, ['robot_03'], 'robot_01', True),
        ('robot_02', 'robot_00', ['robot_03'], 'robot_01', True),
    ])
    def test_is_locked(self, mocked_token, loi, poi, w, robot_id, update_waitings):
        mocked_entity = {
            'is_locked': {
                'value': True,
            },
            'lock_owner_id': {
                'value': loi,
            },
            'waitings': {
                'value': w,
            },
        }
        mocked_token.orion.get_entity.return_value = mocked_entity

        mocked_payload = {
            'result': 'dummy',
        }
        mocked_token.orion.make_token_info_command.return_value = mocked_payload

        tkn_str = 'token_a'
        token = mocked_token.Token(tkn_str)
        if poi is not None:
            token.prev_owner_id = poi
        result = token.get_lock(robot_id)

        assert result is False
        assert token._token == tkn_str
        assert token._entity == mocked_entity
        assert token.is_locked is True
        if update_waitings:
            assert token.prev_owner_id == '' if poi is None else poi
            assert token.lock_owner_id == loi
            assert token.waitings == w + [robot_id]

            assert mocked_token.orion.get_entity.call_count == 1
            assert mocked_token.orion.get_entity.call_args == call(
                const.FIWARE_SERVICE, const.TOKEN_SERVICEPATH, const.TOKEN_TYPE, tkn_str)

            assert mocked_token.orion.make_token_info_command.call_count == 1
            assert mocked_token.orion.make_token_info_command.call_args == call(True, loi, w + [robot_id])

            assert mocked_token.orion.send_command.call_count == 1
            assert mocked_token.orion.send_command.call_args == call(
                const.FIWARE_SERVICE, const.TOKEN_SERVICEPATH, const.TOKEN_TYPE, tkn_str, mocked_payload)
        else:
            assert token.prev_owner_id == '' if poi is None else poi
            assert token.lock_owner_id == loi
            assert token.waitings == w
            assert mocked_token.orion.get_entity.call_count == 1
            assert mocked_token.orion.get_entity.call_args == call(
                const.FIWARE_SERVICE, const.TOKEN_SERVICEPATH, const.TOKEN_TYPE, tkn_str)

            assert mocked_token.orion.make_token_info_command.call_count == 0

            assert mocked_token.orion.send_command.call_count == 0


class TestReleaseLock:

    @pytest.mark.parametrize('is_locked, loi', [
        (True, ''),
        (False, ''),
        (True, 'robot_02'),
        (False, 'robot_02'),
    ])
    def test_not_waitings(self, mocked_token, is_locked, loi):
        mocked_entity = {
            'is_locked': {
                'value': is_locked,
            },
            'lock_owner_id': {
                'value': loi,
            },
            'waitings': {
                'value': [],
            },
        }
        mocked_token.orion.get_entity.return_value = mocked_entity

        mocked_payload = {
            'result': 'dummy',
        }
        mocked_token.orion.make_token_info_command.return_value = mocked_payload

        tkn_str = 'token_a'
        robot_id = 'robot_01'
        token = mocked_token.Token(tkn_str)
        result = token.release_lock(robot_id)

        assert result is None
        assert token._token == tkn_str
        assert token._entity == mocked_entity
        assert token.is_locked is False
        assert token.prev_owner_id == loi
        assert token.lock_owner_id == ''
        assert token.waitings == []

        assert mocked_token.orion.get_entity.call_count == 1
        assert mocked_token.orion.get_entity.call_args == call(
            const.FIWARE_SERVICE, const.TOKEN_SERVICEPATH, const.TOKEN_TYPE, tkn_str)

        assert mocked_token.orion.make_token_info_command.call_count == 1
        assert mocked_token.orion.make_token_info_command.call_args == call(False, '', [])

        assert mocked_token.orion.send_command.call_count == 1
        assert mocked_token.orion.send_command.call_args == call(
            const.FIWARE_SERVICE, const.TOKEN_SERVICEPATH, const.TOKEN_TYPE, tkn_str, mocked_payload)

    @pytest.mark.parametrize('is_locked, loi, w, no, nw', [
        (True, '', ['robot_02'], 'robot_02', []),
        (False, '', ['robot_02'], 'robot_02', []),
        (True, 'robot_03', ['robot_02'], 'robot_02', []),
        (False, 'robot_03', ['robot_02'], 'robot_02', []),
        (True, '', ['robot_02', 'robot_04'], 'robot_02', ['robot_04']),
        (False, '', ['robot_02', 'robot_04'], 'robot_02', ['robot_04']),
        (True, 'robot_03', ['robot_02', 'robot_04'], 'robot_02', ['robot_04']),
        (False, 'robot_03', ['robot_02', 'robot_04'], 'robot_02', ['robot_04']),
    ])
    def test_waitings(self, mocked_token, is_locked, loi, w, no, nw):
        mocked_entity = {
            'is_locked': {
                'value': is_locked,
            },
            'lock_owner_id': {
                'value': loi,
            },
            'waitings': {
                'value': w,
            },
        }
        mocked_token.orion.get_entity.return_value = mocked_entity

        mocked_payload = {
            'result': 'dummy',
        }
        mocked_token.orion.make_token_info_command.return_value = mocked_payload

        tkn_str = 'token_a'
        robot_id = 'robot_01'
        token = mocked_token.Token(tkn_str)
        result = token.release_lock(robot_id)

        assert result == no
        assert token._token == tkn_str
        assert token._entity == mocked_entity
        assert token.is_locked is True
        assert token.prev_owner_id == loi
        assert token.lock_owner_id == no
        assert token.waitings == nw

        assert mocked_token.orion.get_entity.call_count == 1
        assert mocked_token.orion.get_entity.call_args == call(
            const.FIWARE_SERVICE, const.TOKEN_SERVICEPATH, const.TOKEN_TYPE, tkn_str)

        assert mocked_token.orion.make_token_info_command.call_count == 1
        assert mocked_token.orion.make_token_info_command.call_args == call(True, no, nw)

        assert mocked_token.orion.send_command.call_count == 1
        assert mocked_token.orion.send_command.call_args == call(
            const.FIWARE_SERVICE, const.TOKEN_SERVICEPATH, const.TOKEN_TYPE, tkn_str, mocked_payload)
