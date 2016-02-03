from django.contrib import admin
from models import Pages, Channels, News, News_Channels, User_Conf, New_User, User_Custom


admin.site.register(Pages)
admin.site.register(Channels)
admin.site.register(News)
admin.site.register(News_Channels)
admin.site.register(User_Conf)
admin.site.register(New_User)
admin.site.register(User_Custom)
