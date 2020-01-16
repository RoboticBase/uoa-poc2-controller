import pytest
import lazy_import
caller = lazy_import.lazy_module('src.caller')


class TestCaller:

    def test_str(self):
        assert str(caller.Caller.ORDERING) == 'ordering'
        assert str(caller.Caller.WAREHOUSE) == 'warehouse'

    @pytest.mark.parametrize('shipment_list', [
        ({'caller': 'zaico-extensions'}),
    ])
    def test_get_ordering(self, shipment_list):
        assert caller.Caller.get(shipment_list) == caller.Caller.ORDERING

    @pytest.mark.parametrize('shipment_list', [
        ({'x': 'Y'}, 'warehouse'),
        ({'caller': 'dummy'}, 'warehouse'),
        ({}, 'warehouse'),
        ([], 'warehouse'),
        (None, 'warehouse'),
        (1, 'warehouse'),
        ('a', 'warehouse'),
        ('abc', 'warehouse'),
        (True, 'warehouse'),
    ])
    def test_get_warehouse(self, shipment_list):
        assert caller.Caller.get(shipment_list) == caller.Caller.WAREHOUSE

    def test_value_of(self):
        assert caller.Caller.value_of('ordering') == caller.Caller.ORDERING
        assert caller.Caller.value_of('warehouse') == caller.Caller.WAREHOUSE
        with pytest.raises(ValueError) as e:
            caller.Caller.value_of('abc')
        assert str(e.value) == 'abc is not a Caller'
