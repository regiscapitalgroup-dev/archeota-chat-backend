from rest_framework import serializers
from django.db.models import Sum
from users.serializers import UserSerializer
from .models import ActionsHoldings, ClaimAction, ClaimActionTransaction, ImportLog, ClassActionLawsuit
from django.contrib.auth import get_user_model

USER_MODEL = get_user_model()


class HoldingSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActionsHoldings
        fields = '__all__'
        read_only_fields = ('user',)

class ClassActionLawsuitSerializer(serializers.ModelSerializer):
    holding = HoldingSerializer(read_only=True)
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = ClassActionLawsuit
        fields = '__all__'
        read_only_fields = ('user',)
    
    def validate(self, data):
        qty = data.get("quantity_stock")
        value = data.get("value_per_stock")

        if qty is not None and value is not None:
            data["amount"] = qty * value

        return data

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
    class_actions_lawsuits = ClassActionLawsuitSerializer(
        many=True,
        read_only=True
    )

    class Meta:
        model = ClaimAction
        fields = '__all__'
        read_only_fields = ('user',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        request = self.context.get('request')
        if not request:
            return

        user = request.user
        user_role = getattr(user, 'role', None)
        if user_role in ('FINAL_USER', 'CLIENT'):
            self.fields.pop('class_actions_lawsuits', None)

class ClaimActionTransactionSerializer(serializers.ModelSerializer):
    costPerStock = serializers.DecimalField(
        max_digits=24,
        decimal_places=4,
        required=False 
    )
    class Meta:
        model = ClaimActionTransaction
        fields = '__all__'
        read_only_fields = ('user', 'cost_per_stock')

class ImportLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImportLog
        fields = ['id', 'status', 'row_number', 'error_message', 'row_data', 'created_at']


class ErrorLogDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImportLog
        fields = ['row_number', 'error_message', 'row_data']
