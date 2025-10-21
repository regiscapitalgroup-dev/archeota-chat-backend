from rest_framework.response import Response
import uuid
from rest_framework.views import APIView
from django.db import transaction
import pandas as pd
from asset.pagination import StandardResultsSetPagination
from .models import ClaimActionTransaction, ClaimAction, ImportLog
from rest_framework import status, generics, permissions
from .serializers import (
    ClaimActionSerializer,
    FileUploadSerializer,
    ClaimActionTransactionSerializer,
    ImportLogSerializer,
    ErrorLogDetailSerializer
)
from rest_framework.parsers import MultiPartParser, FormParser
from django.contrib.auth import get_user_model
from django.db.models import Count
from users.permissions import IsCompanyManager

# Added for dashboard aggregation of assets
from asset.models import Asset
from asset.serializers import AssetSerializer


USER_MODEL = get_user_model()


class ClaimActionListView(generics.ListAPIView):
    serializer_class = ClaimActionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return ClaimAction.objects.none()

        # Default: own claims
        own_qs = ClaimAction.objects.filter(user=user)

        # Optional target user by query param (e.g., ?user_id=123)
        user_id = self.request.query_params.get('user_id')
        if not user_id:
            return own_qs

        # Parse target id
        try:
            target_id = int(user_id)
        except (TypeError, ValueError):
            return own_qs

        # Load target user
        try:
            target_user = USER_MODEL.objects.get(pk=target_id)
        except USER_MODEL.DoesNotExist:
            return ClaimAction.objects.none()

        # If requesting own data, return own
        if target_user.id == user.id:
            return own_qs

        # Authorization: only managers or superior can view others
        if user.is_superuser:
            return ClaimAction.objects.filter(user=target_user)

        role = getattr(user, 'role', None)

        # Company Admin can view users they directly manage or second-level reports
        if role == 'COMPANY_ADMIN':
            managed_by = getattr(target_user, 'managed_by', None)
            if managed_by == user or getattr(managed_by, 'managed_by', None) == user:
                return ClaimAction.objects.filter(user=target_user)

        # Company Manager can view direct reports
        if role == 'COMPANY_MANAGER':
            if getattr(target_user, 'managed_by', None) == user:
                return ClaimAction.objects.filter(user=target_user)

        # Fallback to own claims if not authorized
        return own_qs

    def perform_create(self, serializer):
        # AÑADIDO: Asigna automáticamente el usuario autenticado al crear
        serializer.save(user=self.request.user)


class ClaimActionDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Permite Leer (Detalle), Actualizar y Borrar una ClaimAction específica.
    """
    serializer_class = ClaimActionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Sobrescribimos para asegurar que el usuario solo pueda
        acceder a SUS PROPIAS ClaimActions.
        """
        user = self.request.user
        if not user.is_authenticated:
            return ClaimAction.objects.none()
        return ClaimAction.objects.filter(user=user)


class ClaimActionTransactionListView(generics.ListAPIView):
    serializer_class = ClaimActionTransactionSerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        request = self.request
        # Must be authenticated to access any data
        if not request.user or not request.user.is_authenticated:
            return ClaimActionTransaction.objects.none()

        # Optional target user by query param (?user_id=123); default to session user
        user_id = request.query_params.get('user_id')
        if user_id is None or user_id == '':
            target_user_id = request.user.id
        else:
            try:
                target_user_id = int(user_id)
            except (TypeError, ValueError):
                # If invalid user_id, fallback to session user
                target_user_id = request.user.id

        return (
            ClaimActionTransaction.objects
            .filter(user_id=target_user_id)
            .order_by('-trade_date', 'pk')
        )

    def perform_create(self, serializer):
        # AÑADIDO: Asigna el usuario de la sesión al crear una transacción
        serializer.save(user=self.request.user)


class ClaimActionTransactionDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Permite Leer (Detalle), Actualizar y Borrar una ClaimActionTransaction específica.
    """
    serializer_class = ClaimActionTransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Sobrescribimos para asegurar que el usuario solo pueda
        acceder/editar/borrar SUS PROPIAS transacciones.
        """
        user = self.request.user
        if not user.is_authenticated:
            return ClaimActionTransaction.objects.none()
        return ClaimActionTransaction.objects.filter(user=user)


class ImportTransactionsDataView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, *args, **kwargs):
        serializer = FileUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        file_obj = serializer.validated_data['file']
        current_job_id = uuid.uuid4()
        target_user_id = serializer.validated_data.get('target_user_id')
        user_for_import = None

        if target_user_id:
            user_for_import = USER_MODEL.objects.get(pk=target_user_id)
        else:
            # Comportamiento por defecto: usar el usuario de la sesión.
            user_for_import = request.user

        successful_imports = 0
        failed_imports = 0

        company_profile = self.request.user.profile.company

        if not company_profile:
            company_profile = 'No Company'

        try:

            if file_obj.name.endswith('.csv'):
                df = pd.read_csv(file_obj)
            elif file_obj.name.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(file_obj)
            else:
                return Response({'error': 'Unsupported file format.'}, status=status.HTTP_400_BAD_REQUEST)

            df = df.fillna(0, inplace=False)

            for index, row in df.iterrows():
                row_number = index + 2
                try:
                    with transaction.atomic():
                        ClaimActionTransaction.objects.create(
                            data_for=row['Data For'],
                            trade_date=row['Trade Date'],
                            account=row['Account'],
                            account_name=row['Account Name'],
                            account_type=row['Account Type'],
                            account_number=row['Account Number'],
                            activity=row['Activity'],
                            description=row['Description'],
                            symbol=row['Symbol'],
                            quantity=row['Quantity'],
                            amount=row['Amount'],
                            notes=row['Notes'],
                            type='Type',
                            company=company_profile,
                            user=user_for_import,
                        )
                    successful_imports += 1
                except Exception as e:
                    failed_imports += 1
                    row_dict = row.to_dict()

                    for key, value in row_dict.items():
                        if isinstance(value, pd.Timestamp):
                            row_dict[key] = value.isoformat()

                    ImportLog.objects.create(
                        import_job_id=current_job_id,
                        status=ImportLog.StatusChoices.ERROR,
                        row_number=row_number,
                        error_message=str(e),
                        row_data=row_dict,
                        user=user_for_import,
                    )
            return Response({
                "message": "Processing complete.",
                "import_job_id": current_job_id,
                "successful_imports": successful_imports,
                "failed_imports": failed_imports
            }, status=status.HTTP_202_ACCEPTED)
        except Exception as e:
            return Response({'error': f"Error processing file: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ImportLogListView(generics.ListAPIView):
    serializer_class = ImportLogSerializer

    def get_queryset(self):
        job_id = self.kwargs['job_id']
        return ImportLog.objects.filter(import_job_id=job_id).order_by('row_number')


class UserImportJobsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user_job_ids = ImportLog.objects.filter(
            user=request.user,
            status=ImportLog.StatusChoices.ERROR
        ).values_list('import_job_id', flat=True).distinct()

        response_data = []

        for job_id in user_job_ids:
            error_logs = ImportLog.objects.filter(
                import_job_id=job_id,
                status=ImportLog.StatusChoices.ERROR
            ).order_by('row_number')

            errors_serializer = ErrorLogDetailSerializer(error_logs, many=True)

            job_data = {
                "import_job_id": job_id,
                "import_date": error_logs.first().created_at if error_logs.exists() else None,
                "error_count": error_logs.count(),
                "errors": errors_serializer.data
            }
            response_data.append(job_data)

        return Response(response_data)


class ClaimActionDashboardView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        # Determinar el usuario objetivo: ?user_id=<id> o usuario de la sesión
        user_id_param = request.query_params.get('user_id') or kwargs.get('user_id')
        if user_id_param is None or user_id_param == '':
            if not request.user or not request.user.is_authenticated:
                return Response({'detail': 'No autenticado.'}, status=status.HTTP_401_UNAUTHORIZED)
            target_user_id = request.user.id
        else:
            try:
                target_user_id = int(user_id_param)
            except (TypeError, ValueError):
                return Response({'detail': 'El parámetro user_id debe ser un número entero.'}, status=status.HTTP_400_BAD_REQUEST)

        # Query de claims filtrados por usuario
        user_claims = ClaimAction.objects.filter(user_id=target_user_id)

        # Agregación por estatus excluyendo nulos, vacíos y la cadena "NULL"
        by_status_qs = (
            user_claims
            .exclude(claim_status__isnull=True)
            .exclude(claim_status='')
            .exclude(claim_status__iexact='NULL')
            .values('claim_status')
            .annotate(total=Count('id'))
            .order_by('-total')
        )
        totals_by_status = [
            {
                'status': item['claim_status'],
                'total': item['total'],
            }
            for item in by_status_qs
        ]
        total_claims = user_claims.count()

        return Response({
            'user_id': target_user_id,
            'total_claims': total_claims,
            'totals_by_status': totals_by_status,
        })


class ManagerDependentsClaimListView(generics.ListAPIView):
    serializer_class = ClaimActionSerializer
    permission_classes = [permissions.IsAuthenticated, IsCompanyManager]

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return ClaimAction.objects.none()
        # Listar solo claims cuyos usuarios son gestionados por el manager en sesión
        return ClaimAction.objects.filter(user__managed_by=self.request.user)
