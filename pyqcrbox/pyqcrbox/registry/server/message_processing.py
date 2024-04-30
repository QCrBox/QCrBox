import functools
import textwrap

from pyqcrbox import logger, msg_specs, settings, sql_models

from . import db_helpers


@functools.singledispatch
def server_side_message_dispatcher(msg: dict):
    """
    Fallback processing definition.

    This is executed only if none of the other registered handlers match.
    """
    error_msg = textwrap.dedent(
        f"""
        Cannot process incoming message: {msg}.

        If it represents an action, make sure that:

        (1) there exists a submodule of `pyqcrbox.msg_specs.msg_types` which defines
        a subclass of QCrBoxBaseAction associated with this action (and this submodule
        is imported in `pyqcrbox/msg_specs/msg_types/__init__.py`)

        (2) there exists a submodule of `pyqcrbox.registry.{{server|client}}.message_processing`
        which defines a handler for this action (and this submodule is imported in
        `pyqcrbox/registry/{{server|client}}/message_processing/__init__.py
        """
    )
    logger.warning(error_msg)
    return msg_specs.responses.error(response_to="incoming_message", msg=error_msg)


@server_side_message_dispatcher.register
def handle_application_registration_request(msg: msg_specs.RegisterApplication):
    assert msg.action == "register_application"

    application_spec = msg.payload.application_spec
    app_slug = application_spec.slug
    app_version = application_spec.version
    logger.info(f"Registering application: {app_slug} (version: {app_version})")

    application_db = db_helpers.get_one_or_none(sql_models.ApplicationSpecDB, slug=app_slug, version=app_version)
    if application_db is None:
        application_db = sql_models.ApplicationSpecDB.from_pydantic_model(
            application_spec,
            private_routing_key=msg.payload.private_routing_key,
        )
        with settings.db.get_session() as session:
            session.add(application_db)
            session.commit()
            session.refresh(application_db)

    # assigned_application_id = application_db.id

    return msg_specs.responses.success(
        response_to=msg.action,
        # payload=msg_specs.PayloadForRegisterApplicationResponse(application_id=assigned_application_id),
    )


@server_side_message_dispatcher.register
def health_check(msg: msg_specs.HealthCheck):
    assert msg.action == "health_check"
    return msg_specs.responses.health_check_healthy()
