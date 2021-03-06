from logging import getLogger

from src import const, orion
from src.utils import flatten

logger = getLogger(__name__)


class Waypoint:
    def estimate_routes(self, shipment_list, robot_id):
        if not ('destination' in shipment_list and 'name' in shipment_list['destination']
                and isinstance(shipment_list['destination']['name'], str)
                and 'updated' in shipment_list and isinstance(shipment_list['updated'], list)
                and all('place' in v for v in shipment_list['updated'])
                and all(isinstance(v['place'], str) for v in shipment_list['updated'])):
            raise TypeError('invalid shipment_list')
        if not isinstance(robot_id, str):
            raise TypeError('invalid robot_id')

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
            f'name=={v}')['id'] for v in sorted(via_name_list)]
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
        raw_places = {place['id']: place for place in orion.get_entities(
            const.FIWARE_SERVICE,
            const.DELIVERY_ROBOT_SERVICEPATH,
            const.PLACE_TYPE)}

        places = {place: raw_places[place]['pose']['value'] for place in place_set}
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
