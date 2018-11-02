#!/bin/bash

########################################################################
# generator.sh for VHDL task fsm_mealy
# Generates the individual tasks, enters in databases and moves
# description files to user folder
#
# Copyright (C) 2015 Martin  Mosbeck   <martin.mosbeck@gmx.at>
# License GPL V2 or later (see http://www.gnu.org/licenses/gpl2.txt)
########################################################################


##########################
####### PARAMETERS #######
##########################
user_id=$1
task_nr=$2
submission_email=$3
mode=$4
semester_db=$5
language=$6

##########################
########## PATHS #########
##########################
# src path of autosub system
autosub_path=$(pwd)
# root path of the task itself
task_path=$(readlink -f $0|xargs dirname)
# path for all the files that describe the created path
desc_path="${autosub_path}/users/${user_id}/Task${task_nr}/desc"

##########################
##### PATH CREATIONS #####
##########################
if [ ! -d "${task_path}/tmp" ]
then
   mkdir ${task_path}/tmp
fi

if [ ! -d "${desc_path}" ]
then
   mkdir ${desc_path}
fi

##########################
########## MISC ##########
##########################
TASKERROR=3

##########################
####### GENERATE #########
##########################
cd ${task_path}

task_parameters=$(python3 scripts/generateTask.py \
    "${user_id}" "${task_nr}" "${submission_email}" "${language}" \
    2> tmp/generator_error_${user_id}_Task${task_nr}.txt)

# output errors from generateTask.py (if any occured) to stderr to be logged
if [ -s "tmp/generator_error_${user_id}_Task${task_nr}.txt" ]
then
    cat tmp/generator_error_${user_id}_Task${task_nr}.txt 1>&2
    exit $TASKERROR
else
    rm -f tmp/generator_error_${user_id}_Task${task_nr}.txt
fi

#generate the description pdf and move it to user's description folder
cd ${task_path}/tmp

pdflatex -halt-on-error desc_${user_id}_Task${task_nr}.tex >/dev/null
RET=$?
zero=0
if [ "$RET" -ne "$zero" ];
then
    echo "ERROR with pdf generation for Task${task_nr} !!! Are all needed LaTeX packages installed??">&2
    exit $TASKERROR
fi

pdflatex -halt-on-error desc_${user_id}_Task${task_nr}.tex >/dev/null #second time for reference to picture resolution
rm -f desc_${user_id}_Task${task_nr}.aux
rm -f desc_${user_id}_Task${task_nr}.log
rm -f desc_${user_id}_Task${task_nr}.tex
rm -f desc_${user_id}_Task${task_nr}.out
rm -f fsm_${user_id}_Task${task_nr}

#copy description and state chart image tp user's description folder
mv ${task_path}/tmp/desc_${user_id}_Task${task_nr}.pdf ${desc_path}
mv ${task_path}/tmp/fsm_${user_id}_Task${task_nr}.png ${desc_path}

#copy static files to user's description folder
cp ${task_path}/static/fsm.vhdl ${desc_path}
cp ${task_path}/static/fsm_beh.vhdl ${desc_path}

# move package file to user's description folder
mv ${task_path}/tmp/fsm_pkg_${user_id}_Task${task_nr}.vhdl ${desc_path}/fsm_pkg.vhdl

#for exam
cp ${task_path}/exam/testbench_exam.vhdl ${desc_path}/fsm_tb_exam.vhdl

##########################
##   EMAIL ATTACHMENTS  ##
##########################
task_attachments=""
task_attachments_base="${desc_path}/desc_${user_id}_Task${task_nr}.pdf ${desc_path}/fsm_pkg.vhdl ${desc_path}/fsm.vhdl ${desc_path}/fsm_beh.vhdl"

if [ -n "${mode}" ];
then
    if [ "${mode}" = "exam" ];
    then
        task_attachments="${task_attachments_base} ${desc_path}/fsm_tb_exam.vhdl"
    fi
fi
if [ -z "${mode}" ] || [ "${mode}" = "normal" ]; #default to normal
then
    task_attachments="${task_attachments_base}"
fi

##########################
## ADD TASK TO DATABASE ##
##########################
cd ${autosub_path}/tools
python3 add_to_usertasks.py -u ${user_id} -t ${task_nr} -p "${task_parameters}" -a "${task_attachments}" -d ${semester_db}
