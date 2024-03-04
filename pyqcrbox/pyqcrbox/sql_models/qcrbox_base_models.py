import types
from abc import ABCMeta
from collections.abc import Iterable

import pydantic
from sqlmodel import SQLModel


class QCrBoxError(Exception):
    pass


def _is_qcrbox_pydantic_base_model(cls):
    return isinstance(cls, QCrBoxPydanticBaseModel)


def _model_dump_with_recursive_transformation(self, func, condition=None):
    condition = condition or _is_qcrbox_pydantic_base_model

    new_fields = {}
    for name, field_info in self.model_fields.items():
        field_value = getattr(self, name)
        new_fields[name] = _transform_field_recursively(self, field_info, field_value, func, condition)
    return func(self, new_fields)


def _transform_field_recursively(self, field_info, field_value, func, condition):
    assert isinstance(field_info, pydantic.fields.FieldInfo)

    if not isinstance(field_info.annotation, types.GenericAlias):
        return field_value
    else:
        cls_origin = field_info.annotation.__origin__
        if not issubclass(cls_origin, Iterable):
            return field_value
        else:

            def _apply_optionally(item, func, condition):
                if condition(item):
                    return _model_dump_with_recursive_transformation(item, func, condition)
                else:
                    return item

            return [_apply_optionally(item, func, condition) for item in field_value]


def _to_sql_model_impl(self, new_fields):
    try:
        qcrbox_sql_model_class = getattr(self, "__qcrbox_sql_model__")
        # if isinstance(qcrbox_sql_model_class, str):
        #     raise NotImplementedError
        #     caller_globals = inspect.currentframe().f_back.f_globals
        #     breakpoint()
        #     qcrbox_sql_model_class = caller_globals[qcrbox_sql_model_class]
        if not issubclass(qcrbox_sql_model_class, QCrBoxBaseSQLModel):
            raise QCrBoxError()
    except (AttributeError, KeyError, QCrBoxError) as exc:
        raise QCrBoxError(
            "Attribute '__qcrbox_sql_model__' must be defined on the model class and "
            f"refer to a valid subclass of QCrBoxBaseSQLModel. Original error: {exc!r}"
        )
    return qcrbox_sql_model_class(**new_fields)


class QCrBoxPydanticBaseModel(pydantic.BaseModel, metaclass=ABCMeta):
    """
    Base class for QCrBox pydantic models.
    """

    model_config = pydantic.ConfigDict(extra="forbid")

    # TODO: check that __qcrbox_sql_model__ is defined as a class attribute!

    # def to_sql_model(self):
    #     try:
    #         qcrbox_sql_model_class = getattr(self, "__qcrbox_sql_model__")
    #         if isinstance(qcrbox_sql_model_class, str):
    #             qcrbox_sql_model_class = globals()[qcrbox_sql_model_class]
    #         if not issubclass(qcrbox_sql_model_class, QCrBoxBaseSQLModel):
    #             raise QCrBoxError()
    #     except (AttributeError, KeyError, QCrBoxError) as exc:
    #         breakpoint()
    #         raise QCrBoxError(
    #             "Attribute '__qcrbox_sql_model__' must be defined on the model class and "
    #             f"refer to a valid subclass of QCrBoxBaseSQLModel. Original error: {exc}"
    #         )
    #     return qcrbox_sql_model_class(**self.model_dump())

    def to_sql_model(self):
        return _model_dump_with_recursive_transformation(self, func=_to_sql_model_impl)

    def _model_dump_with_recursive_transformation(self, func, condition=None):
        condition = condition or _is_qcrbox_pydantic_base_model

        new_fields = {}
        for name, field_info in self.model_fields.items():
            field_value = getattr(self, name)
            new_fields[name] = _transform_field_recursively(self, field_info, field_value, func, condition)
        return func(self, new_fields)

    # def _get_model_fields_that_need_traversing(self):
    #     """
    #     Return the names of model fields on this model that themselves represent lists of QCrBox models
    #     (and therefore need traversing).
    #     """
    #     return (name for (name, field) in self.model_fields.items() if _represents_list_of_qcrbox_models(field))
    #
    # def model_dump_with_transformation(self, func):
    #     def optionally_transform_value(name, field_info, value):
    #         if _represents_list_of_qcrbox_models(field_info):
    #             return func(value)
    #         else:
    #             return value
    #
    #     new_fields = {}
    #     for name, field_info in self.model_fields.items():
    #         value = getattr(self, name)
    #         new_fields[name] = optionally_transform_value(name, field_info, value)
    #
    #     return new_fields


class QCrBoxBaseSQLModel(SQLModel):
    """
    Base class for QCrBox SQL models. This allows us to add custom
    tweaks or QCrBox-specific functionality as and when needed.
    """

    model_config = pydantic.ConfigDict(extra="forbid")
