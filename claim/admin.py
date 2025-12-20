from django.contrib import admin
from .models import ClaimAction,  ClaimActionTransaction, ImportLog, ClassActionLawsuit

@admin.register(ClassActionLawsuit)
class ClassActionLawsuitAdmin(admin.ModelAdmin):
    list_filter = ["status", "send_format", "accept_claim", "register_payment"]

@admin.register(ClaimAction)
class ClaimActionAdmin(admin.ModelAdmin):
    list_filter = ['user']

admin.site.register(ClaimActionTransaction)
admin.site.register(ImportLog)

