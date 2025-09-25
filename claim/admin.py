from django.contrib import admin
from .models import ClaimAction,  ClaimActionTransaction, ImportLog


@admin.register(ClaimAction)
class ClaimActionAdmin(admin.ModelAdmin):
    list_filter = ['user']

admin.site.register(ClaimActionTransaction)
admin.site.register(ImportLog)

