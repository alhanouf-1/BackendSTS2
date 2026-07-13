from passlib.context import CryptContext

# Set up CryptContext for bcrypt hashing configuration
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class PasswordHasher:
    """Password Hashing and Verification Helper Wrappers."""
    
    @staticmethod
    def hash(password: str) -> str:
        """Hashes a plaintext password."""
        return pwd_context.hash(password)

    @staticmethod
    def verify(plain_password: str, hashed_password: str) -> bool:
        """Verifies a plaintext password against a hash."""
        return pwd_context.verify(plain_password, hashed_password)
