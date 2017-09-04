# coding=utf8

import logging
import re

import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand, CommandError

from tn_parser.transport.sync import process_platform_input
from ...helpers import parse_rus_date_to_naive_date

from tn_parser.transport.models import RouteTypes, Route, RoutePoint, Stop

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
                    if 6 in days:
                        days.insert(6)
                    else:
                        days.append(6)

            print('days: {}'.format(days))

            # Schedule days
            tr_tags = ttop.find_all('tr', limit=5)
            on_date = None
            for tag in tr_tags:
                td = tag.find('td', align='center')
                if td and 'по состоянию' in td.text:
                    on_date = td.find('font')

            # calc on_date date
            last_update = None
            if on_date:
                last_update = parse_rus_date_to_naive_date(on_date.text)

                print('last update: {}'.format(last_update))

            # Schedule itself
            # Here determines each row of schedule
            tt = soup.find('table', class_='t')

            # The first row, it is the columns' headers,
            # which will use to determine bus stop order for correct mapping
            td_tags = tt.tr.find_all('td', recursive=False)
            raw_stops = list([td.text.strip() for td in td_tags])

            self.sync_stops_list(raw_stops, route)

            print('\n')
            # # for each row determine row cell's values
            # for row in tt.find_all('tr', recursive=False)[1:]:
            #     td_tags = row.find_all('td', recursive=False)
            #     # schedule_time = r4.findall(row)
            #     # print('\t'.join([td.text for td in td_tags]))
            #
            #     row_items = []
            #     # import ipdb; ipdb.set_trace()
            #     for td in td_tags:
            #         tdt = td.text.replace('ул.', '').replace('ул', '').strip()
            #         parts = tdt.split(' ')
            #         if len(parts) > 1:
            #             time = parts[-1].strip()
            #             desc = parts[0].strip().strip('-')
            #             row_items.append((time, desc))
            #             continue
            #
            #         parts = tdt.split('-')
            #         if len(parts) > 1 and all([p.strip() for p in parts]):
            #             time = parts[-1].strip()
            #             desc = parts[0].strip()
            #             row_items.append((time, desc))
            #             continue
            #
            #         time = tdt
            #         desc = ''
            #         row_items.append((time, desc))
            #
            #     print('\t'.join([str(td) for td, _ in row_items]))
            #     print('\t'.join([str(de) for _, de in row_items]))
            #
            #     #print(td.text)
            #     # print('\n')

            print(route)

            break

    def sync_stops_list(self, stops_list, route):
        rpqs = RoutePoint.objects.filter(route=route, lap=0)
        rplst = list(RoutePoint.objects.filter(route=route, lap=0).order_by('route', 'lap', 'order'))
        stop_ids = set([tpl[0] for tpl in RoutePoint.objects.filter(route=route, lap=0).values_list('stop_id')])
        print(stop_ids)
        stop_qs = Stop.objects.filter(id__in=stop_ids)

        for stop in stops_list:
            parsed = process_platform_input(stop)

            res = list(stop_qs.filter(alias__name__in=parsed['raw_aliases']))
            if res:
                if len(res) > 1:
                    self.stdout.write(parsed['raw'])
                    self.stdout.write(self.style.SUCCESS('has few stop for alias\n'))
                    self.stdout.write('{}\n'.format(res))
                else:
                    rps = rpqs.filter(stop=res[0])
                    for rp in rps:
                        rplst.remove(rp)

                    self.stdout.write(parsed['raw'])
                    self.stdout.write(self.style.SUCCESS('exists'))

            else:
                alias_for = self.suggest_alias(parsed, rplst)

                if alias_for == 0:
                    break

                if isinstance(alias_for, list):
                    for to in alias_for:
                        rplst.remove(to)
                        print(to)

    def suggest_alias(self, stopd, rplst):
        print('-'*10)
        print(stopd)

        print('May by one of:')
        for i in range(len(rplst)):
            rp = rplst[i]
            self.stdout.write(
                self.style.SUCCESS('  {}'.format(str(rp.stop.id).rjust(3))) +
                ': {}\t\t{}'.format(rp.direction, rp.stop)
            )

        print('? (input number or 0 for exit)')

        num = input('> ')

        if num in {'0', 0, 'q', 'Q'}:
            return 0

        else:
            try:
                res = []
                for rp in rplst:
                    if rp.stop.id == int(num):
                        res.append(rp)

                if res:
                    return res
                else:
                    return 0

            except (IndexError, ValueError):
                return 0

