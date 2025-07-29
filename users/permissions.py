from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsCompanyAdministrator(BasePermission):
    """
    Permite el acceso solo a usuarios con el rol de Company Administrator.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'COMPANY_ADMIN'

class IsCompanyManager(BasePermission):
    """
    Permite el acceso solo a usuarios con el rol de Company Manager.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'COMPANY_MANAGER'

class CanManageUserObject(BasePermission):
    """
    Permiso a nivel de objeto para verificar si un usuario puede gestionar a otro.
    - Un manager puede ver/editar a un usuario que él directamente gestiona.
    - Un admin puede ver/editar a los managers que gestiona y a los usuarios de esos managers.
    """
    def has_object_permission(self, request, view, obj):
        # El super admin puede hacer todo
        if request.user.is_superuser:
            return True
        
        # El usuario que hace la petición debe ser el manager directo del objeto (usuario)
        if obj.managed_by == request.user:
            return True
        
        # Un Company Admin puede gestionar a los usuarios de sus managers
        if request.user.role == 'COMPANY_ADMIN' and obj.managed_by and obj.managed_by.managed_by == request.user:
            return True

        return False
