# your_app/pagination.py

from rest_framework.pagination import PageNumberPagination

class StandardResultsSetPagination(PageNumberPagination):
    """
    Clase de paginación personalizada para devolver 100 resultados por página.
    """
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 1000
