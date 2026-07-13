from typing import List, Union
from fastapi import Depends
from app.models.user import UserRole, User
from app.core.utils.exceptions import InsufficientPermissionsException
# Note: get_current_user will be imported inside __call__ or dependencies dynamically to avoid circular imports.

class RoleBasedAccessChecker:
    """
    FastAPI dependency that restricts endpoint access to specified roles.
    """
    def __init__(self, allowed_roles: List[Union[UserRole, str]]):
        # Normalize inputs to enum
        self.allowed_roles = [
            role if isinstance(role, UserRole) else UserRole(role) 
            for role in allowed_roles
        ]

    def __call__(self, current_user: User) -> User:
        """
        Validates if the current user's role is within the allowed roles.
        """
        if current_user.role not in self.allowed_roles:
            raise InsufficientPermissionsException(
                message=f"Insufficient permissions. Role '{current_user.role.value}' does not have access."
            )
        return current_user
