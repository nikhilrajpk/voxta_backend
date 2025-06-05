from urllib.parse import parse_qs
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import get_user_model
from django.db import close_old_connections
from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async
import jwt
from django.conf import settings
import logging

User = get_user_model()
logger = logging.getLogger(__name__)

@database_sync_to_async
def get_user_from_token(token):
    """
    Get user from JWT token
    """
    try:
        # Decode the JWT token
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
        user_id = payload.get('user_id')
        if user_id:  # Fixed indentation here
            user = User.objects.get(id=user_id)
            logger.info(f"Successfully authenticated user: {user.username} (ID: {user_id})")
            return user
    except jwt.ExpiredSignatureError:
        logger.warning("JWT token has expired")
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid JWT token: {str(e)}")
    except User.DoesNotExist:
        logger.warning(f"User with id {user_id} does not exist")
    except Exception as e:
        logger.error(f"Error decoding JWT token: {str(e)}")
    
    return AnonymousUser()

class TokenAuthMiddleware(BaseMiddleware):
    """
    Custom middleware to authenticate WebSocket connections using JWT tokens
    """
    def __init__(self, inner):  # Fixed method name
        self.inner = inner

    async def __call__(self, scope, receive, send):  # Fixed method name
        close_old_connections()
        
        # Extract token from query string
        query_string = scope.get('query_string', b'').decode()
        logger.info(f"WebSocket connection attempt - Query string: {query_string}")
        query_params = parse_qs(query_string)
        token = query_params.get('token', [None])[0]
        
        if token:
            logger.info(f"Extracted token: {token[:20]}..." if len(token) > 20 else token)
            scope['user'] = await get_user_from_token(token)
            if scope['user'].is_authenticated:
                logger.info(f"WebSocket authenticated user: {scope['user'].username}")
            else:
                logger.warning("Token provided but authentication failed")
        else:
            scope['user'] = AnonymousUser()
            logger.warning("No token provided in WebSocket connection")
        
        return await self.inner(scope, receive, send)

def TokenAuthMiddlewareStack(inner):
    """
    Middleware stack for token authentication
    """
    return TokenAuthMiddleware(inner)