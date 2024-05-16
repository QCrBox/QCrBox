import argparse
import hashlib
from pathlib import Path

from qcrboxtools.cif.cif2cif import cif_file_merge_to_unified_by_yml, cif_file_to_specific_by_yml
from qcrboxtools.robots.olex2 import Olex2Socket

YAML_PATH = "/opt/qcrbox/config_olex2.yaml"


def refine(args):
    work_cif_path = args.input_cif_path.parent / "qcrbox_work.cif"

    if args.tsc_path:
        command_name = "refine_tsc"
    else:
        command_name = "refine_iam"

    cif_file_to_specific_by_yml(
        args.input_cif_path.parent / "qcrbox_work.cif", work_cif_path, YAML_PATH, command_name, "input_cif_path"
    )

    olex2_socket = Olex2Socket(structure_path=work_cif_path)

    if args.tsc_path:
        olex2_socket.tsc_path = args.tsc_path

    _ = olex2_socket.refine(n_cycles=args.n_cycles, refine_starts=args.weight_cycles)

    cif_file_merge_to_unified_by_yml(
        work_cif_path, args.output_cif_path, args.input_cif_path, YAML_PATH, command_name, "output_cif_path"
    )


def run_commands(args):
    work_cif_path = args.input_cif_path.parent / "qcrbox_work.cif"

    cif_file_to_specific_by_yml(args.input_cif_path, work_cif_path, YAML_PATH, "run_cmds_file", "input_cif_path")

    olex2_socket = Olex2Socket(structure_path=work_cif_path)

    hash0 = hashlib.md5(work_cif_path.read_bytes()).hexdigest()

    if args.tsc_path:
        olex2_socket.tsc_path = args.tsc_path

    cmd_string = args.cmd_file_path.read_text(encoding="UTF-8")

    olex2_socket.send_command(cmd_string)

    hash1 = hashlib.md5(work_cif_path.read_bytes()).hexdigest()

    if hash0 != hash1 and args.output_cif_path is not None:
        cif_file_merge_to_unified_by_yml(
            work_cif_path, args.output_cif_path, args.input_cif_path, YAML_PATH, "run_cmds_file", "output_cif_path"
        )


def main():
    parser = argparse.ArgumentParser()

    subparsers = parser.add_subparsers(required=True)

    parser_refine = subparsers.add_parser(
        "refine",
        description="CLI for interacting with Olex2 refinement program via sockets.",
    )
    parser_refine.add_argument("--input_cif_path", help="Path to the structure file", type=Path, required=True)
    parser_refine.add_argument("--output_cif_path", help="Path to the output CIF file", type=Path)
    parser_refine.add_argument("--tsc_path", help="Path to the tsc(b) file", type=Path, required=False)
    parser_refine.add_argument("--n_cycles", type=int, default=20, help="Number of cycles for refinement")
    parser_refine.add_argument(
        "--weight_cycles",
        type=int,
        default=3,
        help="Number of refine cycles for weight convergence",
    )
    parser_refine.set_defaults(func=refine)

    parser_cmds = subparsers.add_parser("cmds", description="CLI for running arbitrary commands with Olex2")

    parser_cmds.add_argument("--input_cif_path", help="Path to the structure file", type=Path, required=True)
    parser_cmds.add_argument("--output_cif_path", help="Path to the output CIF file", type=Path, required=False)
    parser_cmds.add_argument("--tsc_path", help="Path to the tsc(b) file", type=Path, required=False)
    parser_cmds.add_argument(
        "--cmd_file_path", help="file containing a list of olex2 commands", type=Path, required=True
    )
    parser_cmds.set_defaults(func=run_commands)

    # Parse arguments
    args = parser.parse_args()

    args.func(args)


if __name__ == "__main__":
    main()
