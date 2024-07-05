__all__ = ["retrieve_parameter_type"]


class QCrBoxInputCif:
    pass


class QCrBoxInputFile:
    pass


class QCrBoxOutputCif:
    pass


def retrieve_parameter_type(dtype_name):
    match dtype_name:
        case "QCrBox.input_cif":
            return QCrBoxInputCif
        case "QCrBox.input_file":
            return QCrBoxInputFile
        case "QCrBox.output_cif":
            return QCrBoxOutputCif
        case "str":
            return str
        case "int":
            return int
        case "float":
            return float
        case "bool":
            return bool
        case _:
            raise ValueError(f"Unsupported parameter type: {dtype_name!r}")
