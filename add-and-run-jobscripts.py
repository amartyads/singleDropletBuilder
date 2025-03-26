#! /usr/bin/env python3

import sys, getopt, os, json, subprocess, shlex

commonPrerun = """
export OMP_NUM_THREADS=1

cd "<workDir>"

set +e

"""

commonPostrun = """
rm -f AutoPas*

"""

commonErrCatch = """
var=$?
if [ "$var" -ne 0 ];then
    rm -f AutoPas*
    exit $var
fi

"""

slurmHeader = """#!/bin/bash

#SBATCH --time=01:00:00   # walltime limit (HH:MM:SS)
#SBATCH --nodes=1   # number of nodes
#SBATCH --ntasks-per-node=64
#SBATCH --cpus-per-task=1   # processor core(s) per node
#SBATCH --partition=small    # partition
#SBATCH --job-name="droplet"
#SBATCH --output="drop%j" # job standard output file (%j replaced by job id)
#SBATCH --hint=nomultithread

"""

pbsHeader = """#!/bin/bash

#PBS -N droplet
#PBS -l select=1:node_type=rome:mpiprocs=64:ompthreads=1
#PBS -l walltime=01:00:00
#PBS -j oe
#PBS -o output
"""

slurmDependency = """
#SBATCH --dependency=afterok:"""
slurmDependencySep = ","

pbsDependency = """
#PBS -W depend=afterok:"""
pbsDependencySep = ":"

hsuperModules = """
set -e

ml gcc
ml mpi

"""

hawkModules = """
set -e

ml gcc
ml openmpi/5.0.5

"""

hsuperRunComm = """
srun <execPath> <configFile>

"""

hawkRunComm = """
mpirun -n 64 <execPath> <configFile>

"""

hsuperExec = "sbatch job.sh"
hawkExec = "qsub job.sh"

liqConfigs = ["config_1_generateLiq.xml","config_2_replicateLiq.xml"]
vapConfigs = ["config_3_generateVap.xml","config_4_replicateVap.xml"]
vleConfigs = ["config_5_droplet.xml","config_6_dropletLoad.xml"]

def main(argv):
    with open('config.json') as jsonFile:
        jsonData = json.load(jsonFile)

    #overwrite with args
    helpText = f"""add-and-run-jobscripts.py
              --runPrep <1/0, default 0>
              --runProd <1/0, default 0>
              """

    # input: scenario size, droplet diameter, autopas/ls1, 100save y/n, mamico y/n
    try:
        opts, args = getopt.getopt(argv, "he:d:", ["help","runPrep=","runProd="])
    except:
        print(helpText)
        sys.exit(2)
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            print(helpText)
            sys.exit()
        elif opt in ("-e", "--runPrep"):
            jsonData["job"]["runPrep"] = bool(arg)
        elif opt in ("-d", "--runProd"):
            jsonData["job"]["runProd"] = bool(arg)

    curPath = os.getcwd()
    liqPath = os.path.join(curPath,jsonData['paths']['output'],'liq')
    vapPath = os.path.join(curPath,jsonData['paths']['output'],'vap')
    vlePath = os.path.join(curPath,jsonData['paths']['output'],'vle')
    coupledPath = os.path.join(curPath,jsonData['paths']['output'],'coupled')

    #create folders
    if not os.path.exists(jsonData['paths']['output']):
        os.makedirs(liqPath)
        os.makedirs(vapPath)
        os.makedirs(vlePath)
        if jsonData['stack']['mamico']:
            os.makedirs()

    #decisions
    if jsonData["job"]["manager"] == 'slurm':
        header = slurmHeader
        dependency = slurmDependency
        dependencySep = slurmDependencySep
    elif jsonData["job"]["manager"] == 'pbs':
        header = pbsHeader
        dependency = pbsDependency
        dependencySep = pbsDependencySep
    else:
        print("job manager not supported")
        sys.exit(2)


    if jsonData["job"]["system"] == 'hsuper':
        modules = hsuperModules
        runComm = hsuperRunComm
        exec = hsuperExec
    elif jsonData["job"]["system"] == 'hawk':
        modules = hawkModules
        runComm = hawkRunComm
        exec = hawkExec
    else:
        print("cluster not supported")
        sys.exit(2)

    if jsonData["stack"]["autopasPrep"]:
        prepExec = jsonData["paths"]["ls1APExec"]
    else:
        prepExec = jsonData["paths"]["ls1LCExec"]

    if jsonData["stack"]["autopasProd"]:
        prodExec = jsonData["paths"]["ls1APExec"]
    else:
        prodExec = jsonData["paths"]["ls1LCExec"]

    liqJobID = ''
    vapJobID = ''
    vleJobID = ''

    #liq
    os.chdir(liqPath)
    with open(liqPath + "/job.sh", 'w') as job:
        job.write(header)
        job.write(modules)
        job.write(commonPrerun.replace('<workDir>',liqPath))
        job.write(runComm.replace("<execPath>",prepExec).replace("<configFile>",liqConfigs[0]))
        job.write(commonErrCatch)
        job.write(runComm.replace("<execPath>",prepExec).replace("<configFile>",liqConfigs[1]))
        job.write(commonPostrun)
    if jsonData["job"]["runPrep"]:
        print("Submitting: " + liqPath + "/job.sh")
        liqJobID = subprocess.run(shlex.split(exec), stdout=subprocess.PIPE).stdout.decode('utf-8').rstrip()

    #vap
    os.chdir(vapPath)
    with open(vapPath + "/job.sh", 'w') as job:
        job.write(header)
        job.write(modules)
        job.write(commonPrerun.replace('<workDir>',vapPath))
        job.write(runComm.replace("<execPath>",prepExec).replace("<configFile>",vapConfigs[0]))
        job.write(commonErrCatch)
        job.write(runComm.replace("<execPath>",prepExec).replace("<configFile>",vapConfigs[1]))
        job.write(commonPostrun)
    if jsonData["job"]["runPrep"]:
        print("Submitting: " + vapPath + "/job.sh")
        vapJobID = subprocess.run(shlex.split(exec), stdout=subprocess.PIPE).stdout.decode('utf-8').rstrip()

    #vle
    #with buildcp=on and prod=off, config 5 is added to script, 6 isnt
    os.chdir(vlePath)
    with open(vlePath + "/job.sh", 'w') as job:
        job.write(header)
        if liqJobID != '' and vapJobID != '':
            job.write(dependency+liqJobID+dependencySep+vapJobID+'\n')
        job.write(modules)
        job.write(commonPrerun.replace('<workDir>',vlePath))
        if jsonData["scenario"]["buildCP"]:
            job.write(runComm.replace("<execPath>",prepExec).replace("<configFile>",vleConfigs[0]))
            job.write(commonErrCatch)
            if jsonData["job"]["runProd"]:
                job.write(runComm.replace("<execPath>",prodExec).replace("<configFile>",vleConfigs[1]))
        else:
            job.write(runComm.replace("<execPath>",prodExec).replace("<configFile>",vleConfigs[0]))
        job.write(commonPostrun)
    if (jsonData["scenario"]["buildCP"] and jsonData["job"]["runPrep"]) or jsonData["job"]["runProd"]:
        print("Submitting: " + vlePath + "/job.sh")
        vleJobID = subprocess.run(shlex.split(exec), stdout=subprocess.PIPE).stdout.decode('utf-8')

    #mamico
    os.chdir(coupledPath)
    with open(coupledPath + "/job.sh", 'w') as job:
        job.write(header)
        if vleJobID != '':
            job.write(dependency+vleJobID+'\n')
        job.write(modules)
        job.write(commonPrerun.replace('<workDir>',coupledPath))
        job.write(runComm.replace("<execPath>",jsonData["paths"]["mamicoExec"]).replace("<configFile>",''))
        job.write(commonPostrun)
    if jsonData["job"]["runMamico"]:
        print("Submitting: " + coupledPath + "/job.sh")
        subprocess.run(shlex.split(exec), stdout=subprocess.PIPE).stdout.decode('utf-8').rstrip()

if __name__ == '__main__':
    main(sys.argv[1:])
