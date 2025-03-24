#!/bin/bash

#SBATCH --time=06:00:00   # walltime limit (HH:MM:SS)
#SBATCH --nodes=4   # number of nodes
#SBATCH --ntasks-per-node=72
#SBATCH --cpus-per-task=1   # processor core(s) per node
##SBATCH --partition=small    # partition
#SBATCH --job-name="droplet"
#SBATCH --output="drop%j" # job standard output file (%j replaced by job id)

# LOAD MODULES, INSERT CODE, AND RUN YOUR PROGRAMS HERE
ml gcc
ml mpi

export OMP_NUM_THREADS=1

cd /beegfs/home/d/dasshara/staticLB/01_pureMD/md120r50/liq

srun ~/repos/ls1-mardyn/build/src/MarDyn config_1_generateLiq.xml
srun ~/repos/ls1-mardyn/build/src/MarDyn config_2_replicateLiq.xml
rm AutoPas*

echo "Job ${SLURM_JOB_ID} named ${SLURM_JOB_NAME} running from ${SLURM_SUBMIT_DIR} done" >> ~/completed_jobs.txt

