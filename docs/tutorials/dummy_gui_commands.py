from pyqcrbox import logger


def finalise_interactive(input_file: str) -> str:
    logger.debug(f"Finished dummy GUI session with input file {input_file!r}")

    output_file = input_file.replace(".cif", ".out.cif")
    with open(output_file, "w") as f:
        f.write("Dummy GUI output file")
    logger.debug(f"Wrote output file: {output_file!r}")
    return output_file
