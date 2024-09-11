from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING

import nats.js.errors

from pyqcrbox.sql_models import ApplicationSpecDB

from .helper_functions import get_nats_key_value

if TYPE_CHECKING:
    from pyqcrbox.sql_models import ApplicationSpec


class BasePersistenceAdapter(metaclass=ABCMeta):
    @abstractmethod
    async def save_application_spec(self, application_spec: "ApplicationSpec") -> None:
        pass


class NatsPersistenceAdapter(BasePersistenceAdapter):
    async def save_application_spec(self, application_spec: "ApplicationSpec") -> None:
        kv_applications = await get_nats_key_value(bucket="applications")
        nats_key = application_spec.nats_key
        try:
            existing_application_spec = await kv_applications.get(nats_key)
            print(
                "TODO: an application with the same slug and version was registered before. "
                f"Verify that the new spec is consistent with the existing one: {existing_application_spec=}"
            )
            return
        except nats.js.errors.KeyNotFoundError:
            pass

        nats_value = application_spec.model_dump_json().encode()
        await kv_applications.put(nats_key, nats_value)


class SQLitePersistenceAdapter(BasePersistenceAdapter):
    async def save_application_spec(self, application_spec: "ApplicationSpec") -> None:
        application_spec_db = ApplicationSpecDB.from_pydantic_model(application_spec)
        application_spec_db.save_to_db()
