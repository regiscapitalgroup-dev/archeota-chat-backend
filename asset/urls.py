from django.urls import path, include
from .views import (
    AssetCategoryListView, 
    AssetDetailView, 
    AssetListCreateView,
    ClaimActionListView, 
    ClaimActionTransactionListView, 
    AssetsByCategoryView,
    ImportTransactionsDataView, 
    ImportLogListView, 
    UserImportJobsView
)


urlpatterns = [
    path('', AssetListCreateView.as_view(), name='asset-list-create'),
    path('<int:pk>/', AssetDetailView.as_view(), name='asset-detail'),
    path('assets-by-category/', AssetsByCategoryView.as_view(), name='assets-by-category'),
    # URL para AssetCategory (Solo listar)
    path('categories/', AssetCategoryListView.as_view(), name='assetcategory-list'),
    path('claim-actions/', ClaimActionListView.as_view(), name='claimaction-list'),
    path('claim-transactions/', ClaimActionTransactionListView.as_view(), name='claimtransaction-list'),
    # import data
    path('transactions/import-data/', ImportTransactionsDataView.as_view(), name='import-transaction-data'),
    path('import-logs/<uuid:job_id>/', ImportLogListView.as_view(), name='import-log-list'),
    path('my-imports/', UserImportJobsView.as_view(), name='user-import-jobs'),
]
