from django.contrib import admin
from .models import AgentInteractionLog, Asset 


admin.site.register(AgentInteractionLog)
admin.site.register(Asset)