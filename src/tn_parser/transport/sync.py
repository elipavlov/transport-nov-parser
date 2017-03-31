# coding=utf-8

import logging

import datetime
from collections import defaultdict
from copy import copy

import requests

from .models import Route, DataProviderUrl,\
    DataProviderTypes as p_types, RouteTypes, Point, Platform, Directions, RoutePoint, RouteWeekDimension, GeoDirections

logger = logging.getLogger(__name__)


def _adds_count_of_sets_to_dict(datadict):
    res = dict()

    for key, val in dict(**datadict).items():
        res.update({'%s_count' % key: len(val)})
    res.update(datadict)
    return res


def get_routes_raw_data():
    try:
        data_provider = DataProviderUrl.objects.get(
            type=p_types.ROUTES_HTML_PAGE)

        resp = requests.get(data_provider.link)
        return resp.content.decode(data_provider.coding)
    except DataProviderUrl.DoesNotExist:
        logger.error(
            'No data providers found for Routes HTML page type of data')
        return ''


def process_parsed_routes(routes, transport_type):
    parsed = set([route['code'].split('_')[0] for route in routes])
    exists = set(Route.objects
                 .filter(type=transport_type)
                 .values_list('code', flat=True)
                 .order_by('code'))

    diff = parsed - exists

    batch = []
    for route_dict in routes:
        route = dict(**route_dict)
        route.update({
            'code': route['code'].split('_')[0],
            'type': transport_type,
        })
        if route['code'] in diff:
            batch.append(Route(**route))

    if len(batch):
        Route.objects.bulk_create(batch)

    return _adds_count_of_sets_to_dict({
        'added': diff,
        'updated': parsed - diff,
        'exists': exists,
    })


def get_2gis_data(api_key, route):
    """
    return None or route data got from 2gis API

    :param api_key: key for connecting to API
    :type str
    :param route: route model for using to look up
    data provider in DB
    :type route: .models.Route
    :return: json dict from api | None
    :rtype: dict|None
    """
    data_provider = None
    try:
        data_provider = route.data_providers.get(
            type=p_types.TWOGIS_ROUTE_API)
    except DataProviderUrl.DoesNotExist:
        pass

    try:
        data_provider = DataProviderUrl.objects.get(
            route_code=route.code,
            type=p_types.TWOGIS_ROUTE_API)

        data_provider.route = route
        data_provider.save()
    except DataProviderUrl.DoesNotExist:
        pass

    if not data_provider:
        logger.error(
            'No data providers found for route: {}'.format(route.name))
        return None
    else:
        resp = requests.get('{}&key={}'.format(data_provider.link, api_key))
        return resp.json()


def process_route_platforms_with_2gis(api_key, route):
    json = get_2gis_data(api_key, route)
    if json:
        week_dim, _ = RouteWeekDimension.objects.get_or_create(
            weekend=False,
            weekday=1)

        dir_ind = 'undefined'
        stats = {
            'created': 0,
            'updated': 0,
        }
        platforms = {
            'new': [],
            'exists': [],
            'common': [],
        }
        directions = {
            Directions.FORWARD: defaultdict(list),
            Directions.BACKWARD: defaultdict(list),
            Directions.CIRCULAR: defaultdict(list),
        }
        for direction in json['result']['items'][0]['directions']:
            if direction['type'] == 'backward':
                dir_ind = Directions.BACKWARD
            elif direction['type'] == 'forward':
                dir_ind = Directions.FORWARD
            elif direction['type'] == 'circular':
                dir_ind = Directions.CIRCULAR

            for platform in direction['platforms']:
                pnt = Point(repr=platform['geometry']['centroid'])
                try:
                    exists = Platform.objects.get(
                        name=platform['name'],
                        longitude=pnt.lon,
                        latitude=pnt.lat)

                    directions[dir_ind]['exists'].append(exists)
                    directions[dir_ind]['common'].append(exists)
                    platforms['exists'].append(exists)
                    platforms['common'].append(exists)
                except Platform.DoesNotExist:
                    new_platform = Platform(
                        name=platform['name'],
                        longitude=pnt.lon,
                        latitude=pnt.lat)
                    try:
                        # logger.warn('Find platform before create')
                        # index = directions[dir_ind]['new'].index(new_platform)
                        index = platforms['common'].index(new_platform)
                        # logger.warn('This platform already in batch to create')
                        directions[dir_ind]['common'].append(
                            platforms['common'][index])
                    except ValueError:
                        directions[dir_ind]['new'].append(new_platform)
                        directions[dir_ind]['common'].append(new_platform)
                        platforms['new'].append(new_platform)
                        platforms['common'].append(new_platform)

        # creating route points
        order = 0
        last = None
        time = datetime.time(0, 0, 0, 0)
        for key, batch in directions.items():
            # platforms['created'] += len(batch['new'])
            logger.warn('Route: %s \tDirection: %s\t batch: %s'
                        % (route.name, key, len(batch['common'])))
            for platform in batch['common']:
                if not platform.pk:
                    platform.save()

                if last:
                    last_pnt = Point(
                        lon=last.platform.longitude,
                        lat=last.platform.latitude)
                    pnt = Point(
                        lon=platform.longitude,
                        lat=platform.latitude)
                    angle = pnt.angle(last_pnt)
                    angle += last.angle
                    angle = GeoDirections._normalize_angle(angle)
                else:
                    angle = 0

                geo_direction = GeoDirections.from_angle(angle)

                if order > 0:
                    time_delta = (pnt - last_pnt).length * 10000
                    # logger.debug('Timedelta : %s' % time_delta)
                    dt = datetime.datetime\
                        .combine(datetime.datetime.today(), time)\
                        + datetime.timedelta(0, int(time_delta))
                    time = dt.time()

                last, _ = RoutePoint.objects.update_or_create(
                    route=route,
                    platform=platform,
                    week_dimension=week_dim,
                    lap=0,
                    order=order,
                    defaults={
                        'time': time,
                        'lap_start': order <= 0,
                        'direction': key,
                        'geo_direction': geo_direction,
                        'angle': angle,
                        'on_demand': platform.name.lower().find(u'по требованию')>=0
                    }
                )

                if _:
                    stats['created'] += 1
                else:
                    stats['updated'] += 1

                status = 'created' if _ else 'updated'
                # logger.info('Order %s, %s, route: %s, platforms: %s, angle %s'
                #             % (order, status, route.name, platform.name, angle,))
                order += 1

        logger.info('route: %s,\t created: %s,\t updated: %s,\t'
                    'platforms: new: %s,\t exists: %s'
                    % (route.name, stats['created'], stats['updated'],
                       len(platforms['new']), len(platforms['exists'])))
        # print(stats)
        return stats
    else:
        return None


def process_routes_with_2gis(api_key, routes):
    stats = []
    for route in routes:
        stats.append(process_route_platforms_with_2gis(api_key, route))

    return stats


def sync_platforms_from_2gis_api(api_key, type=None):
    # process bus platforms at first
    if not type:
        type = RouteTypes.BUS
    routes = Route.objects.filter(type=type)

    return process_routes_with_2gis(api_key, routes=routes)


