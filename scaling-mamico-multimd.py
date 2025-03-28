#! /usr/bin/env python3

# create folders
# strong scaling
# weak scaling

import json, sys, getopt, subprocess, shlex, os, shutil

import xml.etree.cElementTree as ET


def convertLBRowtoMamicoRow(lb):
    ret = str(lb[0])
    for i in range(len(lb)-1):
        ret += ' ; ' + str(lb[i+1])
    return ret

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
    shutil.copy(os.path.join(jsonData['paths']['output'],'coupled','couette.xml'), os.path.join(masterFolder,'maincouette.xml'))
    shutil.copy(os.path.join(jsonData['paths']['output'],'coupled','ls1config.xml'), os.path.join(masterFolder,'mainls1config.xml'))

    # edit ls1 for filepaths
    treeF = ET.parse(os.path.join(masterFolder, 'mainls1config.xml'))
    tree = treeF.getroot()
    for tag in tree.findall(".//include"):
        print(tag)
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

        # create strong scaling
        # strong scaling: same problem size, more resources
        checkMakeFolder(os.path.join(configFolder,"strong"))
        for i in range(len(numMultiMD)):
            checkMakeFolder(os.path.join(configFolder,"strong",numMultiMDFolders[i]))
            # make couette.xml
            treeF = ET.parse(os.path.join(masterFolder, 'maincouette.xml'))
            tree = treeF.getroot()
            tree.find("couette-test/coupling").attrib["coupling-cycles"] = str(scaleData['mamicoCyc'])
            tree.find("couette-test/microscopic-solver").attrib["number-md-simulations"] = str(max(numMultiMD))
            tree.find("molecular-dynamics/domain-decomp-configuration").attrib["decomposition-type"] = "static-irreg-rect-grid"
            tree.find("molecular-dynamics/domain-decomp-configuration").attrib["x"] = convertLBRowtoMamicoRow(config["ratios"][0])
            tree.find("molecular-dynamics/domain-decomp-configuration").attrib["y"] = convertLBRowtoMamicoRow(config["ratios"][1])
            tree.find("molecular-dynamics/domain-decomp-configuration").attrib["z"] = convertLBRowtoMamicoRow(config["ratios"][2])
            ET.indent(tree, '  ')
            treeF.write(os.path.join(configFolder,"strong",numMultiMDFolders[i],'couette.xml'), encoding='UTF-8', xml_declaration=True)
            # copy ls1config
            shutil.copy(os.path.join(masterFolder,'mainls1config.xml'),os.path.join(configFolder,"strong",numMultiMDFolders[i],'ls1config.xml'))
            # make jobscript
        
        # create weak scaling
        # weak scaling: same problem size per resource
        checkMakeFolder(os.path.join(configFolder,"weak"))
        for i in range(len(numMultiMD)):
            checkMakeFolder(os.path.join(configFolder,"weak",numMultiMDFolders[i]))
            # make couette.xml
            treeF = ET.parse(os.path.join(masterFolder, 'maincouette.xml'))
            tree = treeF.getroot()
            tree.find("couette-test/coupling").attrib["coupling-cycles"] = str(scaleData['mamicoCyc'])
            tree.find("couette-test/microscopic-solver").attrib["number-md-simulations"] = str(numMultiMD[i])
            tree.find("molecular-dynamics/domain-decomp-configuration").attrib["decomposition-type"] = "static-irreg-rect-grid"
            tree.find("molecular-dynamics/domain-decomp-configuration").attrib["x"] = convertLBRowtoMamicoRow(config["ratios"][0])
            tree.find("molecular-dynamics/domain-decomp-configuration").attrib["y"] = convertLBRowtoMamicoRow(config["ratios"][1])
            tree.find("molecular-dynamics/domain-decomp-configuration").attrib["z"] = convertLBRowtoMamicoRow(config["ratios"][2])
            ET.indent(tree, '  ')
            treeF.write(os.path.join(configFolder,"weak",numMultiMDFolders[i],'couette.xml'), encoding='UTF-8', xml_declaration=True)
            # copy ls1config
            shutil.copy(os.path.join(masterFolder,'mainls1config.xml'),os.path.join(configFolder,"weak",numMultiMDFolders[i],'ls1config.xml'))
            # make jobscript
        

if __name__ == '__main__':
    main(sys.argv[1:])
