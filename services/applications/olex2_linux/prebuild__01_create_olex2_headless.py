import io
import pathlib
import sys
import zipfile

import requests

from qcrbox.logging import logger

url = "https://secure.olex2.org/olex2-distro/1.5-alpha/olex2-linux64.zip"
output_path = pathlib.Path("olex2_files/olex2-linux64_hl.zip")

startc_str = """#! /bin/bash

#http://stackoverflow.com/questions/59895/can-a-bash-script-tell-what-directory-its-stored-in
SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ]; do # resolve $SOURCE until the file is no longer a symlink
  DIR="$( cd -P "$( dirname "$SOURCE" )" && pwd )"
  SOURCE="$(readlink "$SOURCE")"
  [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE" # if $SOURCE was a relative symlink, we need to resolve it relative to the path where the symlink file was located
done
bin_dir="$( cd -P "$( dirname "$SOURCE" )" && pwd )"

#modify the line below to point to a valid cctbx installtion to be used with olex2
export OLEX2_CCTBX_DIR=$bin_dir/cctbx
#this is necessary here as the cctbx sets signalf for FPE and does not handle them...
export BOOST_ADAPTBX_FPE_DEFAULT=1
export BOOST_ADAPTBX_SIGNALS_DEFAULT=1

#uncomment this on k/ubuntu to fix graphics...
#export OLEX2_GL_DEFAULT=True
#change if have/need stereo support in opengl (use gl.stereo(hardware) to turn on)
export OLEX2_GL_STEREO=FALSE
export OLEX2_GL_MULTISAMPLE=FALSE
# change appropriatly - if needed
export OLEX2_GL_DEPTH_BITS=16

#uncomment the line below to specify alternative location of olex2 GUI
#by default it is the $bin_dir
#export OLEX2_DIR=$bin_dir


# we need to set the correct update path, if the gui is not at the default location
#update_path="$bin_dir"

if [ $OLEX2_DIR ]
then
  update_path="$OLEX2_DIR"
  echo Setting the update path to: $update_path
fi

#set the dynamic library paths
export LD_LIBRARY_PATH=$bin_dir/lib:$OLEX2_CCTBX_DIR/cctbx_build/lib:$LD_LIBRARY_PATH
export PYTHONHOME=$bin_dir
export PATH=$bin_dir/bin:$PATH

# this may be needed for SSL in Python
#export SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt

cd "$bin_dir"
if [ ! -x unirun ]
then
  chmod +x unirun
fi

if [ -n "$update_path" ]
then
  ./unirun -run
else
  $bin_dir/unirun "$update_path" -run
fi

if [ ! -x olex2c-linux64 ]
then
  chmod +x olex2c-linux64
fi

./olex2c-linux64 "$@"
"""

macrox_string = """<xl_macro

<a
  <body
    <args
      <arg1 name='file' def='DataDir()/samples/sucrose/sucrose.res'>
    >
    <cmd
      <cmd10 "reap %1">
    >
  >
>

<b
  <body
    <args
      <arg1 name='file' def='DataDir()/samples/THPP/thpp.res'>
    >
    <cmd
      <cmd10 "reap %1">
    >
  >
>

<c
  <body
    <args
      <arg1 name='file' def='DataDir()/samples/Co110/Co110.res'>
    >
    <cmd
      <cmd10 "reap %1">
    >
  >
>


<onstartup help="Executes on program start"
  <body
    <args
      <arg1 name="width" def='100'>
    >
    <cmd
      <cmd1 XXX="silent on">
      <cmd2 "py.Export(datadir()/olx)">
      <cmd3 "py.run basedir()/util/pyUtil/initpy.py">
      <cmd4 "if IsVar(defeditor) then none else setvar(defeditor,'gedit')">
      <cmd5 "if IsVar(defexplorer) then none else setvar(defexplorer,'nautilus')">
      <cmd6 "if IsVar(defbrowser) then none else setvar(defbrowser,'htmlview')">
      <cmd7 cmd1="spy.InitialiseVariables(startup)">
      <cmd8 XXX="echo filepath()">
      <cmd9 XXX="panel html.clientwidth(self)">
      <cmd10 XXX="schedule 8 'UpdateFile olex2.exe'">
      <cmd11 "server start">
    >

  <onterminate
    <cmd1 cmd1="clear">
    <cmd2 "echo filepath()">
  >
>
>

<reap help="Load a Crystallographic File"
  <body
    <args
      <arg1 name="file name" def="">
      <arg2 name="options" def="">
      <arg3 name="width" def="100">
      <arg4 name="filename" def="filename()">
      <arg5 name="base" def="basedir()">
      <arg6 name="ext" def="fileext()">
      <arg7 name="filefull" def="filefull()">
      >
    <cmd
      <cmd1  "if strcmp(%4,'none') then none else spy.saveHistory()">
      <cmd2  "spy.SaveStructureParams()">
      <cmd4  "@reap %1 %2">
      <cmd4  "echo 'loading'">
      <cmd9  "spy.OnStructureLoaded(%7)">
      <cmd4  "echo 'loaded'">
      <cmd7  "SetVar(snum_refinement_sg,sg(%n))">
      <cmd10 "if File.Exists(strdir()/filename().vvd) then none else 'SetVar(snum_refinement_original_formula,xf.GetFormula())'">
      <cmd14 cmd1="if strcmp(%4,filename()) then none else 'clear'">
    >
  >
>


<onexit help="Executes on program exit"
  <body
    <args
    >

  <cmd
    <cmd1  "echo Good Bye">
    <cmd2  "spy.saveHistory()">
    <cmd3  x="spy.pickleVVD(structure)">
    <cmd4  x="storeparam startup filefull()">
    <cmd26 "stop logging">
>

  <onterminate
  >
>
>


<report help="Creates structure report"
  <body
    <args
      <arg1 name="show_html" def="False">
    >
    <cmd
      <cmd8 "spy.SetParam(snum.report.title, spy.GetParam(snum.report.title))">
      <cmd8 "spy.ExtractCifInfo()">
      <cmd9 "spy.MergeCif()">
      <cmd11 "cif2tab header acrd anis bnd ang htab tang hcrd footer -n=spy.GetParam(snum.report.title)_tables">
      <cmd12 "if %1 then 'shell spy.GetParam(snum.report.title)_tables.html'">
    >
  >
>

<refine help="Launches refine program. Syntax: refine [l.s.=-1] [plan=-1]"
  <body
    <args
      <arg0 name="l.s." def='-1'>
      <arg1 name="plan" def='-1'>
    >
    <cmd
      <cmd4 "user filepath()">
      <cmd3 "kill $q">
      <cmd5 "file">
      <cmd5 "if strcmp(%1,'-1') then None else spy.SetMaxCycles(%1)">
      <cmd6 "if strcmp(%2,'-1') then None else spy.SetMaxPeaks(%2)">
      <cmd10 "spy.RunRefinementPrg()">
    >
  >
>


<solve help="Launches solution program XS"
  <body
    <args
      <arg1 name="SOLVE" def='SOLVE'>
    >
    <cmd
      <cmd10 "spy.RunSolutionPrg()">
    >
  >
>


<tidy help = "Automatically select things"
  <body
    <args
      <arg1 name="cutoff" def='0.07'>
    >
    <cmd
      <cmd1 "sel atoms where xatom.uiso > %1">
      <cmd2 "sel atoms where xatom.peak<2&&xatom.peak>0">
      <cmd3 "updatehtml">
    >
  >
>


<edit help="Launches notepad for the file with name of current file and extension passed as parameter"
  <body
    <args
      <arg1 name="File extension" def="ins">
      <arg2 name="File path" def="filepath()">
      <arg3 name="File name" def="filename()">
    >
    <cmd
      <cmd1 cmd1="silent on">
      <cmd2 cmd1="echo %2%3.%1">
      <cmd3 "file">
      <cmd4 "if or(IsFileType(ires),IsFileType(cif)) then 'listen filepath()/filename().%1' else none">
      <cmd5 "if strcmp(%1,hkl) then 'exec -o getvar(defeditor) hklsrc()' else 'exec -o getvar(defeditor) filepath()/filename().%1'">
    >
    <onterminate
      <cmd0 "silent off">
      <cmd1 "stop">
    >
  >
>

</ help="Add command to the ins file"
  <body
    <args
      <arg1 name="name" def="">
      <arg2 name="name" def="">
      <arg3 name="name" def="">
      <arg4 name="name" def="">
      <arg5 name="name" def="">
        >
    <cmd
      <cmd1 "addins %1 %2 %3 %4 %5">
    >
  >
>


<emf help='Edit a macro file (macro, auto, custom, ...)'
  <body
    <args
      <arg1 name="filname" def="custom">
    >
    <cmd
      <cmd1 "exec -o getvar(defeditor) basedir()/%1.xld">
    >
  >
>

<log help='Shows the current log file'
  <body
    <args
      <arg1 name="filname" def="custom">
    >
    <cmd
      <cmd1 "flush log">
      <cmd2 "exec -o getvar(defeditor) app.GetLogName()">
    >
  >
>

<config help='Opens the config file'
  <body
    <args
      <arg1 name="filname" def="custom">
    >
    <cmd
      <cmd1 "exec -o getvar(defeditor) BaseDir()/util/pyUtil/PluginLib/plugin-AutoChem/autochem_config.txt">
    >
  >
>


<profile help='Opens the profiler output'
  <body
    <args
      <arg1 name="filname" def="custom">
    >
    <cmd
      <cmd1 "exec -o getvar(defeditor) DataDir()/profile.txt">
    >
  >
>

<dire help="Opens the current directory in Explorer"
  <body
    <cmd
      <cmd0 "exec -o getvar(defexplorer) filepath()">
    >
  >
>

<oda help="Launches ac_run"
  <body
    <args
      <arg1 name="single" def="">
    >
    <cmd
      <cmd6 "spy.runODAC('spy.ac_run solveit -%1')">
    >
  >
>


<ac6 help="Launches ac_run"
  <body
    <args
      <arg1 name="single" def="">
    >
    <cmd
      <cmd1 "spy.ac6.auto()">
    >
  >
>

<start_autochem help="Launches ac_run"
  <body
    <args
      <arg1 name="filefull" def="'FileFull()'">
    >
    <cmd
      <cmd1 "reap %1.ins">
      <cmd2 "spy.ac6.auto()">
    >
  >
>

<start_rpac help="Launches ReportPlusAC"
  <body
    <args
      <arg1 name="filefull" def="'FileFull()'">
    >
    <cmd
      <cmd1 "reap %1.ins">
      <cmd2 "spy.ac6.create_report()">
    >
  >
>

<onexit help="Executes on program exit"
  <body
  <cmd
    <cmd "stop logging">
    <cmd "flush history">
    <cmd "if IsFileLoaded() then 'spy.saveHistory()>>spy.SaveStructureParams()>>
          spy.SaveCifInfo()'">
    <cmd "spy.SaveUserParams()">
    <cmd "spy.SaveOlex2Params()">
    <cmd "spy.threading.joinAll()">
    <cmd "spy.onexit()">
    <cmd "echo Good Bye">
  >
 >
>

<reapcif help="Load a Crystallographic File"
  <body
    <args
      <arg1 name="file name" def="">
      <arg2 name="options" def="">
      <arg3 name="width" def="100">
      <arg4 name="filename" def="filename()">
      <arg5 name="base" def="basedir()">
      <arg6 name="ext" def="fileext()">
      >
    <cmd
      <cmd1  "if strcmp(%4,'none') then none else spy.saveHistory()">
      <cmd2  "spy.SaveStructureParams()">
      <cmd4  "@reap %1">
      <cmd4  "echo 'loading'">
      <cmd9  "spy.OnStructureLoaded(%4)">
      <cmd4  "echo 'loaded'">
      <cmd7  "SetVar(snum_refinement_sg,sg(%n))">
      <cmd8  a="spy.SetParam(snum.refinement_max_peaks,Ins(QNUM))">
      <cmd9  a="spy.SetParam(snum.refinement_max_cycles,Ins(LS))">
      <cmd10 "if File.Exists(strdir()/filename().vvd) then none else 'SetVar(snum_refinement_original_formula,xf.GetFormula())'">
      <cmd11 "if and(strcmp(%4,filename()),strcmp(%6,fileext())) then none else 'spy.loadHistory()'">
      <cmd14 cmd1="if strcmp(%4,filename()) then none else 'clear'">
    >
  >
>

<export help="Exports data from CIF"
  <body
    <args
      <arg1 name="hkl_name" def="">
    >
    <cmd
      <cmd1 "@export %1">
      <cmd2 "spy.cif.reloadMetadata(True)">
    >
  >
>

<#include "custom.xld">
<#include "app.ConfigDir()/custom.xld">
"""


def create_new_file():
    logger.debug(f"Downloading Olex2 archive from: {url}")
    r = requests.get(url, timeout=600)
    zip_io = io.BytesIO(r.content)
    zip_file = zipfile.ZipFile(zip_io, "a")
    zip_file.writestr("olex2/startc", startc_str)
    zip_file.writestr("olex2/macrox.xld", macrox_string)
    zip_file.write("olex2_files/olex2c-linux64", "olex2/olex2c-linux64")
    zip_file.close()
    with open(output_path, "wb") as fobj:
        fobj.write(zip_io.getbuffer())


def main():
    if not output_path.exists():
        if not pathlib.Path("olex2_files/olex2c-linux64"):
            logger.error("Could not find ./olex2_file/olex2c-linux64, this file is necessary")
            sys.exit(1)
        create_new_file()


if __name__ == "__main__":
    main()
