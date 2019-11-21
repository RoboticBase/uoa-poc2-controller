from logging import getLogger

from src import const, orion
from src.utils import flatten

logger = getLogger(__name__)


class Waypoint:
    def estimate_routes(self, shipment_list, robot_id):
        logger.info(f'shipment_list = {shipment_list}')

        destination = orion.query_entity(
            const.FIWARE_SERVICE,
            const.DELIVERY_ROBOT_SERVICEPATH,
            const.PLACE_TYPE,
            f'name=={shipment_list["destination"]["name"]}')['id']

        via_name_list = list(set([v['place'] for v in shipment_list['updated']]))
        via_list = [orion.query_entity(
            const.FIWARE_SERVICE,
            const.DELIVERY_ROBOT_SERVICEPATH,
            const.PLACE_TYPE,
            f'name=={v}')['id'] for v in via_name_list]
        via = const.VIA_SEPARATOR.join(sorted(via_list))

        route_plan = orion.query_entity(
            const.FIWARE_SERVICE,
            const.DELIVERY_ROBOT_SERVICEPATH,
            const.ROUTE_PLAN_TYPE,
            f'destination=={destination};via=={via};robot_id=={robot_id}')
        routes = route_plan['routes']['value']
        source = route_plan['source']['value']

        places = self.get_places([flatten([r['from'], r['via'], r['to'], r['destination']]) for r in routes])

        waypoints_list = []
        for route in routes:
            waypoints = self.get_waypoints([places[place_id] for place_id in route['via']], [places[route['to']]])
            waypoints_list.append({
                'to': route['to'],
                'destination': route['destination'],
                'action': route['action'],
                'waypoints': waypoints,
            })

        order = {
            'source': source,
            'via': via_list,
            'destination': destination,
        }

        return routes, waypoints_list, order

    def get_places(self, place_id_list):
        place_set = set(flatten(place_id_list))
        places = {place: orion.get_entity(
            const.FIWARE_SERVICE,
            const.DELIVERY_ROBOT_SERVICEPATH,
            const.PLACE_TYPE,
            place)['pose']['value'] for place in place_set}
        return places

    def get_waypoints(self, via_list, to_list):
        via = [{
            'point': p['point'],
            'angle': None,
        } for p in via_list]

        to = [{
            'point': p['point'],
            'angle': p['angle'],
        } for p in to_list]

        return via + to
