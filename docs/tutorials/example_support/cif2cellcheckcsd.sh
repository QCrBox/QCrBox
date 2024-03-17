#!/bin/bash

# Usage: script_name path_to_cif_file dimension_tolerance angle_tolerance maximum_hits

cif_file=$1
dimension_tolerance=$2
angle_tolerance=$3
maximum_hits=$4

# Check for correct number of arguments
if [ "$#" -ne 4 ]; then
    echo "Usage: $0 path_to_cif_file dimension_tolerance angle_tolerance maximum_hits"
    exit 1
fi

# Function to clean extracted values (removing potential string indicators and newlines)
clean_value() {
    echo "$1" | sed "s/['\"]//g" | tr -d '\n'
}

# Extract cell parameters from CIF file, avoiding similar entries by ensuring whitespace or end-of-line after the parameter name
a=$(clean_value $(grep -oP '_cell.length_a\s+\K\S+' $cif_file))
b=$(clean_value $(grep -oP '_cell.length_b\s+\K\S+' $cif_file))
c=$(clean_value $(grep -oP '_cell.length_c\s+\K\S+' $cif_file))
alpha=$(clean_value $(grep -oP '_cell.angle_alpha\s+\K\S+' $cif_file))
beta=$(clean_value $(grep -oP '_cell.angle_beta\s+\K\S+' $cif_file))
gamma=$(clean_value $(grep -oP '_cell.angle_gamma\s+\K\S+' $cif_file))

# Try to extract lattice centring from "_space_group.centring_type"
centring=$(clean_value $(grep -oP '_space_group.centring_type\s+\K\S+' $cif_file))

# If not available, use the first letter of "_space_group.name_h-m_alt", handling potential string indicators
if [ -z "$centring" ]; then
    centring=$(clean_value $(grep -oP '_space_group.name_h-m_alt\s+\K\S+' $cif_file | cut -c 1))
fi

# Default to "P" if none is found
if [ -z "$centring" ]; then
    centring="P"
fi

# Create the XML content
cat <<EOF > search.xml
<?xml version="1.0" encoding="UTF-8"?>
<query name="reduced_cell_search" version="1.0" originator="crysalispro">
  <lattice_centring>$centring</lattice_centring>
  <a>$a</a>
  <b>$b</b>
  <c>$c</c>
  <alpha>$alpha</alpha>
  <beta>$beta</beta>
  <gamma>$gamma</gamma>
  <settings>
    <dimension_tolerance>$dimension_tolerance</dimension_tolerance>
    <angle_tolerance>$angle_tolerance</angle_tolerance>
    <maximum_hits>$maximum_hits</maximum_hits>
  </settings>
</query>
EOF

# Extract the directory from the CIF file path
dir=$(dirname "$cif_file")

# Define the output XML file path in the same directory as the CIF file
output_xml="$dir/output.xml"

ccdc_searcher -query search.xml -results "$output_xml"