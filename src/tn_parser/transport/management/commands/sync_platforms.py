# coding=utf8

import logging

from django.core.management.base import BaseCommand, CommandError

from ...models import RouteTypes
from ...sync import sync_platforms_from_2gis_api

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Parse, collect new and update existing platforms'

    def add_arguments(self, parser):
        parser.add_argument('api_key', nargs=1, type=str,
                            help='2GIS API key got from browser request,'
                                 ' expiring after a while')

    def handle(self, *args, **options):
        if not options['api_key']:
            self.stdout.write(
                'Sync bus routes platforms for bus ' +
                self.style.ERROR('Fail') +
                'api_key arg is not defined')

        key = options['api_key'][0] if isinstance(options['api_key'], (list, tuple)) else options['api_key']
        # bus routes
        stats = sync_platforms_from_2gis_api(key, RouteTypes.BUS)

        self.stdout.write(
            'Sync bus routes platforms for bus ' +
            self.style.SUCCESS('DONE'))

        # bus routes
        stats = sync_platforms_from_2gis_api(key, RouteTypes.TROLLEYBUS)

        self.stdout.write(
            'Sync bus routes platforms for bus ' +
            self.style.SUCCESS('DONE'))
