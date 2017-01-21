# coding=utf-8

from django.contrib import admin

from .models import DataProviderUrl, \
    Route, RoutePoint, RouteSchedule, \
    RouteWeekDimension, RouteDateDimension, \
    Platform, PlatformAlias


class DataProviderUrlAdmin(admin.ModelAdmin):
    pass


class RouteAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'type')
    list_filter = ('type', )
    ordering = ('name', )


class RoutePointAdmin(admin.ModelAdmin):
    pass


class RouteScheduleAdmin(admin.ModelAdmin):
    pass

admin.site.register(DataProviderUrl, DataProviderUrlAdmin)
admin.site.register(Route, RouteAdmin)
admin.site.register(RoutePoint, RoutePointAdmin)

admin.site.register(RouteSchedule, RouteScheduleAdmin)

admin.site.register(RouteWeekDimension, admin.ModelAdmin)
admin.site.register(RouteDateDimension, admin.ModelAdmin)

admin.site.register(Platform, admin.ModelAdmin)
admin.site.register(PlatformAlias, admin.ModelAdmin)




