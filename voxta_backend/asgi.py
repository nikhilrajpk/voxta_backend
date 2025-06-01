import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'voxta_backend.settings')

django_asgi_app = get_asgi_application()

# Import routing and middleware after Django is initialized
from channels.security.websocket import AllowedHostsOriginValidator
from user_app.middleware import TokenAuthMiddlewareStack
from user_app import routing

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    "websocket": AllowedHostsOriginValidator(
        TokenAuthMiddlewareStack( 
            URLRouter(
                routing.websocket_urlpatterns
            )
        )
    ),
})