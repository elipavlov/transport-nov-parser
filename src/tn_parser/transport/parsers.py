# coding=utf-8

import re

OPTIONS_RAW = "<select\s.*?name='{0}'.*?>\s*?(?P<options>.*?)</select"
OPTIONS_RE = re.compile(
    "<option\s*?value=\'(?P<code>.*?)_?[rv]?\'.*?>(?P<name>.*?)</option",
    re.I | re.S)


def get_options_part(raw_data, data_name):
    # import ipdb; ipdb.set_trace()
    options = re.findall(
        OPTIONS_RAW.format(data_name),
        raw_data,
        re.I | re.S)

    if len(options) != 1:
        RuntimeError('Wrong input data')

    return options[0]


def get_bus_routes_from_page(page_html):
    raw = get_options_part(page_html, 'avt')

    options = OPTIONS_RE.findall(raw)

    return [{'code': opt[0].strip(),
             'name': opt[1].strip()} for opt in options]


def get_trolleybus_routes_from_page(page_html):
    raw = get_options_part(page_html, 'trol')

    options = OPTIONS_RE.findall(raw)

    return [{'code': opt[0].strip(),
             'name': opt[1].strip()} for opt in options]


