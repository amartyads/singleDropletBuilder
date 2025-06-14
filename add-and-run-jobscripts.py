#! /usr/bin/env python3

import sys, getopt, os, json, subprocess, shlex
import yaml

CUR_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(CUR_DIR))
from helperscripts.utils import strtobool,getJobID,checkMakeFolder

liqConfigs = ["config_1_generateLiq.xml","config_2_replicateLiq.xml"]
vapConfigs = ["config_3_generateVap.xml","config_4_replicateVap.xml"]
vleConfigs = ["config_5_droplet.xml","config_6_dropletLoad.xml"]

def main(argv):
    with open('config.json','r') as jsonFile:
        jsonData = json.load(jsonFile)

    with open('job-snips.yaml','r') as file:
        jobSnips = yaml.safe_load(file)

    #overwrite with args
    helpText = f"""add-and-run-jobscripts.py
              --runPrep <1/0, default 0>
              --runProd <1/0, default 0>
              --runMamico <1/0, default 0>
              """

    # input: scenario size, droplet diameter, autopas/ls1, 100save y/n, mamico y/n
    try:
        opts, args = getopt.getopt(argv, "he:d:m:", ["help","runPrep=","runProd=","runMamico="])
    except:
        print(helpText)
        sys.exit(2)
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            print(helpText)
            sys.exit()
        elif opt in ("-e", "--runPrep"):
            jsonData["job"]["runPrep"] = strtobool(arg)
        elif opt in ("-d", "--runProd"):
            jsonData["job"]["runProd"] = strtobool(arg)
        elif opt in ("-m", "--runMamico"):
            jsonData["job"]["runMamico"] = strtobool(arg)
    curPath = os.getcwd()
    liqPath = os.path.join(curPath,jsonData['paths']['output'],'liq')
    vapPath = os.path.join(curPath,jsonData['paths']['output'],'vap')
    vlePath = os.path.join(curPath,jsonData['paths']['output'],'vle')
    coupledPath = os.path.join(curPath,jsonData['paths']['output'],'coupled')

    #create folders
    checkMakeFolder(liqPath)
    checkMakeFolder(vapPath)
    checkMakeFolder(vlePath)
    if jsonData['stack']['mamico']:
        checkMakeFolder(coupledPath)

    header = jobSnips["manager"][jsonData["job"]["manager"]]["header"]
    dependency = jobSnips["manager"][jsonData["job"]["manager"]]["dependency"]
    dependencySep = jobSnips["manager"][jsonData["job"]["manager"]]["dependencySep"]

    modules = jobSnips["system"][jsonData["job"]["system"]]["modules"]
    runComm = jobSnips["system"][jsonData["job"]["system"]]["runComm"]
    exec = jobSnips["system"][jsonData["job"]["system"]]["exec"]

    header = header.replace("<wallTime>","01:00:00").replace("<numNodes>","1").replace("<partition>","small").replace("<jobName>","droplet")
    runComm = runComm.replace("<numProcs>","64")

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
        job.write(jobSnips["common"]["preRun"].replace('<workDir>',liqPath))
        job.write(runComm.replace("<execPath>",prepExec).replace("<configFile>",liqConfigs[0]))
        job.write(jobSnips["common"]["errCatch"])
        job.write(runComm.replace("<execPath>",prepExec).replace("<configFile>",liqConfigs[1]))
        job.write(jobSnips["common"]["postRun"])
    if jsonData["job"]["runPrep"]:
        print("Submitting: " + liqPath + "/job.sh")
        liqJobID = subprocess.run(shlex.split(exec), stdout=subprocess.PIPE).stdout.decode('utf-8').rstrip()
        liqJobID = getJobID(liqJobID, jsonData["job"]["system"])

    #vap
    os.chdir(vapPath)
    with open(vapPath + "/job.sh", 'w') as job:
        job.write(header)
        job.write(modules)
        job.write(jobSnips["common"]["preRun"].replace('<workDir>',vapPath))
        job.write(runComm.replace("<execPath>",prepExec).replace("<configFile>",vapConfigs[0]))
        job.write(jobSnips["common"]["errCatch"])
        job.write(runComm.replace("<execPath>",prepExec).replace("<configFile>",vapConfigs[1]))
        job.write(jobSnips["common"]["postRun"])
    if jsonData["job"]["runPrep"]:
        print("Submitting: " + vapPath + "/job.sh")
        vapJobID = subprocess.run(shlex.split(exec), stdout=subprocess.PIPE).stdout.decode('utf-8').rstrip()
        vapJobID = getJobID(vapJobID, jsonData["job"]["system"])

    #vle
    #with buildcp=on and prod=off, config 5 is added to script, 6 isnt
    os.chdir(vlePath)
    with open(vlePath + "/job.sh", 'w') as job:
        job.write(header)
        if liqJobID != '' and vapJobID != '':
            job.write(dependency+liqJobID+dependencySep+vapJobID+'\n')
        job.write(modules)
        job.write(jobSnips["common"]["preRun"].replace('<workDir>',vlePath))
        if jsonData["scenario"]["buildCP"]:
            job.write(runComm.replace("<execPath>",prepExec).replace("<configFile>",vleConfigs[0]))
            job.write(jobSnips["common"]["errCatch"])
            if jsonData["job"]["runProd"]:
                job.write(runComm.replace("<execPath>",prodExec).replace("<configFile>",vleConfigs[1]))
        else:
            job.write(runComm.replace("<execPath>",prodExec).replace("<configFile>",vleConfigs[0]))
        job.write(jobSnips["common"]["postRun"])
    if (jsonData["scenario"]["buildCP"] and jsonData["job"]["runPrep"]) or jsonData["job"]["runProd"]:
        print("Submitting: " + vlePath + "/job.sh")
        vleJobID = subprocess.run(shlex.split(exec), stdout=subprocess.PIPE).stdout.decode('utf-8')
        vleJobID = getJobID(vleJobID, jsonData["job"]["system"])

    #mamico
    if jsonData['stack']['mamico']:
        os.chdir(coupledPath)
        with open(coupledPath + "/job.sh", 'w') as job:
            job.write(header)
            if vleJobID != '':
                job.write(dependency+vleJobID+'\n')
            job.write(modules)
            job.write(jobSnips["common"]["preRun"].replace('<workDir>',coupledPath))
            job.write(runComm.replace("<execPath>",jsonData["paths"]["mamicoExec"]).replace("<configFile>",''))
            job.write(jobSnips["common"]["postRun"])
        if jsonData["job"]["runMamico"]:
            print("Submitting: " + coupledPath + "/job.sh")
            subprocess.run(shlex.split(exec), stdout=subprocess.PIPE).stdout.decode('utf-8').rstrip()

if __name__ == '__main__':
    main(sys.argv[1:])
