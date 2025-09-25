from django.urls import path
from .views import (
    AssetCategoryListView, 
    AssetDetailView, 
    AssetListCreateView,
    AssetsByCategoryView,
    MyAssetCategoriesListView,
)


urlpatterns = [
    path('', AssetListCreateView.as_view(), name='asset-list-create'),
    path('<int:pk>/', AssetDetailView.as_view(), name='asset-detail'),
    path('assets-by-category/', AssetsByCategoryView.as_view(), name='assets-by-category'),
    # URL para AssetCategory (Solo listar)
    path('categories/', AssetCategoryListView.as_view(), name='assetcategory-list'),
    # URL para listar solo las categorías que tienen assets del usuario en sesión
    path('my-categories/', MyAssetCategoriesListView.as_view(), name='my-asset-categories'),
]
