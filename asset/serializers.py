from rest_framework import serializers
from .models import AssetCategory, Asset, ClaimAction, ClaimActionTransaction, ImportLog
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
        required=False, # Permite que sea nulo
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


class FileUploadSerializer(serializers.Serializer):
    file = serializers.FileField()
    target_user_id = serializers.IntegerField(required=False, allow_null=True)

    def validate_file(self, value):
        valid_extensions = ['csv', 'xlsx', 'xls']
        ext = value.name.split('.')[-1]
        if ext.lower() not in valid_extensions:
            raise serializers.ValidationError(f"Unsupported extension. Upload a file {', '.join(valid_extensions)}.")
        return value
    
    def validate_target_user_id(self, value):
        if value is not None:
            try:
                CustomUser.objects.get(pk=value)
            except CustomUser.DoesNotExist:
                raise serializers.ValidationError(f"The user with ID {value} does not exist.")
        return value    


class ClaimActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClaimAction
        fields = '__all__' 


class ClaimActionTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClaimActionTransaction
        fields = '__all__'


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


class ImportLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImportLog
        fields = ['id', 'status', 'row_number', 'error_message', 'row_data', 'created_at']


class ErrorLogDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImportLog
        fields = ['row_number', 'error_message', 'row_data']
