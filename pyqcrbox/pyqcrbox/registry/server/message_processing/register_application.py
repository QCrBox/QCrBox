from pyqcrbox import db_helpers, logger, msg_specs, settings, sql_models

from .base_message_dispatcher import server_side_message_dispatcher


@server_side_message_dispatcher.register
def handle_application_registration_request(msg: msg_specs.RegisterApplication, **kwargs):
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
