from rest_framework import serializers
from .models import AssetCategory, Asset
from django.contrib.auth import get_user_model


CustomUser = get_user_model()


class AssetCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetCategory
        fields = ['id', 'category_name', 'attributes']


class AssetSerializer(serializers.ModelSerializer):
    owner_username = serializers.CharField(source='owner.username', read_only=True)
    category_details = AssetCategorySerializer(source='category', read_only=True)
    category = serializers.PrimaryKeyRelatedField(
        queryset=AssetCategory.objects.all(), 
        write_only=True,
        required=False,
        allow_null=True
    )    

    class Meta:
        model = Asset
        fields = [
            'id', 
            'owner_username', 
            'name',
            'acquisition_value',
            'estimated_value',
            'low_value',
            'high_value',
            'photo',
            'syntasis_summary',
            'full_conversation_history',
            'category',
            'category_details',
            'attributes',
            'asset_date',
        ]
        read_only_fields = ['asset_date', 'owner_username']





class AssetDetailNestedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        fields = ['id', 'name', 'acquisition_value', 'estimated_value', 'low_value', 
                'high_value', 'photo', 'syntasis_summary', 'full_conversation_history', 'attributes']


class CategoryWithAssetsSerializer(serializers.ModelSerializer):
    category = serializers.CharField(source='category_name')
    assets = AssetDetailNestedSerializer(many=True, read_only=True)

    class Meta:
        model = AssetCategory
        fields = ['category', 'assets']


