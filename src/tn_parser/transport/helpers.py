# coding=utf-8

from datetime import date


_RUS_MONTHS = ['января', 'февраля',
               'марта', 'апреля', 'мая',
               'июня', 'июля', 'августа',
               'сентября', 'октября', 'ноября',
               'декабря']


def parse_rus_date_to_naive_date(date_str):
    """
    Parse string date like '24 апреля 2017'
    :param str date_str:
    :return date:
    """
    parts = date_str.split(' ')

    month = _RUS_MONTHS.index(parts[1].strip())
    if month < 0:
        raise ValueError('Can not parse this rus date: {}'.format(date_str))

    return date(int(parts[2]), month+1, int(parts[0]))

