# SPDX-License-Identifier: MPL-2.0

from pyqcrbox import msg_specs, sql_models

from .base import process_message

__all__ = []


@process_message.register
def _(msg: msg_specs.RegisterApplication) -> msg_specs.QCrBoxGenericResponse:
    """
    Register a new application and store it in the database
    """
    app_spec = sql_models.ApplicationCreate(**msg.payload.application_spec.model_dump())
    app_spec_db = app_spec.save_to_db(private_routing_key=msg.payload.private_routing_key)
    assigned_application_id = app_spec_db.id

    return msg_specs.RegisterApplicationResponse(
        response_to=msg.action,
        status="success",
        msg=f"Successfully registered application {app_spec_db.name!r} (id: {app_spec_db.id})",
        payload=msg_specs.RegisterApplicationResponse.Payload(
            application_id=assigned_application_id,
        ),
    )
