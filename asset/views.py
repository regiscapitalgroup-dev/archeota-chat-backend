from .models import Asset, AssetCategory
from .serializers import (
    AssetCategorySerializer,
    AssetCategoryBasicSerializer,
    AssetSerializer,
    CategoryWithAssetsSerializer,
)

from rest_framework.response import Response
from rest_framework import status, generics, permissions
from django.db.models import Prefetch
from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.auth import get_user_model
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle

USER_MODEL = get_user_model()


class AssetListCreateView(generics.ListCreateAPIView):
    serializer_class = AssetSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['category']
    throttle_classes = [UserRateThrottle]

    def get_queryset(self):
        request = self.request
        user_id = request.query_params.get('user_id')

        # Determine target user id: from query or default to session user
        if user_id is None or user_id == '':
            # Use authenticated session user
            if not request.user or not request.user.is_authenticated:
                return Asset.objects.none()
            target_user_id = request.user.id
        else:
            try:
                target_user_id = int(user_id)
            except (TypeError, ValueError):
                # If invalid user_id, fall back to session user when available
                if request.user and request.user.is_authenticated:
                    target_user_id = request.user.id
                else:
                    return Asset.objects.none()

        return Asset.objects.filter(owner_id=target_user_id).order_by('-asset_date')

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
    throttle_classes = [UserRateThrottle]
    
    def get_queryset(self):
        return Asset.objects.filter(owner=self.request.user)


class AssetCategoryListView(generics.ListAPIView):
    queryset = AssetCategory.objects.all().order_by('category_name')
    serializer_class = AssetCategorySerializer
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [UserRateThrottle]


class MyAssetCategoriesListView(generics.ListAPIView):
    serializer_class = AssetCategoryBasicSerializer
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [UserRateThrottle]

    def get_queryset(self):
        user = self.request.user
        if not user or not user.is_authenticated:
            return AssetCategory.objects.none()
        return (
            AssetCategory.objects.filter(asset__owner=user)
            .distinct()
            .order_by('category_name')
        )

class AssetsByCategoryView(generics.ListAPIView):
    serializer_class = CategoryWithAssetsSerializer
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [UserRateThrottle]

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