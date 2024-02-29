from pyqcrbox.sql_models import CommandSpecDB, ParameterSpecDB


def test_initialise_parameters():
    _ = ParameterSpecDB(name="xxx", dtype="int", required=True)
    _ = ParameterSpecDB(name="yyy", dtype="str", description="Some other parameter", required=False)


def test_initialise_command():
    param_a = ParameterSpecDB(name="a", dtype="int", required=True)
    param_b = ParameterSpecDB(name="b", dtype="str", description="Some other parameter", required=False)

    _ = CommandSpecDB(
        name="calc_hypotenuse",
        description="Given the lengths of two legs of a right triangle, calculate the length of the hypotenuse",
        parameters=[param_a, param_b],
    )
