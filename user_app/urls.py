from django.urls import path
from .views import RegisterView, CustomTokenObtainPairView, LogoutView, CheckAuthView, UserListView, InterestRequestView, ConnectedUsersView, MessageHistoryView

urlpatterns = [
    path('auth/register', RegisterView.as_view(), name='register'),
    path('auth/login', CustomTokenObtainPairView.as_view(), name='login'),
    path('auth/logout', LogoutView.as_view(), name='logout'),
    path('auth/check-auth', CheckAuthView.as_view(), name='check-auth'),
    path('users/', UserListView.as_view(), name='user_list'),
    path('interests/', InterestRequestView.as_view(), name='interest_request'),
    path('interests/<int:pk>/', InterestRequestView.as_view(), name='interest_request_detail'),
    
    path('connected-users/', ConnectedUsersView.as_view(), name='connected_users'),
    path('messages/<int:user_id>/', MessageHistoryView.as_view(), name='message_history'),
]