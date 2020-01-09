import datetime

from src.utils import flatten, is_jsonable

import pytest


class TestFlatten:

    @pytest.mark.parametrize('target, expected', [
        ([], []),
        ([1], [1]),
        ([1, 2], [1, 2]),
        ([1, [2]], [1, 2]),
        ([[1], [2], []], [1, 2]),
        ([[[[4]], [3]], [[2]], [1], 0], [4, 3, 2, 1, 0]),
        (tuple(), []),
        (((((3,)), (2,), 1)), [3, 2, 1]),
    ])
    def test_success(self, target, expected):
        assert flatten(target) == expected

    @pytest.mark.parametrize('target, expected', [
        ('a', ['a']),
        ('abcde', ['a', 'b', 'c', 'd', 'e']),
        ([['abc'], 'def'], ['abc', 'def']),
    ])
    def test_str(self, target, expected):
        assert flatten(target) == expected

    @pytest.mark.parametrize('target, expected', [
        ({}, []),
        ({'a': 'A', 'b': 'B'}, ['a', 'b']),
        ({'a': 'A', 'b': {'c': {'d': 'D'}}}, ['a', 'b']),
        ([{'a': 'A', 'b': None}, {'c': 'C', 'd': True}], ['a', 'b', 'c', 'd']),
        (set(), []),
        (set((((3,)), (2,), 1)), [1, 2, 3]),
    ])
    def test_dict_set(self, target, expected):
        assert sorted(flatten(target)) == expected

    @pytest.mark.parametrize('target, expected', [
        (None, TypeError),
        (1, TypeError),
        (True, TypeError),
    ])
    def test_exception(self, target, expected):
        with pytest.raises(expected):
            flatten(target)


class TestIsJsonable:

    @pytest.mark.parametrize('target, expected', [
        ({'test': 'dummy', 'None': None}, True),
        ({'test': {'nested': [1, 2.0, '3']}}, True),
        ({}, True),
        ([1, 1.2e-2, 'a', True, {'a': 'b'}, None], True),
        ([], True),
        ('dummy', True),
        (1, True),
        (0.5, True),
        (False, True),
        (tuple([1, 2]), True),
        (None, True),
        (datetime.datetime.utcnow(), False),
        (set([1, 2, 1]), False),
    ])
    def test_is_jsonable(self, target, expected):
        assert is_jsonable(target) == expected
