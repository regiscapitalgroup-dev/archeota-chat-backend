from django.contrib import admin
from .models import AssetCategory, Asset


admin.site.register(Asset)
admin.site.register(AssetCategory)
