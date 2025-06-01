from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth import get_user_model
from django.conf import settings

User = get_user_model()

class CookieJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        access_token = request.COOKIES.get('access_token')
        if not access_token:
            # Fallback to Bearer token if cookie is absent
            return super().authenticate(request)
        
        try:
            validated_token = AccessToken(access_token)
            user_id = validated_token['user_id']
            user = User.objects.get(id=user_id)
            return (user, validated_token)
        except Exception as e:
            raise AuthenticationFailed(f'Authentication failed: {str(e)}')