from decimal import Decimal
from django.forms import ValidationError
from rest_framework.response import Response
import uuid
from datetime import datetime
from rest_framework.views import APIView
from django.db import transaction
import pandas as pd
from asset.pagination import StandardResultsSetPagination
from claim.services.stock import FileStockHandler
from claim.services.transaction import TransactionService
from users.models import Company
from .models import ClaimActionTransaction, ClaimAction, ImportLog, ClassActionLawsuit
from rest_framework import status, generics, permissions
from .serializers import (
    ClaimActionSerializer,
    FileUploadSerializer,
    ClaimActionTransactionSerializer,
    ImportLogSerializer,
    ErrorLogDetailSerializer,
    ClassActionLawsuitSerializer
)
from claim.services.claim import ClaimSevice
from rest_framework.parsers import MultiPartParser, FormParser
from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from users.permissions import IsCompanyManager
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle
# Added for dashboard aggregation of assets
from asset.models import Asset
from asset.serializers import AssetSerializer
from openpyxl import load_workbook


USER_MODEL = get_user_model()

class ClassActionLawsuitListView(generics.ListCreateAPIView):
    serializer_class = ClassActionLawsuitSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return ClassActionLawsuit.objects.none()
        own_qs = ClassActionLawsuit.objects.filter(user=user)
        role = getattr(user, 'role', None)
        company_id = self.request.query_params.get('company_id')
        if company_id:
            if role == 'SUPER_ADMIN':
                return ClassActionLawsuit.objects.filter(company_id=company_id)
            else:
                return ClassActionLawsuit.objects.filter(company_id=user.profile.company)
        
        return own_qs
            
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class ClassActionLawsuitDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ClassActionLawsuitSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return ClassActionLawsuit.objects.none()
        
        role = getattr(user, 'role', None)
        if role == 'SUPER_ADMIN':
            return ClassActionLawsuit.objects.all()
        if role == 'COMPANY_ADMIN' or role == 'COMPANY_MANAGER':
            return ClassActionLawsuit.objects.filter(company_id=user.profile.company)

        return ClassActionLawsuit.objects.filter(user=user)

class ClaimActionListView(generics.ListCreateAPIView):
    serializer_class = ClaimActionSerializer
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [UserRateThrottle]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return ClaimAction.objects.none()
        
        role = getattr(user, 'role', None)
        company_id = self.request.query_params.get('company_id')
        if company_id:
            if role == 'SUPER_ADMIN':
                return ClaimAction.objects.filter(company_id=company_id)
            else:
                return ClaimAction.objects.filter(company_id=user.profile.company)

        if role == 'SUPER_ADMIN':
            return ClaimAction.objects.all()

        return ClaimAction.objects.filter(Q(user=user) | Q(company_id=user.profile.company))

    def create(self, request):
        user = self.request.user
        user_role = getattr(user, 'role', None)
        data = request.data.copy()

        if user_role == 'SUPER_ADMIN':
            company_id = data.get("company_id")
            if not company_id:
                return Response(
                    {"detail": "company_id is required for SUPER_ADMIN"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            data["company"] = company_id
        else:
            data["company"] = user.profile.company.id
        
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)




class ClaimActionDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ClaimActionSerializer
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [UserRateThrottle]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return ClaimAction.objects.none()
        
        user_role = getattr(user, "role", None) 
        if user_role == 'SUPER_ADMIN':
            return ClaimAction.objects.all()

        return ClaimAction.objects.filter(user=user)


class ClaimActionDetailsView(generics.RetrieveAPIView):
    serializer_class = ClaimActionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        qs = ClaimAction.objects.select_related("company")

        if user.role != 'SUPER_ADMIN':
            qs = qs.filter(company=user.profile.company)
        return qs
    
    def get(self, request, *args, **kwargs):
        claim_action = self.get_object()
        if not claim_action.company:
            return Response('Company does not exist in claim action', status=status.HTTP_400_BAD_REQUEST)
        serializer = ClaimActionSerializer(claim_action, context={'request': request})
        return Response(serializer.data)

class ClaimActionGenerateClaimView(generics.RetrieveAPIView):
    serializer_class = ClaimActionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        qs = ClaimAction.objects.select_related("company")

        if user.role != 'SUPER_ADMIN':
            qs = qs.filter(company=user.profile.company)
        return qs
    
    def get(self, request, *args, **kwargs):
        claim_action = self.get_object()
        if not claim_action.company:
            return Response('Company does not exist in claim action', status=status.HTTP_400_BAD_REQUEST)
        if claim_action.claimed:
            return Response('This action is already claimed', status=status.HTTP_400_BAD_REQUEST)

        svc = ClaimSevice(self.request.user, claim_action.company)
        svc.process_claim(claim_action)
        claim_action.claimed = True
        claim_action.save(update_fields=["claimed"])
        return Response()

class ClaimActionTransactionListView(generics.ListCreateAPIView):
    serializer_class = ClaimActionTransactionSerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [UserRateThrottle]

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

    def create(self, request):
        user = self.request.user
        user_role = getattr(user, 'role', None)
        if user_role != 'CLIENT' and user_role != 'FINAL_USER':
            if not self.request.query_params.get('user'):
                return Response({ "error": "No allowed" }, status=status.HTTP_403_FORBIDDEN)
            target_id = self.request.query_params.get('user')
        else:
            target_id = user.pk

        try:
            target_user = USER_MODEL.objects.get(pk=target_id)
        except USER_MODEL.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        transaction_svc = TransactionService(user=target_user, company_profile=target_user.profile.company)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data.copy()
        instance = transaction_svc.create_instance(
            data_for=data['data_for'],
            account=data['account'],
            account_name=data['account_name'],
            account_number=data['account_number'],
            account_type=data['account_type'],
            activity=data['activity'],
            quantity=data['quantity'],
            amount=data['amount'],
            cost_per_stock=data['amount'] / Decimal(data['quantity']),
            description=data['description'],
            notes=data['notes'],
            symbol=data['symbol'],
            trade_date=datetime.fromisoformat(data['trade_date'])
        )
        transaction_svc.insert_objects([instance])
        transaction_svc.process_bulk()
        return Response(instance, status=status.HTTP_201_CREATED)


class ClaimActionTransactionDetailView(generics.RetrieveAPIView):
    serializer_class = ClaimActionTransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [UserRateThrottle]

    def get_queryset(self):
        """
        Sobrescribimos para asegurar que el usuario solo pueda
        acceder/editar/borrar SUS PROPIAS transacciones.
        """
        user = self.request.user
        if not user.is_authenticated:
            return ClaimActionTransaction.objects.none()
        
        user_role = getattr(user, "role", None) 
        if user.is_superuser or user_role == "SUPER_USER":
            return ClaimActionTransaction.objects.all()

        if user_role in ("COMPANY_ADMIN", "COMPANY_MANAGER"):
            return ClaimActionTransaction.objects.filter(user__company=user.company)

        return ClaimActionTransaction.objects.filter(user=user)
    
    # def retrieve(self, request, *args, **kwargs):
    #     instance = self.get_object()
    #     data = self.get_serializer(instance).data

    #     user = instance.user
    #     data["user"] = user.id 
    #     company = getattr(user.profile, "company", None)
    #     if company:
    #         data["company"] = company.id
    #     return Response(data)



class ImportTransactionsDataView(APIView):
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [UserRateThrottle]

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
        warnings_imports = {}
        company_profile = self.request.user.profile.company
        try:
            transaction_svc = TransactionService(user=user_for_import, company_profile=company_profile)
            file_svc = FileStockHandler(file_obj)
            _, header_idx = file_svc.create_iter()
            batch_size = 1000
            objects = []
            oldest_symbols = file_svc.oldest_symbols()
            symbols = []
            for symbol in oldest_symbols:
                old_activity_row = oldest_symbols[symbol][header_idx["Activity"]]
                validated = transaction_svc.validate_oldest_buy(symbol, old_activity_row)
                if not validated:
                    warnings_imports[symbol] = "There is no initial purchase for this symbol"
                    continue
                symbols.append(symbol)

            for row in file_svc.rows_by_symbols(symbols):
                try:
                    cost_per_stock = Decimal(row[header_idx['Amount']]) / Decimal(row[header_idx['Quantity']])
                    obj = transaction_svc.create_instance(
                        data_for=row[header_idx['Data For']],
                        trade_date=row[header_idx['Trade Date']],
                        account=row[header_idx['Account']],
                        account_name=row[header_idx['Account Name']],
                        account_type=row[header_idx['Account Type']],
                        account_number=row[header_idx['Account Number']],
                        activity=row[header_idx['Activity']],
                        description=row[header_idx['Description']],
                        symbol=row[header_idx['Symbol']],
                        quantity=row[header_idx['Quantity']],
                        cost_per_stock=cost_per_stock,
                        amount=row[header_idx['Amount']],
                        notes=row[header_idx['Notes']]
                    )
                    objects.append(obj)
                    if len(objects) >= batch_size:
                        transaction_svc.insert_objects(objects)
                        successful_imports += len(objects)
                        objects.clear()

                except Exception as e:
                    failed_imports += 1   

            if objects:
                transaction_svc.insert_objects(objects)
                successful_imports += len(objects)
                objects.clear()

            warnings_process = transaction_svc.process_bulk()

            return Response({
                "message": "Processing complete.",
                "import_job_id": current_job_id,
                "successful_imports": successful_imports,
                "failed_imports": failed_imports,
                "warnings_imports": warnings_imports,
                "warnings_process": warnings_process
            }, status=status.HTTP_202_ACCEPTED)
        except Exception as e:
            return Response({'error': f"Error processing file: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ImportLogListView(generics.ListAPIView):
    serializer_class = ImportLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    throttle_classes = [UserRateThrottle]

    def get_queryset(self):
        job_id = self.kwargs['job_id']
        return ImportLog.objects.filter(import_job_id=job_id).order_by('row_number')


class UserImportJobsView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [UserRateThrottle]

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
    throttle_classes = [UserRateThrottle]

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
    throttle_classes = [UserRateThrottle]

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return ClaimAction.objects.none()
        # Listar solo claims cuyos usuarios son gestionados por el manager en sesión
        return ClaimAction.objects.filter(user__managed_by=self.request.user)
