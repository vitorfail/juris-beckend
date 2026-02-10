from fastapi import HTTPException, status

class CustomHTTPException(HTTPException):
    def __init__(self, detail: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(status_code=status_code, detail=detail)

# Exceções específicas
class UserNotFoundException(CustomHTTPException):
    def __init__(self):
        super().__init__("Usuário não encontrado", status.HTTP_404_NOT_FOUND)

class InvalidCredentialsException(CustomHTTPException):
    def __init__(self):
        super().__init__("Credenciais inválidas", status.HTTP_401_UNAUTHORIZED)

class InsufficientPermissionsException(CustomHTTPException):
    def __init__(self):
        super().__init__("Permissões insuficientes", status.HTTP_403_FORBIDDEN)