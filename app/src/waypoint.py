import os

from src import const, orion

FIWARE_SERVICE = os.environ[const.FIWARE_SERVICE]
DELIVERY_ROBOT_SERVICEPATH = os.environ[const.DELIVERY_ROBOT_SERVICEPATH]


class Waypoint:
    def get_routes(self, shipment_list):
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

        route_plan = orion.query_entity(
            FIWARE_SERVICE,
            DELIVERY_ROBOT_SERVICEPATH,
            const.ROUTE_PLAN_TYPE,
            f'destination=={destination};via=={via}')
        print(f'route_plan = {route_plan}')

        return route_plan['routes']['value']
