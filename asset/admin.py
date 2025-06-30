from django.contrib import admin
from .models import AssetCategory, ClaimAction, Asset, ClaimActionTransaction

# Register your models here.
admin.site.register(Asset)
admin.site.register(AssetCategory)
admin.site.register(ClaimAction)
admin.site.register(ClaimActionTransaction)
