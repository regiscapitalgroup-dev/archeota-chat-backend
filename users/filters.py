import django_filters
from django.contrib.auth import get_user_model

CustomUser = get_user_model()

class UserFilter(django_filters.FilterSet):
    """
    FilterSet para el modelo CustomUser.
    """
    # Filtro para el nombre del rol (USER, COMPANY, etc.)
    # Busca a través de la relación: user.role.name
    role_name = django_filters.CharFilter(
        field_name='role__name', 
        lookup_expr='iexact' # Búsqueda exacta e insensible a mayúsculas/minúsculas
    )
    
    # Filtro para el nombre de la compañía
    # Busca a través de la relación: user.companyprofile.company_name
    company_name = django_filters.CharFilter(
        field_name='companyprofile__company_name', 
        lookup_expr='icontains' # Busca si el texto está contenido, insensible a mayúsculas/minúsculas
    )

    class Meta:
        model = CustomUser
        # Aquí definimos los campos por los que se puede filtrar directamente
        fields = ['email', 'first_name', 'last_name']