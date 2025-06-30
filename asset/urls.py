from django.urls import path, include
from .views import AssetCategoryListView, ImportDataView, AssetViewSet
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'', AssetViewSet, basename='assets')
router.register('categories/', AssetCategoryListView, basename='category_list')

urlpatterns = [
    #path('', AssetViewSet, basename='asset-list-create'),
    path('', include(router.urls)),
    #path('categories/', AssetCategoryListView.as_view(), name='categories_list'),
    #path('<int:pk>/', AssetAPIView.as_view(), name='asset-detail-update-delete'),   
    # path('import-data/', ImportDataView.as_view(), name='import-data'), 
]
