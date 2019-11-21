from enum import Enum

from src import const


class Caller(Enum):
    ORDERING = 'ordering'
    WAREHOUSE = 'warehouse'

    @classmethod
    def get(cls, shipment_list):
        if 'caller' in shipment_list and shipment_list['caller'] in const.ORDERING_LIST:
            return Caller.ORDERING
        else:
            return Caller.WAREHOUSE

    @classmethod
    def value_of(cls, v):
        for e in Caller:
            if e.value == v:
                return e
        raise ValueError(f'{v} is not a Caller')

    def __str__(self):
        return self.value
