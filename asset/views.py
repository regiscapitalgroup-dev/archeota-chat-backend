from .models import Asset, AssetCategory
from .serializers import (
    AssetCategorySerializer,
    AssetSerializer,
    CategoryWithAssetsSerializer,
)

from rest_framework.response import Response
from rest_framework import status, generics, permissions
from django.db.models import Prefetch
from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.auth import get_user_model


USER_MODEL = get_user_model()


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