from django.contrib import admin
from .models import CustomUser, Company, Profile, CompanyProfile #, Role, 


admin.site.register(CustomUser)
admin.site.register(Profile)
#admin.site.register(Role)
admin.site.register(Company)
admin.site.register(CompanyProfile)