from pathlib import Path
from textwrap import dedent

from pyqcrbox import sql_models_NEW_v2
from pyqcrbox.registry.client import QCrBoxClient

from qcrboxtools.cif.cif2cif import cif_file_merge_to_unified_by_yml, cif_file_to_specific_by_yml
from qcrboxtools.cif.file_converter.hkl import cif2hkl4
from qcrboxtools.cif.read import read_cif_as_unified, read_cif_safe, cifdata_str_or_index

YAML_PATH = "./config_tonto_lamagoet.yaml"

def run_hirshfeld_hf(input_cif_path, output_cif_path, multiplicity, charge, basis_name):
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
        basis_name= {basis_name}
        crystal= {{
            xray_data= {{
            refine_h_u_iso= %(refine_h_u_iso)s
            refine_positions_only= %(refine_positions_only)s
            thermal_smearing_model= %(thermal_smearing_model)s
            partition_model= %(partition_model)s
            optimise_extinction= %(optimise_extinction)s
            correct_dispersion = %(correct_dispersion)s
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
            convergence= %(convergence)s
            diis= {{ convergence_tolerance= %(convergence_tolerance)s }}
        }}
        scf ! << do this

        ! Set cluster-charge SCF for refinement
        scfdata= {{
            kind=  rhf
            initial_density= restricted
            use_SC_cluster_charges= TRUE
            cluster_radius= 8 angstrom
            convergence= %(convergence)s
            diis= {{ convergence_tolerance= %(convergence_tolerance)s }}
        }}

        ! Do the refinement ...
        ! It repeatedly does SCF calculations
        refine_hirshfeld_atoms

        ! Clean up
        delete_scf_archives
        }}
    """)

    work_cif_path.with_name('stdin').write_text(stdin, encoding="UTF-8")



if __name__ == "__main__":
    application_spec = sql_models_NEW_v2.ApplicationSpec.from_yaml_file("config_tonto_lamagoet.yaml")
    client = QCrBoxClient(application_spec=application_spec)
    client.run()