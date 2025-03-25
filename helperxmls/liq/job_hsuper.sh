#!/bin/bash

#SBATCH --time=01:00:00   # walltime limit (HH:MM:SS)
#SBATCH --nodes=1   # number of nodes
#SBATCH --ntasks-per-node=72
#SBATCH --cpus-per-task=1   # processor core(s) per node
##SBATCH --partition=small    # partition
#SBATCH --job-name="droplet"
#SBATCH --output="drop%j" # job standard output file (%j replaced by job id)

# LOAD MODULES, INSERT CODE, AND RUN YOUR PROGRAMS HERE
ml gcc
ml mpi

export OMP_NUM_THREADS=1

cd {workDir}/liq

srun {ls1Exec} config_1_generateLiq.xml
srun {ls1Exec} config_2_replicateLiq.xml
rm AutoPas*

echo "Job ${SLURM_JOB_ID} named ${SLURM_JOB_NAME} running from ${SLURM_SUBMIT_DIR} done" >> ~/completed_jobs.txt

