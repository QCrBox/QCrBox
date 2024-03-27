import pydantic


def action_does_not_match(exc: pydantic.ValidationError):
    def is_action_mismatch_error(err_dict):
        return err_dict["loc"] == ("action",) and err_dict["type"] == "value_error.const"

    assert isinstance(exc, pydantic.ValidationError)
    return [] != [err_dict for err_dict in exc.errors() if is_action_mismatch_error(err_dict)]
