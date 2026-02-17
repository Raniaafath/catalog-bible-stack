import logging
from uuid import uuid4

from django.contrib.auth import authenticate, get_user_model
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.serializers import ValidationError
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from api.v1.serializers.auth import LoginSerializer, SignupSerializer, UserSerializer

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name="dispatch")
class LoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            data = request.data or {}
            serializer = LoginSerializer(data=data)
            serializer.is_valid(raise_exception=True)
            email = serializer.validated_data["email"].strip().lower()
            password = serializer.validated_data["password"]

            user_model = get_user_model()
            user_by_email = user_model.objects.filter(email__iexact=email).first()
            username = user_by_email.get_username() if user_by_email else email
            user = authenticate(request, username=username, password=password)

            if not user:
                return Response({"detail": "Invalid email or password."}, status=status.HTTP_400_BAD_REQUEST)

            token, _ = Token.objects.get_or_create(user=user)
            return Response({"token": token.key, "user": UserSerializer(user).data})
        except ValidationError:
            raise
        except Exception as exc:
            logger.exception("Login failed: %s", exc)
            return Response(
                {"detail": "Login failed. Please try again or contact support."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@method_decorator(csrf_exempt, name="dispatch")
class SignupView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].strip().lower()
        password = serializer.validated_data["password"]
        full_name = serializer.validated_data.get("full_name", "").strip()

        user_model = get_user_model()
        if user_model.objects.filter(email__iexact=email).exists():
            return Response({"detail": "An account with this email already exists."}, status=status.HTTP_400_BAD_REQUEST)

        username = email
        if user_model.objects.filter(username=username).exists():
            username = f"{email.split('@')[0]}-{uuid4().hex[:8]}"

        user = user_model.objects.create_user(username=username, email=email, password=password)
        if full_name:
            user.first_name = full_name
            user.save(update_fields=["first_name"])

        token, _ = Token.objects.get_or_create(user=user)
        return Response({"token": token.key, "user": UserSerializer(user).data}, status=status.HTTP_201_CREATED)


@method_decorator(csrf_exempt, name="dispatch")
class LogoutView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.auth:
            request.auth.delete()
        else:
            Token.objects.filter(user=request.user).delete()
        return Response({"detail": "Logged out."}, status=status.HTTP_200_OK)


class MeView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            return Response({"user": UserSerializer(request.user).data})
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error in MeView: {str(e)}", exc_info=True)
            return Response(
                {"detail": "Error retrieving user information."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
