# coding=utf8

import logging

from django.core.management.base import BaseCommand, CommandError

from tn_parser.transport.models import RouteTypes
from tn_parser.transport.sync import sync_platforms_from_2gis_api

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Parse, collect new and update existing platforms'

    def handle(self, *args, **options):
        # bus routes
        stats = sync_platforms_from_2gis_api()

        self.stdout.write(
            'Sync bus routes platforms for bus ' +
            self.style.SUCCESS('DONE'))

        # bus routes
        stats = sync_platforms_from_2gis_api(RouteTypes.TROLLEYBUS)

        self.stdout.write(
            'Sync bus routes platforms for bus ' +
            self.style.SUCCESS('DONE'))
