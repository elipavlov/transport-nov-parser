# coding=utf8

import logging

import requests

from django.core.management.base import BaseCommand, CommandError

from tn_parser.transport.models import Route, \
    DataProviderUrl, DataProviderTypes as ptypes, RouteTypes
from tn_parser.transport.parsers import \
    get_bus_routes_from_page, get_trolleybus_routes_from_page

logger = logging.getLogger(__name__)


def adds_count_of_sets_to_dict(datadict):
    res = dict()

    for key, val in dict(**datadict).items():
        res.update({'%s_count' % key: len(val)})
    res.update(datadict)
    return res


class Command(BaseCommand):
    help = 'Parse, collect new and update exists routes'

    # def add_arguments(self, parser):
    #     parser.add_argument('poll_id', nargs='+', type=int)

    @classmethod
    def _process_parsed_routes(cls, routes, type):
        parsed = set([route['code'].split('_')[0] for route in routes])
        exists = set(Route.objects
                     .filter(type=type)
                     .values_list('code', flat=True)
                     .order_by('code'))

        diff = parsed - exists

        batch = []
        for route_dict in routes:
            route = dict(**route_dict)
            route.update({
                'code': route['code'].split('_')[0],
                'type': type,
            })
            if route['code'] in diff:
                batch.append(Route(**route))

        # import ipdb; ipdb.set_trace()
        if len(batch):
            Route.objects.bulk_create(batch)

        return adds_count_of_sets_to_dict({
            'added': diff,
            'updated': parsed - diff,
            'exists': exists,
        })

    def handle(self, *args, **options):
        data_prvd = DataProviderUrl.objects.get(type=ptypes.ROUTES_HTML_PAGE)

        resp = requests.get(data_prvd.link)
        resp = resp.content.decode(data_prvd.coding)

        # bus routes
        routes = get_bus_routes_from_page(resp)

        stats = self._process_parsed_routes(routes, RouteTypes.BUS)

        self.stdout.write(
            'Sync bus routes finished ' +
            self.style.SUCCESS('successfully'))
        self.stdout.write(
            '\tadded: {added_count}\n'
            '\tupdated: {updated_count}\n'
            '\texists: {exists_count}\n'.format(**stats),
        )

        # trolleybus routes
        routes = get_trolleybus_routes_from_page(resp)

        stats = self._process_parsed_routes(routes, RouteTypes.TROLLEYBUS)

        self.stdout.write(
            'Sync trolleybus routes finished ' +
            self.style.SUCCESS('successfully'))
        self.stdout.write(
            '\tadded: {added_count}\n'
            '\tupdated: {updated_count}\n'
            '\texists: {exists_count}\n'.format(**stats),
        )
