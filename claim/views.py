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


USER_MODEL = get_user_model()


class ClaimActionListView(generics.ListAPIView):
    queryset = ClaimAction.objects.all()
    serializer_class = ClaimActionSerializer
    permission_classes = [permissions.IsAuthenticated]


class ClaimActionTransactionListView(generics.ListAPIView):
    serializer_class = ClaimActionTransactionSerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_authenticated:
            return ClaimActionTransaction.objects.all().filter(user=self.request.user).order_by('-trade_date', 'pk')
        return ClaimActionTransaction.objects.none()


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
        # Total de todos los claims (sin filtrar por usuario)
        total_claims = ClaimAction.objects.count()
        # Conteo por estatus excluyendo valores NULL
        by_status_qs = (
            ClaimAction.objects
            .exclude(claim_status__isnull=True)
            .exclude(claim_status='NULL')
            .exclude(claim_status='')
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
        return Response({
            'total_claims': total_claims,
            'totals_by_status': totals_by_status,
        })
