# coding=utf8

import logging
import re

import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand, CommandError
from ...helpers import parse_rus_date_to_naive_date

from tn_parser.transport.models import RouteTypes, Route
# from tn_parser.transport.parsers import \
#     get_bus_routes_from_page, get_trolleybus_routes_from_page
# from tn_parser.transport.sync import get_routes_raw_data, process_parsed_routes


logger = logging.getLogger(__name__)

_URL_MASK = 'http://transport.nov.ru/urban_trans/1/?mar={}'


class Command(BaseCommand):
    help = 'Parse, collect new and update existing routes'

    def handle(self, *args, **options):
        # raw_data = get_routes_raw_data()
        for route in Route.objects.filter(type=RouteTypes.BUS):
            resp = requests.get(_URL_MASK.format('{}{}'.format(route.code, '_r')))

            # raw_data = resp.content.decode(resp.apparent_encoding)
            # to avoid htmlDom parse errors
            raw_data = resp.content.decode(resp.apparent_encoding).encode('utf-8').decode()

            soup = BeautifulSoup(raw_data, 'html.parser')

            # First table contains switcher for weekday/weekend/certain day.
            # It's would be using for determine schedule day
            ttop = soup.find('table', class_='top')
            tnav = ttop.find('table', align='center')
            a_tags = tnav.find_all('a')

            # days of week
            days = []
            for a in a_tags:
                if '_r' in a['href']:
                    days.append(1)

                elif '_v' in a['href']:
                    if 6 in days:
                        days.append(7)
                    else:
                        days.append(6)

                elif '_s' in a['href']:
                    days.append(6)

            # Schedule days
            tr_tags = ttop.find_all('tr', limit=5)
            for tag in tr_tags:
                td = tag.find('td', align='center')
                if td and 'по состоянию' in td.text:
                    font = td.find('font')

            last_update = None
            if font:
                last_update = parse_rus_date_to_naive_date(font.text)

            # Schedule itself
            # Here determines each row of schedule
            tt = soup.find('table', class_='t')

            # The first row, it is the columns' headers,
            # which will use to determine bus stop order for correct mapping
            td_tags = tt.tr.find_all('td', recursive=False)
            for td in td_tags:
                print(td.text)

            # for each row determine row cell's values
            for row in tt.find_all('tr', recursive=False)[1:]:
                td_tags = row.find_all('td', recursive=False)
                # schedule_time = r4.findall(row)
                print('\t'.join([td.text for td in td_tags]))
                #print(td.text)
                print('\n')

            print(route)

            break