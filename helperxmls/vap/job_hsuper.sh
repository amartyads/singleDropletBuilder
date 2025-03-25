#!/bin/bash

#SBATCH --time=04:00:00   # walltime limit (HH:MM:SS)
#SBATCH --nodes=2   # number of nodes
#SBATCH --ntasks-per-node=72
#SBATCH --cpus-per-task=1   # processor core(s) per node
##SBATCH --partition=small    # partition
#SBATCH --job-name="droplet"
#SBATCH --output="drop%j" # job standard output file (%j replaced by job id)

# LOAD MODULES, INSERT CODE, AND RUN YOUR PROGRAMS HERE
ml gcc
ml mpi

export OMP_NUM_THREADS=1

cd {workDir}/vap

srun {ls1Exec} config_3_generateVap.xml
srun {ls1Exec} config_4_replicateVap.xml
rm AutoPas*

echo "Job ${SLURM_JOB_ID} named ${SLURM_JOB_NAME} running from ${SLURM_SUBMIT_DIR} done" >> ~/completed_jobs.txt

