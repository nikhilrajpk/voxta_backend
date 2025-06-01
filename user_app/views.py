from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated
from .serializers import RegisterSerializer, UserSerializer, CustomTokenObtainPairSerializer, InterestRequestSerializer, MessageSerializer
from django.contrib.auth import get_user_model
from .models import InterestRequest, Message
from django.db import models
from rest_framework_simplejwt.views import TokenObtainPairView

User = get_user_model()

class RegisterView(APIView):
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            response = Response({
                'user': UserSerializer(user).data,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }, status=status.HTTP_201_CREATED)
            response.set_cookie(
                'refresh_token',
                str(refresh),
                httponly=True,
                secure=False,
                samesite='None',
                max_age=24*60*60,
                path='/',
                domain='localhost',
            )
            response.set_cookie(
                'access_token',
                str(refresh.access_token),
                httponly=True,
                secure=False,
                samesite='None',
                max_age=60*60,
                path='/',
                domain='localhost',
            )
            return response
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        refresh = response.data['refresh']
        access = response.data['access']
        res = Response(response.data, status=status.HTTP_200_OK)
        res.set_cookie(
            'access_token',
            access,
            httponly=True,
            secure=False,
            samesite='None',
            max_age=60*60,  # 1 hour
            path='/',
            domain='localhost',
        )
        res.set_cookie(
            'refresh_token',
            refresh,
            httponly=True,
            secure=False,
            samesite='None',
            max_age=24*60*60,  # 1 day
            path='/',
            domain='localhost',
        )
        return res

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            refresh_token = request.COOKIES.get('refresh_token')
            if not refresh_token:
                response = Response({"message": "No refresh token provided"}, status=status.HTTP_400_BAD_REQUEST)
                response.delete_cookie('access_token', path='/', domain='localhost')
                response.delete_cookie('refresh_token', path='/', domain='localhost')
                return response
            token = RefreshToken(refresh_token)
            token.blacklist()
            response = Response({"message": "Logout successful"}, status=status.HTTP_205_RESET_CONTENT)
            response.delete_cookie('access_token', path='/', domain='localhost')
            response.delete_cookie('refresh_token', path='/', domain='localhost')
            return response
        except Exception as e:
            response = Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)
            response.delete_cookie('access_token', path='/', domain='localhost')
            response.delete_cookie('refresh_token', path='/', domain='localhost')
            return response

class CheckAuthView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data, status=status.HTTP_200_OK)
    
    
class UserListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    def get_queryset(self):
        return User.objects.exclude(id=self.request.user.id)


class InterestRequestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = InterestRequestSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            if serializer.validated_data['receiver'] == request.user:
                return Response({"error": "Cannot send interest to yourself"}, status=status.HTTP_400_BAD_REQUEST)
            if InterestRequest.objects.filter(sender=request.user, receiver=serializer.validated_data['receiver']).exists():
                return Response({"error": "Interest request already sent"}, status=status.HTTP_400_BAD_REQUEST)
            serializer.save(sender=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request):
        interest_type = request.query_params.get('type', 'received')
        if interest_type == 'sent':
            interests = InterestRequest.objects.filter(sender=request.user)
        else:
            interests = InterestRequest.objects.filter(receiver=request.user)
        serializer = InterestRequestSerializer(interests, many=True)
        return Response(serializer.data)

    def patch(self, request, pk):
        try:
            interest = InterestRequest.objects.get(pk=pk, receiver=request.user)
            action = request.data.get('action')
            if action not in ['accept', 'reject']:
                return Response({"error": "Invalid action"}, status=status.HTTP_400_BAD_REQUEST)
            interest.status = 'accepted' if action == 'accept' else 'rejected'
            interest.save()
            serializer = InterestRequestSerializer(interest)
            return Response(serializer.data)
        except InterestRequest.DoesNotExist:
            return Response({"error": "Interest request not found"}, status=status.HTTP_404_NOT_FOUND)
        
class ConnectedUsersView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Get accepted interests (sent or received)
        sent_accepted = InterestRequest.objects.filter(
            sender=request.user, status='accepted'
        ).select_related('receiver')
        received_accepted = InterestRequest.objects.filter(
            receiver=request.user, status='accepted'
        ).select_related('sender')

        # Collect unique connected users
        connected_users = set()
        for interest in sent_accepted:
            connected_users.add(interest.receiver)
        for interest in received_accepted:
            connected_users.add(interest.sender)

        serializer = UserSerializer(connected_users, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
class MessageHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        # Verify mutual connection
        if not (InterestRequest.objects.filter(
                sender_id=request.user.id, receiver_id=user_id, status='accepted'
            ).exists() or InterestRequest.objects.filter(
                sender_id=user_id, receiver_id=request.user.id, status='accepted'
            ).exists()):
            return Response({"error": "No mutual connection"}, status=status.HTTP_403_FORBIDDEN)

        # Get messages between the two users
        messages = Message.objects.filter(
            models.Q(sender=request.user, receiver_id=user_id) |
            models.Q(sender_id=user_id, receiver=request.user)
        ).order_by('timestamp')
        serializer = MessageSerializer(messages, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)