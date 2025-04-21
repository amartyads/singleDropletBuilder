#! /usr/bin/env python3

import os
import re
import sys
import glob
import json
import getopt
import pandas as pd

CUR_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(CUR_DIR))
from helperscripts.utils import zeroPad

def main(argv):
    with open('config.json') as jsonFile:
        jsonData = json.load(jsonFile)
        
    with open('config-scaling.json') as jsonFile:
        scaleData = json.load(jsonFile)
    
    #overwrite with args
    helpText = f"""extract-scaling-runs.py
              --boxSize <size of box in nm>
              --dropDia <droplet diameter in nm>
              --temp <temperature in reduced>
              """

    # input: scenario size, droplet diameter, autopas/ls1, 100save y/n, mamico y/n
    try:
        opts, args = getopt.getopt(argv, "hs:d:t:", ["help","boxSize=","dropDia=","temp="])
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

    folderName = "s" + str(jsonData["scenario"]["boxSize"]) + "d" + str(jsonData["scenario"]["dropDia"]) + "t" + str(jsonData["scenario"]["temperature"]).replace('.','_')
    startPath = os.getcwd()
    masterFolder = os.path.join(startPath,scaleData["masterPath"],folderName)

    os.chdir(masterFolder)
    numNodes = [2**x for x in range(scaleData["scaleStart"],scaleData["scaleSteps"])]
    numNodesSymbols = zeroPad(numNodes)
    runTypes = ["strong", "weak"]

    rowsList = []

    expFloatPattern=r'([+-]?(?=\.\d|\d)(?:\d+)?(?:\.?\d*))(?:[Ee]([+-]?\d+))?'
    timeBreakdownPattern = expFloatPattern + ',' + expFloatPattern + ',' + expFloatPattern + ',' + expFloatPattern
    timeBreakdownPattern = re.compile(timeBreakdownPattern, re.IGNORECASE)

    for config in scaleData["configs"]:
        for runType in runTypes:
            for numNode in numNodesSymbols:
                chpath = os.path.join(config["name"],runType,numNode)
                globobj = glob.glob(os.path.join(chpath,'output*'))
                line = ''
                lineWalltime = []
                timeBreakdown = []
                walltimeCumulative = 0.0
                microCumulative = 0.0
                macroCumulative = 0.0
                filterCumulative = 0.0
                otherCumulative = 0.0
                totNumOutputs = 0
                if len(globobj) >= 1:
                    for i in range(len(globobj)):
                        with open(globobj[i], encoding="utf-8") as file:
                            for line in file:
                                if 'Finished all coupling cycles' in line:
                                    lineWalltime.append(line)
                                if timeBreakdownPattern.search(line) != None:
                                    timeBreakdown.append(line)
                        if len(lineWalltime) == 0:
                            print(f"Error in {chpath}")
                            sys.exit(2)
                        else:
                            assert len(lineWalltime) == len(timeBreakdown)    
                else:
                    print(f"Error in {config['name']},{runType},{numNode}")
                    continue
                    #print(rowsList)
                    #sys.exit(2)
                
                totNumOutputs = len(lineWalltime)
                for i in range(len(lineWalltime)):
                    try:
                        stringWalltime = lineWalltime[i][lineWalltime[i].find('after ')+5:-2].strip()
                        walltimeCumulative += float(stringWalltime)
                        timeBreakdownLine = [float(x.strip()) for x in timeBreakdown[i].split(',')]
                        microCumulative += timeBreakdownLine[0] * float(stringWalltime) / 100.0
                        macroCumulative += timeBreakdownLine[1] * float(stringWalltime) / 100.0
                        filterCumulative += timeBreakdownLine[2] * float(stringWalltime) / 100.0
                        otherCumulative += timeBreakdownLine[3] * float(stringWalltime) / 100.0
                    except:
                        print(f"Error in {config['name']},{runType},{numNode}: stringwalltime:{lineWalltime[i]} timebreakdown:{timeBreakdown[i]}")
                        continue

                dict = {'Folder':chpath,'Config':config["name"],'RunType':runType,'NumNodes':numNode,
                        'CumulativeWalltime':walltimeCumulative,'NoOutputs':totNumOutputs,
                        'AvgWalltime':walltimeCumulative/totNumOutputs,
                        'Micro':microCumulative/totNumOutputs, 'Macro':macroCumulative/totNumOutputs,
                        'Filter':filterCumulative/totNumOutputs, 'Other':otherCumulative/totNumOutputs}
                rowsList.append(dict)

    df = pd.DataFrame(rowsList, columns=['Folder','Config','RunType','NumNodes',
                                         'CumulativeWalltime','NoOutputs','AvgWalltime', 'Micro', 'Macro',
                                         'Filter', 'Other'])
    df.set_index('Folder', inplace=True)
    print(df)
    df.to_csv('./outputs'+ folderName +'.csv')

if __name__ == '__main__':
    main(sys.argv[1:])
