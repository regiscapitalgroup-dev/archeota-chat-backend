from rest_framework import serializers
from .models import ClaimAction, ClaimActionTransaction, ImportLog
from django.contrib.auth import get_user_model

USER_MODEL = get_user_model()


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
                USER_MODEL.objects.get(pk=value)
            except USER_MODEL.DoesNotExist:
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

class ImportLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImportLog
        fields = ['id', 'status', 'row_number', 'error_message', 'row_data', 'created_at']


class ErrorLogDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImportLog
        fields = ['row_number', 'error_message', 'row_data']
