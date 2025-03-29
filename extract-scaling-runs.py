#! /usr/bin/env python3

import os
import sys
import glob
import json
from file_read_backwards import FileReadBackwards
import datetime as dt
import pandas as pd


CUR_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(CUR_DIR))
from helperscripts.utils import zeroPad

with open('config.json') as jsonFile:
    jsonData = json.load(jsonFile)
    
with open('config-scaling.json') as jsonFile:
    scaleData = json.load(jsonFile)

folderName = "s" + str(jsonData["scenario"]["boxSize"]) + "d" + str(jsonData["scenario"]["dropDia"]) + "t" + str(jsonData["scenario"]["temperature"]).replace('.','_')
startPath = os.getcwd()
masterFolder = os.path.join(startPath,scaleData["masterPath"],folderName)

os.chdir(masterFolder)
numNodes = [2**x for x in range(scaleData["scaleStart"],scaleData["scaleSteps"])]
numNodesSymbols = zeroPad(numNodes)
runTypes = ["strong", "weak"]

rowsList = []

for config in scaleData["configs"]:
    for runType in runTypes:
        for numNode in numNodesSymbols:
            chpath = os.path.join(config["name"],runType,numNode)
            globobj = glob.glob(os.path.join(chpath,'output*'))
            line = ''
            lineWalltime = ''
            walltimeCumulative = 0.0
            if len(globobj) >= 1:
                for i in range(len(globobj)):
                    with FileReadBackwards(globobj[i], encoding="utf-8") as file:
                        for line in file:
                            if 'Finished all coupling cycles' in line:
                                lineWalltime = line
                                break
                    if lineWalltime == '':
                        print(f"Error in {globobj[i]}")
                        sys.exit(2)
                    else:
                        stringWalltime = lineWalltime[lineWalltime.find('after ')+5:-1].strip()
                        walltimeCumulative += float(stringWalltime)
            else:
                print(f"Error in {globobj[i]}")
                sys.exit(2)
            dict = {'Folder':chpath,'Config':scaleData["configs"],'RunType':runType,'NumNodes':numNodes,'CumulativeWalltime':walltimeCumulative,'NoOutputs':len(globobj),'AvgWalltime':walltimeCumulative/len(globobj)}
            rowsList.append(dict)

df = pd.DataFrame(rowsList, columns=['Folder','Config','RunType','NumNodes','CumulativeWalltime','NoOutputs','AvgWalltime'])
df.set_index('Folder', inplace=True)
print(df)
df.to_csv('./outputs'+ folderName +'.csv')
