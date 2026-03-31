"""Port interfaces — abstract contracts for infrastructure adapters."""

from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.models import ActivationCode, User


class DuplicateEntryError(Exception):
    """Raised by a repository when a unique constraint is violated."""

    def __init__(self, field: str = "unknown") -> None:
        super().__init__(f"Duplicate entry for field: {field}")
        self.field = field


class UserRepository(ABC):
    @abstractmethod
    async def create(self, email: str, password_hash: str, lang: str) -> User: ...

    @abstractmethod
    async def get_by_email(self, email: str) -> User | None: ...

    @abstractmethod
    async def activate(self, user_id: UUID) -> None: ...


class ActivationCodeRepository(ABC):
    @abstractmethod
    async def create(self, user_id: UUID, code: str, ttl_seconds: int) -> ActivationCode: ...

    @abstractmethod
    async def claim_active_code(self, user_id: UUID, code: str) -> ActivationCode | None:
        """Atomically mark a valid (non-expired, non-used) code as used and return it.

        Returns None if no matching active code exists.
        """
        ...

    @abstractmethod
    async def get_expired_code(self, user_id: UUID, code: str) -> ActivationCode | None: ...

    @abstractmethod
    async def invalidate_all(self, user_id: UUID) -> None: ...

    @abstractmethod
    async def record_failed_attempt(self, user_id: UUID, max_attempts: int) -> bool:
        """Increment failed_attempts on all active codes for user_id.

        Returns True if the attempt count has reached max_attempts (locked).
        """
        ...


class EmailService(ABC):
    @abstractmethod
    async def check_connectivity(self) -> None: ...

    @abstractmethod
    async def send_activation_code(self, email: str, code: str, validity_minutes: int, lang: str) -> None: ...

    @abstractmethod
    async def close(self) -> None: ...
