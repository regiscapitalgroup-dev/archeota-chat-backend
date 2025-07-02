from django.urls import path, include
from .views import (AssetCategoryListView, AssetDetailView, AssetListCreateView, 
          ClaimActionListView, ClaimActionTransactionListView)


urlpatterns = [
    path('', AssetListCreateView.as_view(), name='asset-list-create'),
    path('<int:pk>/', AssetDetailView.as_view(), name='asset-detail'),

    # URL para AssetCategory (Solo listar)
    path('categories/', AssetCategoryListView.as_view(), name='assetcategory-list'),
    path('claim-actions/', ClaimActionListView.as_view(), name='claimaction-list'),
    path('claim-transactions/', ClaimActionTransactionListView.as_view(), name='claimtransaction-list'),

]
