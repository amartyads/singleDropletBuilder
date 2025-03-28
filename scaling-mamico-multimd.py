#! /usr/bin/env python3

# create folders
# strong scaling
# weak scaling

import json, sys, getopt, subprocess, shlex, os, shutil, yaml

import xml.etree.cElementTree as ET

CUR_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(CUR_DIR))
from helperscripts.utils import strtobool,getPartition,convertLBRowtoMamicoRow,zeroPad

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
    
    with open('job-snips.yaml','r') as file:
        jobSnips = yaml.safe_load(file)

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
            scaleData["runScripts"] = strtobool(arg)
    
    # edit jobscript things
    header = jobSnips["manager"][jsonData["job"]["manager"]]["header"]
    dependency = jobSnips["manager"][jsonData["job"]["manager"]]["dependency"]
    dependencySep = jobSnips["manager"][jsonData["job"]["manager"]]["dependencySep"]

    modules = jobSnips["system"][jsonData["job"]["system"]]["modules"]
    runComm = jobSnips["system"][jsonData["job"]["system"]]["runComm"]
    exec = jobSnips["system"][jsonData["job"]["system"]]["exec"]

    runComm = runComm.replace("<execPath>",jsonData["paths"]["mamicoExec"]).replace("<configFile>",'')

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
    shutil.copy(os.path.join(jsonData['paths']['output'],'coupled','couette.xml'), os.path.join(masterFolder,'maincouette.xml'))
    shutil.copy(os.path.join(jsonData['paths']['output'],'coupled','ls1config.xml'), os.path.join(masterFolder,'mainls1config.xml'))

    # edit ls1 for filepaths
    treeF = ET.parse(os.path.join(masterFolder, 'mainls1config.xml'))
    tree = treeF.getroot()
    for tag in tree.findall(".//include"):
        if tag.attrib["query"] == "/components/moleculetype":
            tag.text = os.path.join(masterFolder,'components.xml')
        if tag.attrib["query"] == "/mixing":
            tag.text = os.path.join(masterFolder,'mixing_2c.xml')
    tree.find("simulation/ensemble/phasespacepoint/file/header").text = os.path.join(masterFolder,'cp_binary_droplet-1.restart.header.xml')
    tree.find("simulation/ensemble/phasespacepoint/file/data").text = os.path.join(masterFolder,'cp_binary_droplet-1.restart.dat')
    tree.find('simulation/algorithm/parallelisation').attrib['type'] = "StaticIrregDomainDecomposition"
    for parent in tree.findall('simulation/algorithm/parallelisation'):
        for child in parent.findall('subdomainWeights'):
            parent.remove(child)
    ET.indent(tree, '  ')
    treeF.write(os.path.join(masterFolder, 'mainls1config.xml'), encoding='UTF-8', xml_declaration=True)

    # create configs
    for config in scaleData["configs"]:
        configFolder = os.path.join(masterFolder, config["name"])

        treeF = ET.parse(os.path.join(masterFolder, 'maincouette.xml'))
        tree = treeF.getroot()
        tree.find("couette-test/coupling").attrib["coupling-cycles"] = str(scaleData['mamicoCyc'])
        tree.find("molecular-dynamics/domain-decomp-configuration").attrib["decomposition-type"] = "static-irreg-rect-grid"
        tree.find("molecular-dynamics/domain-decomp-configuration").attrib["x"] = convertLBRowtoMamicoRow(config["ratios"][0])
        tree.find("molecular-dynamics/domain-decomp-configuration").attrib["y"] = convertLBRowtoMamicoRow(config["ratios"][1])
        tree.find("molecular-dynamics/domain-decomp-configuration").attrib["z"] = convertLBRowtoMamicoRow(config["ratios"][2])
        # create strong scaling
        # strong scaling: same problem size, more resources
        checkMakeFolder(os.path.join(configFolder,"strong"))
        for i in range(len(numMultiMD)):
            checkMakeFolder(os.path.join(configFolder,"strong",numMultiMDFolders[i]))
            os.chdir(os.path.join(configFolder,"strong",numMultiMDFolders[i]))
            # make couette.xml
            tree.find("couette-test/microscopic-solver").attrib["number-md-simulations"] = str(max(numMultiMD))
            ET.indent(tree, '  ')
            treeF.write('couette.xml', encoding='UTF-8', xml_declaration=True)
            # copy ls1config
            shutil.copy(os.path.join(masterFolder,'mainls1config.xml'),'ls1config.xml')
            # make jobscript
            with open("job.sh", 'w') as job:
                tempheader = header.replace("<wallTime>","01:00:00")
                tempheader = tempheader.replace("<numNodes>",str(numMultiMD[i]))
                tempheader = tempheader.replace("<partition>",getPartition(jsonData["job"]["system"],numMultiMD[i]))
                tempheader = tempheader.replace("<jobName>","strong-"+str(numMultiMDFolders[i]))
                job.write(tempheader)
                job.write(modules)
                job.write(jobSnips["common"]["preRun"].replace('<workDir>',os.getcwd()))
                job.write(runComm.replace("<execPath>",jsonData["paths"]["mamicoExec"]).replace("<configFile>",''))
                job.write(jobSnips["common"]["postRun"])
            if scaleData["runScripts"]:
                print("Submitting: " + os.getcwd() + "/job.sh")
                subprocess.run(shlex.split(exec), stdout=subprocess.PIPE).stdout.decode('utf-8').rstrip()
            os.chdir(masterFolder)


        # create weak scaling
        # weak scaling: same problem size per resource
        checkMakeFolder(os.path.join(configFolder,"weak"))
        for i in range(len(numMultiMD)):
            checkMakeFolder(os.path.join(configFolder,"weak",numMultiMDFolders[i]))
            # make couette.xml
            tree.find("couette-test/microscopic-solver").attrib["number-md-simulations"] = str(numMultiMD[i])
            ET.indent(tree, '  ')
            treeF.write(os.path.join(configFolder,"weak",numMultiMDFolders[i],'couette.xml'), encoding='UTF-8', xml_declaration=True)
            # copy ls1config
            shutil.copy(os.path.join(masterFolder,'mainls1config.xml'),os.path.join(configFolder,"weak",numMultiMDFolders[i],'ls1config.xml'))
            # make jobscript
        

if __name__ == '__main__':
    main(sys.argv[1:])
