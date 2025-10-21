from django.urls import path
from .views import (
    ClaimActionListView,
    ClaimActionTransactionListView,

    ImportTransactionsDataView,
    ImportLogListView,
    UserImportJobsView,
    ClaimActionDashboardView,
    ManagerDependentsClaimListView,
    ClaimActionDetailView,
    ClaimActionTransactionDetailView
)

urlpatterns = [
    path('claim-actions/', ClaimActionListView.as_view(), name='claimaction-list'),
    path('claim-actions/<int:pk>/', ClaimActionDetailView.as_view(), name='claimaction-detail'), # <-- AÑADIR ESTA LÍNEA
    path('claim-actions/dashboard/', ClaimActionDashboardView.as_view(), name='claimaction-dashboard'),
    path('claim-actions/dependents/', ManagerDependentsClaimListView.as_view(), name='manager-dependents-claim-list'),
    path('claim-transactions/', ClaimActionTransactionListView.as_view(), name='claimtransaction-list-create'),
    path('claim-transactions/<int:pk>/', ClaimActionTransactionDetailView.as_view(), name='claimtransaction-detail'),
    path('transactions/import-data/', ImportTransactionsDataView.as_view(), name='import-transaction-data'),
    path('import-logs/<uuid:job_id>/', ImportLogListView.as_view(), name='import-log-list'),
    path('my-imports/', UserImportJobsView.as_view(), name='user-import-jobs'),
]
