from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Request

User = get_user_model()


# ----------------------------
# User Serializer
# ----------------------------
class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, min_length=6)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'role']
        read_only_fields = ['id']

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User.objects.create_user(**{**validated_data, 'password': password})
        return user


# ----------------------------
# Login Serializer
# ----------------------------
class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)


# ----------------------------
# Request Serializer
# ----------------------------
class RequestSerializer(serializers.ModelSerializer):
    created_by = serializers.ReadOnlyField(source='created_by.username')
    approved_by = serializers.ReadOnlyField(source='approved_by.username')
    proforma = serializers.FileField(required=False, allow_null=True, use_url=True)
    purchase_order = serializers.FileField(required=False, allow_null=True, use_url=True)
    receipt = serializers.FileField(required=False, allow_null=True, use_url=True)

    class Meta:
        model = Request
        fields = [
            'id', 'title', 'description', 'amount', 'status',
            'created_by', 'approved_by',
            'proforma', 'purchase_order', 'receipt',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'status', 'created_by', 'approved_by', 'created_at', 'updated_at']


    def get_purchase_order(self, obj):
        if obj.purchase_order:
            return obj.purchase_order.url  
        return None
