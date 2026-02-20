from django.contrib.auth import authenticate
from rest_framework import serializers

from ..models import User


class RegisterSerializer(serializers.Serializer):
    """Validate and create a new inactive user."""
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    confirmed_password = serializers.CharField(write_only=True, min_length=8)

    def validate(self, attrs):
        if attrs["password"] != attrs["confirmed_password"]:
            raise serializers.ValidationError(
                "Please check your input and try again.")
        if User.objects.filter(email__iexact=attrs["email"]).exists():
            raise serializers.ValidationError(
                "Please check your input and try again.")
        return attrs

    def create(self, validated_data):
        email = validated_data["email"].lower().strip()
        user = User.objects.create_user(
            username=email,
            email=email,
            password=validated_data["password"],
            is_active=False,
        )
        return user


class LoginSerializer(serializers.Serializer):
    """Authenticate user by email and password."""
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs["email"].lower().strip()
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            raise serializers.ValidationError(
                "Please check your input and try again.")

        user = authenticate(username=user.username, password=attrs["password"])
        if not user or not user.is_active:
            raise serializers.ValidationError(
                "Please check your input and try again.")

        attrs["user"] = user
        return attrs


class UserPublicSerializer(serializers.ModelSerializer):
    """Public payload for responses."""
    class Meta:
        model = User
        fields = ("id", "username", "email")
