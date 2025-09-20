from django.contrib import admin
from .models import ClaimAction,  ClaimActionTransaction, ImportLog


admin.site.register(ClaimAction)
admin.site.register(ClaimActionTransaction)
admin.site.register(ImportLog)

