from django.shortcuts import render
from rest_framework.views import generics, status
from rest_framework.response import Response
from .models import User, UserProfile
from rest_framework.permissions import IsAuthenticated
from .serializers import UserSerializer, UserWithProfileSerializer, UserRegistrationSerializer, UserProfileSerializer


class RegisterView(generics.CreateAPIView):
    """Представление для регистрации нового пользователя."""
    query_set = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = []



class ProfileView(generics.RetrieveUpdateAPIView):
    """Представление для получения и обновления профиля пользователя."""
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

class ProfileUpdateView(generics.UpdateAPIView):
    """Представление для обновления профиля пользователя."""
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]
    def get_object(self):
        profile, created = UserProfile.objects.get_or_create(user=self.request.user)
        return profile