#!/bin/bash

#SBATCH --time=08:00:00   # walltime limit (HH:MM:SS)
#SBATCH --nodes=2   # number of nodes
#SBATCH --ntasks-per-node=72
#SBATCH --cpus-per-task=1   # processor core(s) per node
#SBATCH --partition=small    # partition
#SBATCH --job-name="droplet"
#SBATCH --output="drop%j" # job standard output file (%j replaced by job id)
#SBATCH --hint=nomultithread
#SBATCH --dependency=afterok:462535,462536

# LOAD MODULES, INSERT CODE, AND RUN YOUR PROGRAMS HERE
ml gcc
ml mpi

export OMP_NUM_THREADS=1

cd /beegfs/home/d/dasshara/staticLB/01_pureMD/md120r50/vle

#srun ~/repos/ls1-mardyn/build/src/MarDyn config_5_droplet_ref.xml
srun ~/repos/ls1-mardyn/build/src/MarDyn config_5_droplet.xml
#srun ~/repos/ls1-mardyn/build/src/MarDyn config_5_droplet_biggerD.xml
#srun ~/repos/ls1-mardyn/build/src/MarDyn config_5_droplet_lessspace.xml
rm AutoPas*
echo "Job ${SLURM_JOB_ID} named ${SLURM_JOB_NAME} running from ${SLURM_SUBMIT_DIR} done" >> ~/completed_jobs.txt

