#! /usr/bin/env python3

# create folders
# strong scaling
# weak scaling

import json, sys, getopt, subprocess, shlex, os, shutil

def zeroPad(digits):
    maxDigs = len(str(max(digits)))
    toRet = [str(x).zfill(maxDigs) for x in digits]
    return toRet

def checkMakeFolder(path, printPath=False):
    if not os.path.exists(path):
        if printPath:
            print("Creating folder: " + path)
        os.makedirs(path)

def main(argv):
    with open('config.json') as jsonFile:
        jsonData = json.load(jsonFile)
    
    with open('config-scaling.json') as jsonFile:
        scaleData = json.load(jsonFile)

    #overwrite with args
    helpText = f"""scaling-mamico-multimd.py
              --runScripts <1/0, default 0>
              """

    # input: run y/n
    try:
        opts, args = getopt.getopt(argv, "hr:", ["help","runScripts="])
    except:
        print(helpText)
        sys.exit(2)
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            print(helpText)
            sys.exit()
        elif opt in ("-r", "--runScripts"):
            scaleData["runScripts"] = bool(arg)
    
    # create master folder name
    folderName = "s" + str(jsonData["scenario"]["boxSize"]) + "d" + str(jsonData["scenario"]["dropDia"]) + "t" + str(jsonData["scenario"]["temperature"]).replace('.','_')
    startPath = os.getcwd()
    masterFolder = os.path.join(startPath,scaleData["masterPath"],folderName)
    
    # create config folders
    numMultiMD = [2**x for x in range(scaleData["scaleStart"],scaleData["scaleSteps"])]
    numMultiMDFolders = zeroPad(numMultiMD)
    checkMakeFolder(masterFolder, True)
    
    # copy over common objects
    shutil.copy(os.path.join(jsonData['paths']['output'],'components.xml'), os.path.join(masterFolder,'components.xml'))
    shutil.copy(os.path.join(jsonData['paths']['output'],'mixing_2c.xml'), os.path.join(masterFolder,'mixing_2c.xml'))
    #shutil.copy(os.path.join(jsonData['paths']['output'],'vle','cp_binary_droplet-1.restart.header.xml'), os.path.join(masterFolder,'cp_binary_droplet-1.restart.header.xml'))
    #shutil.copy(os.path.join(jsonData['paths']['output'],'vle','cp_binary_droplet-1.restart.dat'), os.path.join(masterFolder,'cp_binary_droplet-1.restart.dat'))

    for config in scaleData["configs"]:
        configFolder = os.path.join(masterFolder, config["name"])
        # create strong scaling
        checkMakeFolder(os.path.join(configFolder,"strong"))
        for i in range(len(numMultiMD)):
            checkMakeFolder(os.path.join(configFolder,"strong",numMultiMDFolders[i]))
            # make couette.xml
            # copy ls1config
            # make jobscript
        # create weak scaling
        checkMakeFolder(os.path.join(configFolder,"weak"))
        for i in range(len(numMultiMD)):
            checkMakeFolder(os.path.join(configFolder,"weak",numMultiMDFolders[i]))

if __name__ == '__main__':
    main(sys.argv[1:])
