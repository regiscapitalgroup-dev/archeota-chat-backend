from .models import Asset, AssetCategory, ClaimActionTransaction
from .serializers import AssetCategorySerializer, AssetCategory, AssetSerializer, FileUploadSerializer
#from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser 
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework import status, generics, permissions, viewsets
from django.db import transaction
import pandas as pd
import numpy as np


class AssetCategoryListView(viewsets.ModelViewSet):
    queryset = AssetCategory.objects.all().order_by('category_name')
    serializer_class = AssetCategorySerializer
    permission_classes = [permissions.AllowAny]


class AssetViewSet(viewsets.ModelViewSet):
    serializer_class = AssetSerializer
    permission_classes = [permissions.IsAuthenticated] # Solo usuarios autenticados pueden acceder

    def get_queryset(self):
        user = self.request.user
        return Asset.objects.filter(owner=user).order_by('-asset_date')

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class ImportDataView(generics.GenericAPIView):
    serializer_class = FileUploadSerializer
    parser_classes = [MultiPartParser, FormParser]

    @transaction.atomic # Envuelve toda la operación en una transacción
    def post(self, request, *args, **kwargs):
        serializer = FileUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        file_obj = serializer.validated_data['file']
        
        try:
            # Determinar el tipo de archivo y leerlo con Pandas
            if file_obj.name.endswith('.csv'):
                df = pd.read_csv(file_obj)
            elif file_obj.name.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(file_obj)
            else:
                # Esta validación ya está en el serializer, pero es bueno tenerla aquí también
                return Response({'error': 'Formato de archivo no soportado.'}, status=status.HTTP_400_BAD_REQUEST)
            
            df = df.fillna(0.00, inplace=False)
            #df['Quantity'] = df['Quantity'].apply(lambda x: '{:.2f}'.format(x))
            #df['Amount'] = df['Amount'].apply(lambda x: '{:.2f}'.format(x))
            


            # --- Lógica de Procesamiento ---
            errors = []
            imported_count = 0
            
            # Itera sobre cada fila del DataFrame de Pandas
            for index, row in df.iterrows():
                try:
                    # Aquí mapeas las columnas del archivo a los campos de tu modelo
                    # Es CRUCIAL limpiar los datos (ej. row['columna'].strip())
                    # y manejar valores nulos (ej. None si row['columna'] es NaN)
                    #row['Quantity'] #= pd.to_numeric(row['Quantity'].str.replace(',', ''), errors='coerce')
                    #row['Amount'] = pd.to_numeric(row['Amount'].str.replace(',', ''), errors='coerce')
                    # row['Quantity'] = row['Quantity'].replace(np.nan, 0)
                    # row['Amount'] = row['Amount'].replace(np.nan, 0)

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
                        user='User',
                    )
                    imported_count += 1

                except Exception as e:
                    # Captura errores por fila para dar un reporte más detallado
                    errors.append(f"Fila {index + 2}: {str(e)}")

            if errors:
                # Si hubo errores, puedes decidir si quieres deshacer toda la operación
                # o simplemente reportarlos. Gracias a @transaction.atomic, si ocurre
                # una excepción no controlada aquí, todo se revierte.
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
            # Error general al procesar el archivo
            return Response({'error': f"Error procesando el archivo: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
