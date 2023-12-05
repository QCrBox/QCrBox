from qcrboxtools.robots.olex2 import Olex2Socket

import argparse
import pathlib
import os


def main():
    parser = argparse.ArgumentParser(description="CLI for interacting with Olex2 refinement program via sockets.")

    # Define arguments
    parser.add_argument("--structure_path", help="Path to the structure file")
    parser.add_argument("--tsc_path", help="Path to the tsc(b) file", required=False)
    parser.add_argument("--n_cycles", type=int, default=20, help="Number of cycles for refinement")
    parser.add_argument("--weight_cycles", type=int, default=3, help="Number of refine cycles for weight convergence")

    # Parse arguments
    args = parser.parse_args()

    # Integrate with your script
    olex2_socket = Olex2Socket(structure_path=args.structure_path)

    if args.tsc_path:
        olex2_socket.tsc_path = args.tsc_path

    _ = olex2_socket.refine(n_cycles=args.n_cycles, refine_starts=args.weight_cycles)

    # clean up afterwards
    cif_path = pathlib.Path(args.structure_path)
    os.remove(cif_path.with_suffix('.hkl'))
    os.remove(cif_path.with_suffix('.ins'))
    os.remove(cif_path.with_suffix('.res'))

if __name__ == "__main__":
    main()