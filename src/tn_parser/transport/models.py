# coding=utf-8

from __future__ import unicode_literals

from abc import ABCMeta, abstractmethod
import six

import math

from django.db import models


class EnumBase(six.with_metaclass(ABCMeta, object)):

    @property
    @abstractmethod
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


class GeoDirections(EnumBase):
    NORTH = 'n'
    NORTHEAST = 'ne'
    EAST = 'e'
    SOUTHEAST = 'se'
    SOUTH = 's'
    SOUTHWEST = 'sw'
    WEST = 'w'
    NORTHWEST = 'nw'

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

    @classmethod
    def normalize_angle(cls, angle):
        if angle < 0:
            return 360 + (angle % 360)
        else:
            return angle % 360

    @classmethod
    def from_angle(cls, angle):
        step = 360/len(cls.as_tuple)
        angle = cls.normalize_angle(angle)
        comp_angle = round(angle + step/2, 1)
        e = 0.1
        x = 0
        for key, repr in cls.as_tuple:
            if x <= comp_angle < x + step:
                return key
            x += step
        else:
            return cls.NORTH


class Directions(EnumBase):
    FORWARD = 'forward'
    BACKWARD = 'backward'
    CIRCULAR = 'circular'

    as_tuple = (
        (FORWARD, "Вперёд"),
        (BACKWARD, "Назад"),
        (CIRCULAR, "Кольцевой"),
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


class Point(object):
    lon = 0.0
    lat = 0.0

    @property
    def length(self):
        return math.hypot(self.lon, self.lat)

    def distance_to(self, other):
        return math.hypot(self.lon-other.lon, self.lat-other.lat)

    def angle(self, other):
        cos_a = (self * other)/(self.length * other.length)
        # return math.degrees(math.acos(cos_a))
        return math.degrees(cos_a)

    def __init__(self, lon=0.0, lat=0.0, repr=None):
        if repr is not None:
            lst = repr.replace('POINT', '').\
                replace('(', '')\
                .replace(')', '')\
                .split(' ')

            self.lon = float(lst[0])
            self.lat = float(lst[1])
        else:
            self.lon = lon
            self.lat = lat

    def __add__(self, other):
        return Point(
            self.lon + other.lon,
            self.lat + other.lat)

    def __sub__(self, other):
        return Point(
            self.lon - other.lon,
            self.lat - other.lat)

    def __mul__(self, other):
        return self.lon * other.lon + self.lat * other.lat

    def __lshift__(self, other):
        diff = self - other
        return Point(
            self.lon+diff.lon,
            self.lat+diff.lat)

    def __rshift__(self, other):
        lon = self.lon-other.lon
        lat = self.lat-other.lat
        return Point(
            self.lon-lon,
            self.lat-lat)

    def __sub__(self, other):
        return Point(
            self.lon - other.lon,
            self.lat - other.lat)

    def __repr__(self):
        return 'POINT({lon:.13f} {lat:.13f})'.format(**self.__dict__)

    def __str__(self):
        return 'Point(lon: {lon:.6f}, lat: {lat:.6f})'.format(**self.__dict__)

    def __unicode__(self):
        return unicode(str(self))


class RouteTypes(EnumBase):
    BUS = 'bus'
    TROLLEYBUS = 'trolleybus'

    as_tuple = (
        (BUS, "Автобус"),
        (TROLLEYBUS, "Троллейбус"),
    )


class NameAlias(models.Model):
    name = models.CharField(max_length=100)

    class META:
        abstract = True


class Platform(models.Model):
    name = models.CharField(max_length=100)
    full_name = models.CharField(max_length=200, blank=True, default='')
    description = models.TextField(blank=True, default='')

    geo_direction = models.CharField(max_length=16, blank=True,
                                     choices=GeoDirections.as_tuple)

    def get_queryset(self, request):
        qs = super(Platform, self).get_queryset(request)
        qs = qs.annotate(models.Count('stops'))
        return qs

    def __eq__(self, other):
        if self.pk:
            return super(Platform, self).__eq__(other)
        else:
            return self.name.strip().lower() == other.name.strip().lower()

    def __str__(self):
        return self.name


class PlatformAlias(NameAlias):
    platform = models.ForeignKey(Platform, related_name='aliases')


class Stop(models.Model):
    platform = models.ForeignKey(Platform, on_delete=models.CASCADE,
                                 related_name='stops')

    longitude = models.FloatField(blank=True, null=True,
                                  help_text='Longitude in WGS84 system')
    latitude = models.FloatField(blank=True, null=True,
                                 help_text='Latitude in WGS84 system')

    alias = models.OneToOneField(PlatformAlias, null=True,
                                 on_delete=models.SET_NULL,
                                 related_name='stop')

    class META:
        unique_together = ('platform', 'longitude', 'latitude')

    def __eq__(self, other):
        if self.pk:
            return super(Stop, self).__eq__(other)
        else:
            return self.platform == other.platform\
                and self.longitude == other.longitude\
                and self.latitude == other.latitude

    def __repr__(self):
        return '{} {}'.format(self.platform, Point(self.longitude, self.latitude))

    def __str__(self):
        return self.__repr__()


class Route(models.Model):
    name = models.CharField(max_length=32)
    code = models.CharField(max_length=32, unique=True)
    type = models.CharField(
        max_length=32,
        choices=RouteTypes.as_tuple,
        default=RouteTypes.BUS,
    )
    canceled = models.DateField(blank=True, null=True, default=None)

    class META:
        unique_together = ("name", "type")

    def __str__(self):
        return '%s (%s)' % (self.name, self.type)


class DataProviderUrl(models.Model):
    link = models.URLField(help_text='The link for getting data through certain API')
    type = models.CharField(max_length=32, choices=DataProviderTypes.as_tuple)
    coding = models.CharField(max_length=32, default='utf-8')

    route = models.ForeignKey(Route, related_name='data_providers',
                              blank=True, null=True, on_delete=models.CASCADE)

    route_code = models.CharField(max_length=32, blank=True, default='')

    class META:
        unique_together = ("name", "type")

    def __str__(self):
        return 'route: %s, type: %s' % (self.route, self.type)


class RouteWeekDimension(models.Model):
    weekend = models.BooleanField(default=False)
    weekday = models.SmallIntegerField(
        default=1,
        help_text="Day of week from 1 to 7, first is monday")

    def __str__(self):
        return 'day: %s%s' % (self.weekday, ' we' if self.weekend else '')


class RoutePoint(models.Model):
    week_dimension = models.ForeignKey(RouteWeekDimension)
    route = models.ForeignKey(Route,
                              on_delete=models.CASCADE,
                              related_name='route_points')
    stop = models.ForeignKey(Stop,
                             on_delete=models.CASCADE,
                             related_name='route_points')

    time = models.TimeField(blank=True, null=True)
    skip = models.BooleanField(default=False)
    lap = models.SmallIntegerField(default=-1)
    lap_start = models.BooleanField(default=False)
    direction = models.CharField(max_length=16, choices=Directions.as_tuple)
    order = models.SmallIntegerField(default=999)

    geo_direction = models.CharField(max_length=16, blank=True,
                                     choices=GeoDirections.as_tuple)
    angle = models.FloatField(default=0.0)
    on_demand = models.BooleanField(default=False)

    class META:
        unique_together = (('week_dimension', 'route', 'platform'),
                           ('lap', 'order'))

    def next_stop(self):
        raise NotImplemented()

    def prev_stop(self):
        raise NotImplemented()

    def __str__(self):
        return '%s %s %s' % (self.route, self.stop, self.week_dimension)


class RouteDateDimension(RouteWeekDimension):
    year = models.SmallIntegerField()
    month = models.SmallIntegerField()
    day = models.SmallIntegerField()

    week = models.SmallIntegerField()

    date = models.DateTimeField()


class RouteSchedule(RoutePoint):
    date_dimension = models.ForeignKey(RouteDateDimension,
                                       related_name='route_schedules',
                                       on_delete=models.CASCADE)

