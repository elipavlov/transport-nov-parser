# coding=utf-8
from django.db import models

from django.contrib import admin

from .models import DataProviderUrl, \
    Route, RoutePoint, RouteSchedule, \
    RouteWeekDimension, RouteDateDimension, \
    Platform, PlatformAlias, Stop


class DataProviderUrlAdmin(admin.ModelAdmin):
    pass


class RouteAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'type')
    list_filter = ('type', )
    ordering = ('name', )


class RoutePointAdmin(admin.ModelAdmin):
    list_display = ('route', 'stop', 'week_dimension',
                    'time',
                    'lap', 'order', 'direction', 'geo_direction',
                    'on_demand', 'skip')
    list_filter = ('route', 'stop', 'week_dimension', 'direction', )
    ordering = ('route', 'lap', 'order')


class RouteScheduleAdmin(admin.ModelAdmin):
    pass


class StopAdmin(admin.ModelAdmin):
    list_display = ('platform', 'latitude', 'longitude')
    list_filter = ('platform', )
    ordering = ('platform', )


class PlatformAdmin(admin.ModelAdmin):
    list_display = ('name', 'stops_count', )
    ordering = ('name', )

    def stops_count(self, obj):
        # return obj.stops__count
        return obj.stops.count()

    # stops_count.admin_order_field = 'stops_count'


admin.site.register(DataProviderUrl, DataProviderUrlAdmin)
admin.site.register(Route, RouteAdmin)
admin.site.register(RoutePoint, RoutePointAdmin)

admin.site.register(RouteSchedule, RouteScheduleAdmin)

admin.site.register(RouteWeekDimension, admin.ModelAdmin)
admin.site.register(RouteDateDimension, admin.ModelAdmin)

admin.site.register(Platform, PlatformAdmin)
admin.site.register(Stop, StopAdmin)
admin.site.register(PlatformAlias, admin.ModelAdmin)




