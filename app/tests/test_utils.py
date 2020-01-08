from src.utils import flatten

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
