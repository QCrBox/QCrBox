This directory is a placeholder. Before building the SHELX Docker image,
the SHELX executables need to be placed here so that they can be copied
into the Docker image.

These can be downloaded from: https://shelx.uni-goettingen.de/bin/linux64/
Note that even if you are on a Windows machine, you must download the Linux
executables because they will be installed inside a docker container.

As of 18th September 2023, the following files are present (see the contents
of `../shelx_checksums.txt` for the precise SHA-256 checksums of these files).

```
Name              Last modified      Size

2018_shelxl.bz2   2022-09-21 09:04   2.9M
anode.bz2         2016-05-25 13:49   8.4M
ciftab.bz2        2016-05-25 13:49   1.3M
pdb2ins           2018-03-13 11:15   20M
pdb2insGUI        2018-03-13 11:15   22M
shelxc.bz2        2016-05-25 13:49   1.5M
shelxd.bz2        2016-05-25 13:49   8.4M
shelxe            2022-12-29 21:12   27M
shelxl            2022-12-29 21:12   5.6M
shelxs.bz2        2016-05-25 13:49   1.5M
shelxt.bz2        2018-03-13 11:14   8.5M
shredcif.bz2      2016-05-25 13:49   1.3M
```
