# coding=utf8

import logging

from django.core.management.base import BaseCommand, CommandError

from tn_parser.transport.models import RouteTypes
from tn_parser.transport.parsers import \
    get_bus_routes_from_page, get_trolleybus_routes_from_page
from ...sync import get_routes_raw_data, process_parsed_routes

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Parse, collect new and update existing routes'

    def handle(self, *args, **options):
        raw_data = get_routes_raw_data()

        # bus routes
        routes = get_bus_routes_from_page(raw_data)
        stats = process_parsed_routes(routes, RouteTypes.BUS)

        if 'verbosity' in options.keys() and options['verbosity'] > 1:
            print('Bus routes:')
            for rt in routes:
                print(rt)

        self.stdout.write(
            'Sync bus routes ' +
            self.style.SUCCESS('DONE'))
        self.stdout.write(
            '\tadded: {added_count}\n'
            '\tupdated: {updated_count}\n'
            '\texists: {exists_count}\n'
            '\tcanceled: {canceled_count}\n'
            '\tcanceled total: {canceled_total_count}\n'.format(**stats),
        )

        # trolleybus routes
        routes = get_trolleybus_routes_from_page(raw_data)
        stats = process_parsed_routes(routes, RouteTypes.TROLLEYBUS)

        if 'verbosity' in options.keys() and options['verbosity'] > 1:
            print('Trolleybus routes:')
            for rt in routes:
                print(rt)

        self.stdout.write(
            'Sync trolleybus routes ' +
            self.style.SUCCESS('DONE'))
        self.stdout.write(
            '\tadded: {added_count}\n'
            '\tupdated: {updated_count}\n'
            '\texists: {exists_count}\n'
            '\tcanceled: {canceled_count}\n'
            '\tcanceled total: {canceled_total_count}\n'.format(**stats),
        )
