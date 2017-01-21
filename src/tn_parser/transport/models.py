# coding=utf-8

from __future__ import unicode_literals

from abc import ABCMeta, abstractproperty

from django.db import models


class EnumBase(object):
    __metaclass__ = ABCMeta

    @abstractproperty
    def as_tuple(self):
        raise NotImplemented()

    @classmethod
    def as_reverse_tuple(cls):
        return tuple([(item[1], item[0]) for item in cls.as_tuple])

    @classmethod
    def as_dict(cls):
        return dict(cls.as_tuple)

    @classmethod
    def as_reverse_dict(cls):
        return dict(cls.as_revert_tuple())


class Directions(EnumBase):
    NORTH = 0
    NORTHEAST = 1
    EAST = 2
    SOUTHEAST = 3
    SOUTH = 4
    SOUTHWEST = 5
    WEST = 6
    NORTHWEST = 7

    as_tuple = (
        (NORTH, "Север"),
        (NORTHEAST, "Северо-восток"),
        (EAST, "Восток"),
        (SOUTHEAST, "Юго-восток"),
        (SOUTH, "Юг"),
        (SOUTHWEST, "Юго-запад"),
        (WEST, "Запад"),
        (NORTHWEST, "Северо-запад"),
    )


class DataProviderTypes(EnumBase):
    TWOGIS_ROUTE_API = '2gis_route_api'
    ROUTES_HTML_PAGE = 'routes_html_page'
    ROUTE_HTML_PAGE = 'route_html_page'

    as_tuple = (
        (TWOGIS_ROUTE_API, "2GIS route API"),
        (ROUTES_HTML_PAGE, "Routes HTML-page"),
        (ROUTE_HTML_PAGE, "Route HTML-page"),
    )


class RouteTypes(EnumBase):
    BUS = 0
    TROLLEYBUS = 1

    as_tuple = (
        (BUS, "Автобус"),
        (TROLLEYBUS, "Троллейбус"),
    )


class NameAlias(models.Model):
    name = models.CharField(max_length=100)

    class META:
        abstract = True


class Platform(models.Model):
    name = models.CharField(max_length=100, unique=True)
    full_name = models.CharField(max_length=200, blank=True, default='')
    description = models.TextField(blank=True, default='')

    longitude = models.FloatField(blank=True, null=True,
                                  help_text='Longitude in WGS84 system')
    latitude = models.FloatField(blank=True, null=True,
                                 help_text='Latitude in WGS84 system')

    bidirectional = models.BooleanField(default=False)
    direction_1 = models.SmallIntegerField(blank=True, null=True,
                                           choices=Directions.as_tuple)
    direction_2 = models.SmallIntegerField(blank=True, null=True,
                                           choices=Directions.as_tuple)


class PlatformAlias(NameAlias):
    platform = models.ForeignKey(Platform, related_name='aliases')


class Route(models.Model):
    name = models.CharField(max_length=32)
    code = models.CharField(max_length=32, unique=True)
    type = models.SmallIntegerField(
        choices=RouteTypes.as_tuple,
        default=RouteTypes.BUS,
    )

    class META:
        unique_together = ("name", "type")


class DataProviderUrl(models.Model):
    link = models.URLField(help_text='The link for getting data through certain API')
    type = models.CharField(max_length=32, choices=DataProviderTypes.as_tuple)
    coding = models.CharField(max_length=32, default='utf-8')

    route = models.ForeignKey(Route, blank=True, null=True, on_delete=models.CASCADE)


class RouteWeekDimension(models.Model):
    weekend = models.BooleanField(default=False)
    weekday = models.SmallIntegerField(default=1,
                                       help_text="Day of week from 1 to 7, first is monday")


class RoutePoint(models.Model):
    week_dimension = models.ForeignKey(RouteWeekDimension)
    route = models.ForeignKey(Route,
                              on_delete=models.CASCADE,
                              related_name='week_points',
                              )
    platform = models.ForeignKey(Platform,
                                 on_delete=models.CASCADE,
                                 related_name='platforms')

    time = models.TimeField(blank=True, null=True)
    order = models.SmallIntegerField(default=999)
    lap = models.SmallIntegerField(default=-1)
    lap_start = models.BooleanField(default=False)
    skip = models.BooleanField(default=False)

    direction = models.SmallIntegerField(blank=True, null=True,
                                           choices=Directions.as_tuple)

    def next_platform(self):
        raise NotImplemented()

    def prev_platform(self):
        raise NotImplemented()


class RouteDateDimension(RouteWeekDimension):
    year = models.SmallIntegerField()
    month = models.SmallIntegerField()
    day = models.SmallIntegerField()

    week = models.SmallIntegerField()

    date = models.DateTimeField()


class RouteSchedule(RoutePoint):
    date_dimension = models.ForeignKey(RouteDateDimension,
                                       on_delete=models.CASCADE)

