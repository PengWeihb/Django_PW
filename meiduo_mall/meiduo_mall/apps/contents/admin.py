from django.contrib import admin

from . import models
# from .models import ContentCategory, Content
# Register your models here.


admin.site.register(models.ContentCategory)
admin.site.register(models.Content)


