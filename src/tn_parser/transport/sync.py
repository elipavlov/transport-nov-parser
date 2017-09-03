# coding=utf-8

import logging

import datetime
import re
from collections import defaultdict, OrderedDict
from copy import copy

import requests

from .models import Route, DataProviderUrl,\
    DataProviderTypes as p_types, RouteTypes, Point, Platform, Directions, RoutePoint, RouteWeekDimension, GeoDirections, \
    PlatformAlias, Stop

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
                 .values_list('code', flat=True))

    diff = parsed - exists
    canceled_now = exists - parsed

    canceled_already = set(Route.objects
        .filter(type=transport_type)
        .exclude(canceled=None)
        .values_list('code', flat=True))

    create_batch = []
    for route_dict in routes:
        route = dict(**route_dict)
        route.update({
            'code': route['code'].split('_')[0],
            'type': transport_type,
        })
        if route['code'] in diff:
            create_batch.append(Route(**route))

    canceled = [route_code
                for route_code in canceled_now
                if route_code not in canceled_already]

    if canceled:
        Route.objects.filter(code__in=canceled)\
            .update(canceled=datetime.datetime.now().date())

    if len(create_batch):
        Route.objects.bulk_create(create_batch)

    return _adds_count_of_sets_to_dict({
        'added': diff,
        'updated': parsed - diff,
        'exists': exists,
        'canceled': canceled,
        'canceled_total': canceled_already,
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


def _find_platform(name, to_create_list):
    """
    get or create platform

    :param name: look up name
    :type:  str | unicode
    :param to_create_list: list of created but not wrote instances
    :type:  list
    :return: (platform, alias, created)
    :rtype: tuple
    """
    alias = None
    alias_list = None
    created = False
    platform = None

    for pl in to_create_list:
        if pl.name == name:
            platform = pl
            # created = True
            break
    else:
        try:
            platform = Platform.objects.get(name=name)
        except Platform.DoesNotExist:
            alias_list = PlatformAlias.objects.filter(name=name)

    if not platform:
        if alias_list and len(alias_list):
            alias = alias_list[0]

        if alias:
            platform = alias.platform
        else:
            platform = Platform(name=name)
            created = True

    return platform, alias, created


def _find_stop(platform, point, to_create_list, alias=None):
    """
    get or create Stop

    :param platform:
    :type platform: Platform
    :param point: GEO point
    :type point: Point
    :param to_create_list: list of created but not wrote instances
    :type to_create_list: list
    :param alias:
    :type alias: PlatformAlias
    :return: return tuple(Stop, created)
    :rtype: tuple
    """
    # Platform
    create = False

    stop = Stop(
        platform=platform,
        longitude=point.lon,
        latitude=point.lat,
        alias=alias
    )

    for st in to_create_list:
        if st == stop:
            stop = st
            break
    else:
        try:
            stop = Stop.objects.get(
                longitude=point.lon,
                latitude=point.lat)
        except Stop.DoesNotExist:
            create = True

    if alias:
        stop.alias = alias

    return stop, create


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
        stops = {
            'new': [],
            'exists': [],
            'common': [],
        }
        directions = {
            Directions.FORWARD: defaultdict(list),
            Directions.BACKWARD: defaultdict(list),
            Directions.CIRCULAR: defaultdict(list),
        }

        try:
            received_directions = json['result']['items'][0]['directions']
        except KeyError:
            raise ValueError('Wrong API response: {}'.format(json))

        order_matters = sorted(
            received_directions,
            key=lambda direction: direction['type'], reverse=False)

        for direction in order_matters:
            logger.info('Start from: {}'.format(direction['type']))
            if direction['type'] == 'forward':
                dir_ind = Directions.FORWARD
            elif direction['type'] == 'backward':
                dir_ind = Directions.BACKWARD
            elif direction['type'] == 'circular':
                dir_ind = Directions.CIRCULAR
            else:
                # TODO implement additional type: weekend meaning
                logger.warning('Skip this direction: {}'.format(direction['type']))
                continue

            for r_stop in direction['platforms']:
                pnt = Point(repr=r_stop['geometry']['centroid'])

                # find platform
                platform, alias, platform_crtd = _find_platform(r_stop['name'], platforms['new'])
                stop, stop_crt = _find_stop(platform, pnt, stops['new'], alias)

                if platform_crtd:
                    platforms['new'].append(platform)
                else:
                    platforms['exists'].append(platform)
                platforms['common'].append(platform)

                if stop_crt:
                    stops['new'].append(stop)
                    directions[dir_ind]['exists'].append(stop)
                else:
                    stops['exists'].append(stop)
                    # directions[dir_ind]['common'].append(stop)
                directions[dir_ind]['common'].append(stop)
                stops['common'].append(stop)

        logger.info('Route: %s \t platforms: %s'
                    % (route.name, len(platforms['common'])))
        for platform in platforms['new']:
            platform.save()

        # creating route points
        order = 0
        last = None
        time = datetime.time(0, 0, 0, 0)
        for key, batch in directions.items():
            logger.info('Route: %s \tDirection: %s\t stops: %s'
                        % (route.name, key, len(batch['common'])))
            for stop in batch['common']:
                if not stop.pk:
                    stop.platform = stop.platform
                    stop.save()

                # calculate angel between prev and current stop
                pnt = Point(
                    lon=stop.longitude,
                    lat=stop.latitude)
                if last:
                    last_pnt = Point(
                        lon=last.stop.longitude,
                        lat=last.stop.latitude)
                    angle = pnt.angle(last_pnt)
                    angle += last.angle
                    angle = GeoDirections.normalize_angle(angle)
                else:
                    last_pnt = Point(0, 0)
                    angle = 0

                geo_direction = GeoDirections.from_angle(angle)

                if order > 0:
                    time_delta = (pnt - last_pnt).length * 10000
                    # logger.debug('Timedelta : %s' % time_delta)
                    dt = datetime.datetime\
                        .combine(datetime.datetime.today(), time)\
                        + datetime.timedelta(0, int(time_delta))
                    time = dt.time()

                last, last_crtd = RoutePoint.objects.update_or_create(
                    route=route,
                    stop=stop,
                    week_dimension=week_dim,
                    lap=0,
                    order=order,
                    defaults={
                        'time': time,
                        'lap_start': order <= 0,
                        'direction': key,
                        'geo_direction': geo_direction,
                        'angle': angle,
                        'on_demand': stop.platform.name.lower().find(u'по требованию')>=0
                    }
                )

                if last_crtd:
                    stats['created'] += 1
                else:
                    stats['updated'] += 1

                # status = 'created' if last_crtd else 'updated'
                # # logger.info('Order %s, %s, route: %s, platforms: %s, angle %s'
                # #             % (order, status, route.name, platform.name, angle,))
                order += 1

        logger.info('Route: %s,\t created: %s,\t updated: %s,\t'
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


def sync_platforms_from_2gis_api(api_key, type):
    routes = Route.objects.filter(type=type)

    return process_routes_with_2gis(api_key, routes=routes)


def process_platform_input(raw_platform):
    _map = {'отпр': 'start', 'приб': 'finish'}
    extreme = None
    for k, v in _map.items():
        if k in raw_platform:
            raw_platform = raw_platform.replace('{}.'.format(k), '')
            raw_platform = raw_platform.replace(k, '')
            extreme = v
            break

    aliase = None
    _subaliase = re.compile('\((.+?)\)')
    res = _subaliase.search(raw_platform)
    if res:
        aliase = res.group(1)
        raw_platform = raw_platform.replace('({})'.format(aliase), '')

    raw_pltfs = [raw_platform]
    if aliase:
        raw_pltfs.append(aliase)

    _platform_prefix = ('ул', 'п', 'пл', 'пер', 'пр')

    pltfs = []
    for pltf in raw_pltfs:
        parts = pltf.strip().split(' ')
        platform = []
        # clear raw
        for part in parts:
            skip = False
            for w in _platform_prefix:
                if part.lower() == w or part.lower() == '{}.'.format(w):
                    skip = True
                    break

            if not skip:
                platform.append(part)

        pltf = ' '.join(platform).strip()
        parts = pltf.strip().split('.')
        platform = []
        # clear raw
        for part in parts:
            skip = False
            for w in _platform_prefix:
                if part.lower() == w:
                    skip = True
                    break

            if not skip:
                platform.append(part)

        pltfs.append('.'.join(platform).strip())

    return pltfs, extreme

