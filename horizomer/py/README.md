### Python scripts used in this work

All scripts depend on Python 3.5+ with scikit-bio 0.5.1, unless otherwise stated.

**phylophlan_summarize.py**: Generate marker map and summarize genome to marker matches.
 - `/projects/genome_annotation/20170307/markers/phylophlan/scripts/phylophlan_summarize.py`

**phylophlan_extract.py**: Extract marker gene sequences based on PhyloPhlAn result.
 - `/projects/genome_annotation/20170307/markers/phylophlan/scripts/phylophlan_extract.py`

**phylosift_summarize.py**: Summarize the number of hits per marker per genome.
 - `/projects/genome_annotation/20170307/markers/phylosift/scripts/phylosift_summarize.py`

**phylosift_extract.py**: Extract marker gene sequences from search result.
 - `/projects/genome_annotation/20170307/markers/phylosift/scripts/phylosift_extract.py`

**shrink_taxdump.py**: Shrink the standard NCBI taxdump files `nodes.dmp` and `names.dmp` so that they only contain given TaxIDs and their ancestors
 - `/projects/genome_annotation/profiling/scripts/shrink_taxdump.py`