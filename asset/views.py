from .models import Asset, AssetCategory, ClaimActionTransaction, ClaimAction
from .serializers import (AssetCategorySerializer, AssetCategory, AssetSerializer, FileUploadSerializer, 
       ClaimActionTransactionSerializer, ClaimActionSerializer)
from rest_framework.parsers import MultiPartParser, FormParser 
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework import status, generics, permissions
from django.db import transaction
import pandas as pd
from .pagination import StandardResultsSetPagination 
from django_filters.rest_framework import DjangoFilterBackend


class AssetListCreateView(generics.ListCreateAPIView):
    serializer_class = AssetSerializer
    permission_classes = [permissions.IsAuthenticated]

    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['category']    

    def get_queryset(self):
        return Asset.objects.filter(owner=self.request.user).order_by('-asset_date')

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


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
            return ClaimActionTransaction.objects.all().order_by('-trade_date', 'pk') #filter(user=self.request.user)
        return ClaimActionTransaction.objects.none()


class ImportDataView(generics.GenericAPIView):
    serializer_class = FileUploadSerializer
    parser_classes = [MultiPartParser, FormParser]

    @transaction.atomic 
    def post(self, request, *args, **kwargs):
        serializer = FileUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        file_obj = serializer.validated_data['file']
        
        try:
            if file_obj.name.endswith('.csv'):
                df = pd.read_csv(file_obj)
            elif file_obj.name.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(file_obj)
            else:
                return Response({'error': 'Formato de archivo no soportado.'}, status=status.HTTP_400_BAD_REQUEST)
            
            df = df.fillna(0.00, inplace=False)
            
            errors = []
            imported_count = 0
            
            for index, row in df.iterrows():
                try:
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
                        quantity=pd.to_numeric(str(row['Quantity']).replace(',', ''), downcast="float", errors='coerce'),
                        amount=pd.to_numeric(str(row['Amount']).replace(',', ''), downcast="float", errors='coerce'),
                        notes=row['Notes'],
                        type='Type',
                        company='Company',
                        user=self.request.user.email,
                    )
                    imported_count += 1

                except Exception as e:
                    errors.append(f"Fila {index + 2}: {str(e)}")

            if errors:
                return Response({
                    "status": "Importación completada con errores.",
                    "imported_count": imported_count,
                    "errors": errors
                }, status=status.HTTP_400_BAD_REQUEST)

            return Response({
                "status": "Archivo importado exitosamente.",
                "imported_count": imported_count
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({'error': f"Error procesando el archivo: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        