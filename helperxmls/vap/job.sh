#!/bin/bash

#SBATCH --time=04:00:00   # walltime limit (HH:MM:SS)
#SBATCH --nodes=2   # number of nodes
#SBATCH --ntasks-per-node=72
#SBATCH --cpus-per-task=1   # processor core(s) per node
##SBATCH --partition=small    # partition
#SBATCH --job-name="droplet"
#SBATCH --output="drop1%j" # job standard output file (%j replaced by job id)

# LOAD MODULES, INSERT CODE, AND RUN YOUR PROGRAMS HERE
ml gcc
ml mpi

export OMP_NUM_THREADS=1

cd /beegfs/home/d/dasshara/staticLB/01_pureMD/md120r50/vap

srun ~/repos/ls1-mardyn/build/src/MarDyn config_3_generateVap.xml
srun ~/repos/ls1-mardyn/build/src/MarDyn config_4_replicateVap.xml
rm AutoPas*


echo "Job ${SLURM_JOB_ID} named ${SLURM_JOB_NAME} running from ${SLURM_SUBMIT_DIR} done" >> ~/completed_jobs.txt

