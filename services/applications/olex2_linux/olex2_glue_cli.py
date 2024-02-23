import argparse
import os
import pathlib

from qcrboxtools.robots.olex2 import Olex2Socket


def refine(args):
    olex2_socket = Olex2Socket(structure_path=args.structure_path)

    if args.tsc_path:
        olex2_socket.tsc_path = args.tsc_path

    _ = olex2_socket.refine(n_cycles=args.n_cycles, refine_starts=args.weight_cycles)

def run_commands(args):

    olex2_socket = Olex2Socket(structure_path=args.structure_path)

    if args.tsc_path:
        olex2_socket.tsc_path = args.tsc_path

    cmd_string = pathlib.Path(args.cmd_file_path).read_text(encoding='UTF-8')

    olex2_socket.send_command(cmd_string)
    olex2_socket.send_command(f'file {str(olex2_socket.structure_path)}')

def main():
    parser = argparse.ArgumentParser()

    subparsers = parser.add_subparsers(required=True)

    parser_refine = subparsers.add_parser(
        'refine', description="CLI for interacting with Olex2 refinement program via sockets."
    )
    parser_refine.add_argument("--structure_path", help="Path to the structure file")
    parser_refine.add_argument("--tsc_path", help="Path to the tsc(b) file", required=False)
    parser_refine.add_argument("--n_cycles", type=int, default=20, help="Number of cycles for refinement")
    parser_refine.add_argument("--weight_cycles", type=int, default=3, help="Number of refine cycles for weight convergence")
    parser_refine.set_defaults(func=refine)

    parser_cmds = subparsers.add_parser(
        'cmds', description='CLI for running arbitrary commands with Olex2'
    )

    parser_cmds.add_argument("--structure_path", help="Path to the structure file")
    parser_cmds.add_argument("--tsc_path", help="Path to the tsc(b) file", required=False)
    parser_cmds.add_argument("--cmd_file_path", help="file containing a list of olex2 commands")
    parser_cmds.set_defaults(func=run_commands)

    # Parse arguments
    args = parser.parse_args()

    args.func(args)


if __name__ == '__main__':
    main()

