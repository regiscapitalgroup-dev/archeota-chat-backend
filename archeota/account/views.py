from rest_framework import generics, status # Para vistas genéricas
from rest_framework.permissions import AllowAny # Permitir acceso sin autenticación
from rest_framework_simplejwt.views import TokenObtainPairView
from .models import CustomUser # Importa tu modelo
from .serializers import UserRegistrationSerializer, MyTokenObtainPairSerializer # Importa el nuevo serializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.response import Response

class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer


class UserRegistrationView(generics.CreateAPIView):
    """
    Vista para registrar (crear) nuevos usuarios.
    Devuelve tokens JWT (access y refresh) junto con los datos del usuario al registrarse.
    """
    queryset = CustomUser.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny] # Permite a cualquiera acceder a esta vista

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True) # Valida y lanza error si no es válido
        
        # Llama al método create del serializer, que usa CustomUser.objects.create_user()
        # y devuelve la instancia del usuario.
        user = serializer.save() # Esto llama a UserRegistrationSerializer.create()

        # Generar tokens JWT para el usuario recién creado
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)

        # Preparamos los datos del usuario para la respuesta.
        # Usamos el mismo serializer para obtener los datos del usuario que se deben mostrar.
        # El serializer por defecto no incluirá 'password' debido a write_only=True.
        user_data = UserRegistrationSerializer(user, context=self.get_serializer_context()).data
        # Por si acaso, nos aseguramos de no enviar la contraseña (aunque write_only debería cubrirlo)
        user_data.pop('password', None)


        # Construir la respuesta final
        response_data = {
            'refresh': refresh_token,
            'access': access_token,
            'user': user_data # Incluimos los datos del usuario
        }

        # Usamos los headers de la respuesta original de éxito de CreateModelMixin
        headers = self.get_success_headers(serializer.data)
        
        return Response(response_data, status=status.HTTP_201_CREATED, headers=headers)

