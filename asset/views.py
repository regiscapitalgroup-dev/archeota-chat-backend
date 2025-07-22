from .models import Asset, AssetCategory, ClaimActionTransaction, ClaimAction, ImportLog
from .serializers import (
    AssetCategorySerializer, 
    AssetCategory, 
    AssetSerializer, 
    FileUploadSerializer,
    ClaimActionTransactionSerializer, 
    ClaimActionSerializer, 
    CategoryWithAssetsSerializer, 
    ImportLogSerializer, 
    ErrorLogDetailSerializer
)
from rest_framework.parsers import MultiPartParser, FormParser 
from rest_framework.response import Response
from rest_framework import status, generics, permissions
from rest_framework.views import APIView
from django.db import transaction
import pandas as pd
from .pagination import StandardResultsSetPagination 
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Prefetch
import uuid


class AssetListCreateView(generics.ListCreateAPIView):
    serializer_class = AssetSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['category']

    def get_queryset(self):
        return Asset.objects.filter(owner=self.request.user).order_by('-asset_date')

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    def list(self, request, *args, **kwargs):
        if 'category' in request.query_params:
            queryset = self.filter_queryset(self.get_queryset())
            names_list = queryset.values_list('name', flat=True)
            return Response(names_list)
        return super().list(request, *args, **kwargs)


class AssetDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = AssetSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Asset.objects.filter(owner=self.request.user)


class AssetCategoryListView(generics.ListAPIView):
    queryset = AssetCategory.objects.all().order_by('category_name')
    serializer_class = AssetCategorySerializer
    permission_classes = [permissions.IsAuthenticated]


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
            return ClaimActionTransaction.objects.all().order_by('-trade_date', 'pk') 
        return ClaimActionTransaction.objects.none()


class ImportTransactionsDataView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, *args, **kwargs):
        serializer = FileUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        file_obj = serializer.validated_data['file']
        current_job_id = uuid.uuid4()

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

            for index, row in  df.iterrows():
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
                            user=self.request.user.email,
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
                        user=self.request.user.email,  
                    )
            return Response({
                "message": "Processing complete.",
                "import_job_id": current_job_id,
                "successful_imports": successful_imports,
                "failed_imports": failed_imports
            }, status=status.HTTP_202_ACCEPTED)
        except Exception as e:
            return Response({'error': f"Error processing file: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AssetsByCategoryView(generics.ListAPIView):
    serializer_class = CategoryWithAssetsSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        user_assets = Asset.objects.filter(owner=user)

        queryset = AssetCategory.objects.filter(
            asset__owner=user
        ).distinct().prefetch_related(
            Prefetch(
                'asset_set', 
                queryset=user_assets.order_by('name'),
                to_attr='assets' 
            )
        )
        return queryset


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
