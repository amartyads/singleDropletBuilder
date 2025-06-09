#! /usr/bin/env python3

import sys, getopt, os, json, shutil
import xml.etree.cElementTree as ET

CUR_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(CUR_DIR))
from helperscripts.ljts import sat_vrabec2006
from helperscripts.utils import strtobool,convertJsonLBtols1XML,convertLBRowtoMamicoRow,checkMakeFolder
# input: scenario size, droplet diameter, autopas/ls1, 100save y/n, mamico y/n
# create folders
# calculate density
# edit components
# copy mixing
# edit liq (ls1/autop)
# edit vap (ls1/autop)
# edit vle100 (ls1/autop)
# edit vle (ls1/autop) (mamico y/n)
# add mamico

#skeletons

jsonData = ''

autopasText = """
<datastructure type="AutoPas">
    <allowedContainers>linkedCells</allowedContainers>
    <allowedTraversals>sli</allowedTraversals>
    <dataLayout>SoA</dataLayout>
    <newton3>enabled</newton3>
</datastructure>
"""

lcText = """
<datastructure type="LinkedCells">
    <cellsInCutoffRadius>1</cellsInCutoffRadius>
</datastructure>
"""

autoPXML = ET.fromstring(autopasText)
lcXML = ET.fromstring(lcText)

def doCommonXMLChanges(tree, ts, builder):
    tree.find('simulation/ensemble/temperature').text = str(jsonData['scenario']['temperature'])
    tree.find('simulation/algorithm/cutoffs/defaultCutoff').text = str(jsonData['component']['sigma'] * 2.5)
    tree.find('simulation/algorithm/cutoffs/radiusLJ').text = str(jsonData['component']['sigma'] * 2.5)
    tree.find('simulation/run/production/steps').text = str(ts)
    for plugin in tree.findall('simulation/output/outputplugin'):
        if plugin.attrib['name'] == 'CheckpointWriter':
            plugin.find('writefrequency').text = str(ts)
    tree.find('simulation/algorithm').remove(tree.find('simulation/algorithm/datastructure'))
    if builder:
        if(jsonData['stack']['autopasPrep']):
            tree.find('simulation/algorithm').append(autoPXML)
        else:
            tree.find('simulation/algorithm').append(lcXML)
    else:
        if(jsonData['stack']['autopasProd']):
            tree.find('simulation/algorithm').append(autoPXML)
        else:
            tree.find('simulation/algorithm').append(lcXML)

    return tree


def main(argv):
    #load from json
    global jsonData
    with open('config.json') as jsonFile:
        jsonData = json.load(jsonFile)

    #overwrite with args
    helpText = f"""create-droplet-config.py
              --boxSize <size of box in nm>
              --dropDia <droplet diameter in nm>
              --temp <temperature in reduced>
              --buildCP <create final checkpoint with 100 timesteps y/n>
              --mamico <mamico enabled y/n>
              --destination <destination folder, default {jsonData['paths']['output']}
              --jobSys <job system, pbs or slurm>
              """

    # input: scenario size, droplet diameter, autopas/ls1, 100save y/n, mamico y/n
    try:
        opts, args = getopt.getopt(argv, "hs:d:t:b:m:o:j:", ["help","boxSize=","dropDia=","temp=","buildCP=","mamico=","destination=","jobSys="])
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
        elif opt in ("-b", "--buildCP"):
            jsonData['scenario']['buildCP'] = strtobool(arg)
        elif opt in ("-m", "--mamico"):
            jsonData['stack']['mamico'] = strtobool(arg)
        elif opt in ("-o", "--destination"):
            jsonData['paths']['output'] = arg
        elif opt in ("-j", "--jobSys"):
            if arg in ("pbs","slurm"):
                jsonData['job']['manager'] = arg
            else:
                print(helpText)
                sys.exit(2)
    
    #calculate density
    Re=(jsonData['scenario']['dropDia']*10/2.)/jsonData['component']['sigma']       #calculate reduced radius of droplet
    t=jsonData['scenario']['temperature']/jsonData['component']['epsilon']    #calculate reduced temperature
    rhol,rhov,_=sat_vrabec2006(t, Re) #get reduced densities
    rhol=(rhol/(jsonData['component']['sigma']**3))            #convert rho into non reduced
    rhov=(rhov/(jsonData['component']['sigma']**3))
    print('Droplet diameter: ' + str(jsonData['scenario']['dropDia']) + ' nm\nLiquid density: ' + str(rhol) + '\nVapour density: ' +str(rhov))

    print(jsonData)

    #create folders
    
    checkMakeFolder(os.path.join(jsonData['paths']['output'],'liq'))
    checkMakeFolder(os.path.join(jsonData['paths']['output'],'vap'))
    checkMakeFolder(os.path.join(jsonData['paths']['output'],'vle'))
    if jsonData['stack']['mamico']:
        checkMakeFolder(os.path.join(jsonData['paths']['output'],'coupled'))
    
    # extra xmls
    adiosText = f"""
        <outputplugin name="Adios2Writer">
            <outputfile>{jsonData['adiosOutput']['filename']}</outputfile>
            <adios2enginetype>BP4</adios2enginetype>
            <writefrequency>{jsonData['adiosOutput']['frequency']}</writefrequency>
        </outputplugin>
    """
    adiosXML = ET.fromstring(adiosText)

    dropletCPText = f"""
        <outputplugin name="CheckpointWriter">
            <type>binary</type>
            <writefrequency>{jsonData['scenario']['timestepsDropBuild']}</writefrequency>
            <outputprefix>cp_binary_droplet</outputprefix>
        </outputplugin>
    """
    cpXML = ET.fromstring(dropletCPText)

    mamicoText = f"""
    <plugin name="MamicoCoupling">
    </plugin>
    """
    mamicoXML = ET.fromstring(mamicoText)

    #edit components
    treeF = ET.parse('./helperxmls/components.xml')
    tree = treeF.getroot()
    for molecule in tree.iter('moleculetype'):
        molecule.find('site/mass').text = str(jsonData['component']['mass'])
        molecule.find('site/sigma').text = str(jsonData['component']['sigma'])
        molecule.find('site/epsilon').text = str(jsonData['component']['epsilon'])
    treeF.write(os.path.join(jsonData['paths']['output'],'components.xml'), encoding='UTF-8', xml_declaration=True)

    #copy mixing
    shutil.copy('./helperxmls/mixing_2c.xml', os.path.join(jsonData['paths']['output'],'mixing_2c.xml'))
    
    #edit liq 1
    treeF = ET.parse('./helperxmls/liq/config_1_generateLiq.xml')
    tree = treeF.getroot()
    
    tree = doCommonXMLChanges(tree, jsonData['scenario']['timestepsGen'], True)
    tree.find('simulation/ensemble/phasespacepoint/generator/density').text = str(round(rhol,6))

    ET.indent(tree, '  ')
    treeF.write(os.path.join(jsonData['paths']['output'],'liq','config_1_generateLiq.xml'), encoding='UTF-8', xml_declaration=True)

    #edit liq 2
    treeF = ET.parse('./helperxmls/liq/config_2_replicateLiq.xml')
    tree = treeF.getroot()
    
    tree = doCommonXMLChanges(tree, jsonData['scenario']['timestepsRep'], True)
    tree.find('simulation/ensemble/domain/lx').text = str(jsonData['scenario']['dropDia'])
    tree.find('simulation/ensemble/domain/ly').text = str(jsonData['scenario']['dropDia'])
    tree.find('simulation/ensemble/domain/lz').text = str(jsonData['scenario']['dropDia'])
    tree.find('simulation/ensemble/phasespacepoint/generator/objectgenerator/object/upper/x').text = str(jsonData['scenario']['dropDia'])
    tree.find('simulation/ensemble/phasespacepoint/generator/objectgenerator/object/upper/y').text = str(jsonData['scenario']['dropDia'])
    tree.find('simulation/ensemble/phasespacepoint/generator/objectgenerator/object/upper/z').text = str(jsonData['scenario']['dropDia'])

    ET.indent(tree, '  ')
    treeF.write(os.path.join(jsonData['paths']['output'],'liq','config_2_replicateLiq.xml'), encoding='UTF-8', xml_declaration=True)

    #edit vap 1
    treeF = ET.parse('./helperxmls/vap/config_3_generateVap.xml')
    tree = treeF.getroot()
    
    tree = doCommonXMLChanges(tree, jsonData['scenario']['timestepsGen'], True)
    tree.find('simulation/ensemble/phasespacepoint/generator/density').text = str(round(rhov,6))

    ET.indent(tree, '  ')
    treeF.write(os.path.join(jsonData['paths']['output'],'vap','config_3_generateVap.xml'), encoding='UTF-8', xml_declaration=True)

    #edit vap 2
    treeF = ET.parse('./helperxmls/vap/config_4_replicateVap.xml')
    tree = treeF.getroot()
    
    tree = doCommonXMLChanges(tree, jsonData['scenario']['timestepsRep'], True)
    tree.find('simulation/ensemble/domain/lx').text = str(jsonData['scenario']['boxSize'])
    tree.find('simulation/ensemble/domain/ly').text = str(jsonData['scenario']['boxSize'])
    tree.find('simulation/ensemble/domain/lz').text = str(jsonData['scenario']['boxSize'])
    tree.find('simulation/ensemble/phasespacepoint/generator/objectgenerator/object/upper/x').text = str(jsonData['scenario']['boxSize'])
    tree.find('simulation/ensemble/phasespacepoint/generator/objectgenerator/object/upper/y').text = str(jsonData['scenario']['boxSize'])
    tree.find('simulation/ensemble/phasespacepoint/generator/objectgenerator/object/upper/z').text = str(jsonData['scenario']['boxSize'])

    ET.indent(tree, '  ')
    treeF.write(os.path.join(jsonData['paths']['output'],'vap','config_4_replicateVap.xml'), encoding='UTF-8', xml_declaration=True)

    #edit vle
    treeF = ET.parse('./helperxmls/vle/config_5_droplet.xml')
    tree = treeF.getroot()

    if jsonData['scenario']['buildCP']:
        tree = doCommonXMLChanges(tree, jsonData['scenario']['timestepsDropBuild'], True)
        tree.find('simulation/output').append(cpXML)
        tree.find('loglevel').text = "INFO"
    else:
        tree = doCommonXMLChanges(tree, jsonData['scenario']['timestepsProd'], False)
        if jsonData['adiosOutput']['enabled']:
            tree.find('simulation/output').append(adiosXML)
        if jsonData['stack']['mamico']:
            tree.find('simulation').append(mamicoXML)
            tree.find('loglevel').text = "ERROR"
        else:
            tree.find('loglevel').text = "INFO"

    if jsonData['lb']['enabled']:
        tree.find('simulation/algorithm/parallelisation').attrib['type'] = "StaticIrregDomainDecomposition"
        tree.find('simulation/algorithm/parallelisation').append(convertJsonLBtols1XML(jsonData['lb']['ratios']))

    tree.find('simulation/ensemble/domain/lx').text = str(jsonData['scenario']['boxSize'])
    tree.find('simulation/ensemble/domain/ly').text = str(jsonData['scenario']['boxSize'])
    tree.find('simulation/ensemble/domain/lz').text = str(jsonData['scenario']['boxSize'])
    
    objects = tree.findall('simulation/ensemble/phasespacepoint/generator/objectgenerator/object')
    
    # first should be subtractor, next sphere
    # obj 1
    objects[0].find('object1/lower/x').text = str(0)
    objects[0].find('object1/lower/y').text = str(0)
    objects[0].find('object1/lower/z').text = str(0)
    objects[0].find('object1/upper/x').text = str(jsonData['scenario']['boxSize'])
    objects[0].find('object1/upper/y').text = str(jsonData['scenario']['boxSize'])
    objects[0].find('object1/upper/z').text = str(jsonData['scenario']['boxSize'])

    objects[0].find('object2/center/x').text = str(jsonData['scenario']['boxSize'] / 2)
    objects[0].find('object2/center/y').text = str(jsonData['scenario']['boxSize'] / 2)
    objects[0].find('object2/center/z').text = str(jsonData['scenario']['boxSize'] / 2)
    objects[0].find('object2/radius').text = str(jsonData['scenario']['dropDia'] / 2 + jsonData['component']['sigma'])

    # obj 2
    objects[1].find('center/x').text = str(jsonData['scenario']['boxSize'] / 2)
    objects[1].find('center/y').text = str(jsonData['scenario']['boxSize'] / 2)
    objects[1].find('center/z').text = str(jsonData['scenario']['boxSize'] / 2)
    objects[1].find('radius').text = str(jsonData['scenario']['dropDia'] / 2)

    ET.indent(tree, '  ')
    treeF.write(os.path.join(jsonData['paths']['output'],'vle','config_5_droplet.xml'), encoding='UTF-8', xml_declaration=True)

    # edit vle100
    if jsonData['scenario']['buildCP']:
        treeF = ET.parse('./helperxmls/vle/config_6_dropletLoad.xml')
        tree = treeF.getroot()
        tree = doCommonXMLChanges(tree, jsonData['scenario']['timestepsProd'], False)
        tree.find('simulation/ensemble/domain/lx').text = str(jsonData['scenario']['boxSize'])
        tree.find('simulation/ensemble/domain/ly').text = str(jsonData['scenario']['boxSize'])
        tree.find('simulation/ensemble/domain/lz').text = str(jsonData['scenario']['boxSize'])
        if jsonData['adiosOutput']['enabled']:
            tree.find('simulation/output').append(adiosXML)
        if jsonData['stack']['mamico']:
            tree.find('simulation').append(mamicoXML)
            tree.find('loglevel').text = "ERROR"
        else:
            tree.find('loglevel').text = "INFO"
        if jsonData['lb']['enabled']:
            tree.find('simulation/algorithm/parallelisation').attrib['type'] = "StaticIrregDomainDecomposition"
            tree.find('simulation/algorithm/parallelisation').append(convertJsonLBtols1XML(jsonData['lb']['ratios']))
        ET.indent(tree, '  ')
        treeF.write(os.path.join(jsonData['paths']['output'],'vle','config_6_dropletLoad.xml'), encoding='UTF-8', xml_declaration=True)

    # add mamico
    if jsonData['stack']['mamico']:
        # copy ls1
        if jsonData['scenario']['buildCP']:
            shutil.copy(os.path.join(jsonData['paths']['output'],'vle','config_6_dropletLoad.xml'), os.path.join(jsonData['paths']['output'],'coupled','ls1config.xml'))
        else:
            shutil.copy(os.path.join(jsonData['paths']['output'],'vle','config_5_droplet.xml'), os.path.join(jsonData['paths']['output'],'coupled','ls1config.xml'))
        
        # edit mamico
        treeF = ET.parse('./helperxmls/couette.xml')
        tree = treeF.getroot()
        tree.find("couette-test/domain").attrib["channelheight"] = str(jsonData['scenario']['boxSize'] + 40)
        tree.find("couette-test/coupling").attrib["coupling-cycles"] = str(jsonData['scenario']['mamicoCyc'])

        tree.find("couette-test/microscopic-solver").attrib["temperature"] = str(jsonData['scenario']['temperature'])
        tree.find("couette-test/microscopic-solver").attrib["number-md-simulations"] = str(jsonData['scenario']['mamicoNumMultiMD'])
        tree.find("couette-test/microscopic-solver").attrib["density"] = str(rhov)

        tree.find("mamico/coupling-cell-configuration").attrib["cell-size"] = "{0} ; {0} ; {0}".format(str(jsonData['scenario']['mamicoCellsize']))
        tree.find("mamico/boundary-force").attrib["density"] = str(rhov)
        tree.find("mamico/boundary-force").attrib["temperature"] = str(jsonData['scenario']['temperature'])

        tree.find("molecular-dynamics/molecule-configuration").attrib["mass"] = str(jsonData['component']['mass'])
        tree.find("molecular-dynamics/molecule-configuration").attrib["sigma"] = str(jsonData['component']['sigma'])
        tree.find("molecular-dynamics/molecule-configuration").attrib["epsilon"] = str(jsonData['component']['epsilon'])
        tree.find("molecular-dynamics/molecule-configuration").attrib["temperature"] = str(jsonData['scenario']['temperature'])

        if jsonData['lb']['enabled']:
            tree.find("molecular-dynamics/domain-decomp-configuration").attrib["decomposition-type"] = "static-irreg-rect-grid"
            tree.find("molecular-dynamics/domain-decomp-configuration").attrib["x"] = convertLBRowtoMamicoRow(jsonData["lb"]["ratios"][0])
            tree.find("molecular-dynamics/domain-decomp-configuration").attrib["y"] = convertLBRowtoMamicoRow(jsonData["lb"]["ratios"][1])
            tree.find("molecular-dynamics/domain-decomp-configuration").attrib["z"] = convertLBRowtoMamicoRow(jsonData["lb"]["ratios"][2])
            tree.find("molecular-dynamics/mpi-configuration").attrib["number-of-processes"] = \
                convertLBRowtoMamicoRow([len(jsonData["lb"]["ratios"][0]), len(jsonData["lb"]["ratios"][1]), len(jsonData["lb"]["ratios"][2])])
            
        else:
            tree.find("molecular-dynamics/domain-decomp-configuration").attrib["decomposition-type"] = "default"
        
        tree.find("molecular-dynamics/simulation-configuration").attrib["number-of-timesteps"] = str(jsonData['scenario']['mamicoMDper'])

        molPerD = rhov*(jsonData['scenario']['boxSize']**3)
        molPerD = round(molPerD**(1./3.))

        tree.find("molecular-dynamics/domain-configuration").attrib["molecules-per-direction"] = "{0} ; {0} ; {0}".format(str(molPerD))
        tree.find("molecular-dynamics/domain-configuration").attrib["domain-size"] = "{0} ; {0} ; {0}".format(str(jsonData['scenario']['boxSize']))
        tree.find("molecular-dynamics/domain-configuration").attrib["domain-offset"] = "{0} ; {0} ; {0}".format(str(20))
        tree.find("molecular-dynamics/domain-configuration").attrib["cutoff-radius"] = str(jsonData['component']['sigma'] * 2.5)

        ET.indent(tree, '  ')
        treeF.write(os.path.join(jsonData['paths']['output'],'coupled','couette.xml'), encoding='UTF-8', xml_declaration=True)

if __name__ == '__main__':
    main(sys.argv[1:])
