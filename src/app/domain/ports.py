"""Port interfaces — abstract contracts for infrastructure adapters."""

from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.models import ActivationCode, User


class UserRepository(ABC):
    @abstractmethod
    async def create(self, email: str, password_hash: str, lang: str) -> User: ...

    @abstractmethod
    async def get_by_email(self, email: str) -> User | None: ...

    @abstractmethod
    async def get_by_id(self, user_id: UUID) -> User | None: ...

    @abstractmethod
    async def activate(self, user_id: UUID) -> None: ...


class ActivationCodeRepository(ABC):
    @abstractmethod
    async def create(self, user_id: UUID, code: str, ttl_seconds: int) -> ActivationCode: ...

    @abstractmethod
    async def get_active_code(self, user_id: UUID, code: str) -> ActivationCode | None: ...

    @abstractmethod
    async def get_expired_code(self, user_id: UUID, code: str) -> ActivationCode | None: ...

    @abstractmethod
    async def mark_used(self, code_id: UUID) -> None: ...


class EmailService(ABC):
    @abstractmethod
    async def check_connectivity(self) -> None: ...

    @abstractmethod
    async def send_activation_code(self, email: str, code: str, validity_minutes: int, lang: str) -> None: ...

    @abstractmethod
    async def close(self) -> None: ...
