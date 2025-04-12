#! /usr/bin/env python3

import os
import sys
import json
import getopt
import yaml
import subprocess, shlex

CUR_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(CUR_DIR))
from helperscripts.utils import zeroPad, strtobool

def main(argv):
    with open('config.json') as jsonFile:
        jsonData = json.load(jsonFile)
        
    with open('config-scaling.json') as jsonFile:
        scaleData = json.load(jsonFile)
    
    with open('job-snips.yaml','r') as file:
        jobSnips = yaml.safe_load(file)
    
    #overwrite with args
    helpText = f"""extract-scaling-runs.py
              --boxSize <size of box in nm>
              --dropDia <droplet diameter in nm>
              --temp <temperature in reduced>
              --startNum <first int suffix of run>
              --endNum <last int suffix, inclusive>
              --runScripts <1/0, default 0>
              """

    startNum = 1
    endNum = 2

    # input: scenario size, droplet diameter, autopas/ls1, 100save y/n, mamico y/n
    try:
        opts, args = getopt.getopt(argv, "hs:d:t:g:n:r:", ["help","boxSize=","dropDia=","temp=","startNum=","endNum=","runScripts="])
    except:
        print(helpText)
        sys.exit(2)
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            print(helpText)
            sys.exit()
        elif opt in ("-s", "--boxSize"):
            jsonData['scenario']['boxSize'] = int(arg)
        elif opt in ("-d", "--dropDia"):
            jsonData['scenario']['dropDia'] = int(arg)
        elif opt in ("-t","--temp"):
            jsonData['scenario']['temperature'] = float(arg)
        elif opt in ("-g", "--startNum"):
            startNum = int(arg)
        elif opt in ("-n", "--endNum"):
            endNum = int(arg)
        elif opt in ("-r", "--runScripts"):
            scaleData["runScripts"] = strtobool(arg)

    folderName = "s" + str(jsonData["scenario"]["boxSize"]) + "d" + str(jsonData["scenario"]["dropDia"]) + "t" + str(jsonData["scenario"]["temperature"]).replace('.','_')
    startPath = os.getcwd()
    masterFolder = os.path.join(startPath,scaleData["masterPath"],folderName)
    exec = jobSnips["system"][jsonData["job"]["system"]]["exec"]

    os.chdir(masterFolder)
    numNodes = [2**x for x in range(scaleData["scaleStart"],scaleData["scaleSteps"])]
    numNodesSymbols = zeroPad(numNodes)
    runTypes = ["strong", "weak"]

    for config in scaleData["configs"]:
        for runType in runTypes:
            for numNode in numNodesSymbols:
                chpath = os.path.join(config["name"],runType,numNode)
                os.chdir(chpath)
                for i in range(startNum, endNum+1):
                    execCopy = exec.replace('job.sh',f'job{i}.sh')
                    with open('job.sh') as job:
                        newText = job.read().replace('output','output'+str(i))
                    with open(f'job{i}.sh', "w") as f:
                        f.write(newText)
                    subprocess.run(shlex.split(f'rm -f output{i}'))
                    if scaleData["runScripts"]:
                        print("Submitting: " + os.getcwd() + f"/job{i}.sh")
                        subprocess.run(shlex.split(execCopy), stdout=subprocess.PIPE).stdout.decode('utf-8').rstrip()
                os.chdir(masterFolder)

if __name__ == '__main__':
    main(sys.argv[1:])
