import os

from src import const, orion
from src.utils import flatten

FIWARE_SERVICE = os.environ[const.FIWARE_SERVICE]
DELIVERY_ROBOT_SERVICEPATH = os.environ[const.DELIVERY_ROBOT_SERVICEPATH]


class Waypoint:
    def estimate_routes(self, shipment_list):
        print(f'shipment_list = {shipment_list}')

        destination = orion.query_entity(
            FIWARE_SERVICE,
            DELIVERY_ROBOT_SERVICEPATH,
            const.PLACE_TYPE,
            f'name=={shipment_list["destination"]["name"]}')['id']

        via_name_list = list(set([v['place'] for v in shipment_list['updated']]))
        via_list = [orion.query_entity(
            FIWARE_SERVICE,
            DELIVERY_ROBOT_SERVICEPATH,
            const.PLACE_TYPE,
            f'name=={v}')['id'] for v in via_name_list]
        via = const.VIA_SEPARATOR.join(sorted(via_list))

        routes = orion.query_entity(
            FIWARE_SERVICE,
            DELIVERY_ROBOT_SERVICEPATH,
            const.ROUTE_PLAN_TYPE,
            f'destination=={destination};via=={via}')['routes']['value']

        place_set = set(flatten([flatten(r.values()) for r in routes]))
        places = {place: orion.get_entity(
            FIWARE_SERVICE,
            DELIVERY_ROBOT_SERVICEPATH,
            const.PLACE_TYPE,
            place)['position']['value'] for place in place_set}

        waypoints_list = [{'to': r['to'], 'waypoints': [places[place_id] for place_id in r['via'] + [r['to']]]} for r in routes]
        return routes, waypoints_list
