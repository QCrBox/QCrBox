import subprocess
from pathlib import Path
from textwrap import dedent

from qcrboxtools.cif.cif2cif import cif_file_to_specific_by_yml
from qcrboxtools.cif.file_converter.hkl import cif2hkl4
from qcrboxtools.cif.read import read_cif_as_unified, read_cif_safe

from pyqcrbox import sql_models_NEW_v2
from pyqcrbox.registry.client import QCrBoxClient

YAML_PATH = "./config_tonto_lamagoet.yaml"

def run_hirshfeld_hf(input_cif_path, output_cif_path, multiplicity, charge, basis_set):
    input_cif_path = Path(input_cif_path)
    work_cif_path = input_cif_path.with_name("work.cif")

    cif_file_to_specific_by_yml(input_cif_path, work_cif_path, YAML_PATH, "run_hirshfeld", "input_cif_path")

    hkl_file_path = work_cif_path.with_suffix(".hkl")
    cif2hkl4(work_cif_path, 0, hkl_file_path)

    shelx_hkl_str = hkl_file_path.read_text(encoding="UTF-8")
    header = dedent("""
        reflection_data= {
        keys= { h= k= l= i_exp= i_sigma= }
            data= {
    """)

    footer = dedent("""
            }
        }
        REVERT
    """)
    shelx_hkl_str = header + shelx_hkl_str + footer
    hkl_file_path.write_text(shelx_hkl_str, encoding="UTF-8")

    _, data_name = read_cif_safe(work_cif_path, 0)

    unified_block = read_cif_as_unified(work_cif_path, 0)
    if "_refine_ls.extinction_coef" in unified_block:
        optimise_extinction = "TRUE"
    else:
        optimise_extinction = "FALSE"

    convergence = 0.001
    convergence_tolerance = 0.001
    stdin = dedent(f"""\
        {{
        name= qcrbox
        charge= {charge}
        multiplicity= {multiplicity}
        cif= {{
            file_name=  {work_cif_path.name}
            data_block_name= {data_name}
        }}
        process_cif
        basis_directory= {work_cif_path.parent}
        basis_name= {basis_set}
        crystal= {{
            xray_data= {{
            refine_h_u_iso= TRUE
            refine_positions_only= FALSE
            thermal_smearing_model= hirshfeld
            partition_model= gaussian
            optimise_extinction= {optimise_extinction}
            correct_dispersion = TRUE
            REDIRECT {hkl_file_path.name}
            }}
        }}
        becke_grid = {{
            set_defaults
            accuracy= high
        }}
        scfdata= {{
            kind = rhf
            initial_density= promolecule
            convergence= {convergence}
            diis= {{ convergence_tolerance= {convergence_tolerance} }}
        }}
        scf ! << do this

        ! Set cluster-charge SCF for refinement
        scfdata= {{
            kind=  rhf
            initial_density= restricted
            use_SC_cluster_charges= TRUE
            cluster_radius= 8 angstrom
            convergence= {convergence}
            diis= {{ convergence_tolerance= {convergence_tolerance} }}
        }}

        ! Do the refinement ...
        ! It repeatedly does SCF calculations
        refine_hirshfeld_atoms

        put_CIF

        ! Clean up
        delete_scf_archives
        }}
    """)

    work_cif_path.with_name('stdin').write_text(stdin, encoding="UTF-8")

    subprocess.check_call(['tonto', '--b /opt/qcrbox/tonto/basis_sets'], cwd=work_cif_path.parent)



if __name__ == "__main__":
    application_spec = sql_models_NEW_v2.ApplicationSpec.from_yaml_file("config_tonto_lamagoet.yaml")
    client = QCrBoxClient(application_spec=application_spec)
    client.run()