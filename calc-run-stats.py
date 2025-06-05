#! /usr/bin/env python3

import pandas as pd
from pathlib import Path
import glob
import numpy as np
import matplotlib
from matplotlib import pyplot as plt, ticker as mticker
import os,sys

CUR_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(CUR_DIR))

files = glob.glob(f'../*outputs*/*120*.csv')
configTypes = ['default','balance7_5_1D','balance7_5']
# Things to calculate:
# 1. Node hours and core hours
# 2. % speedup

totNodeHoursStrong = 0
totNodeHoursWeak = 0

# 1. Node hours and core hours
for file in files:
    df = pd.read_csv(file)
    
    dfstrong = df[df["RunType"] == 'strong'].copy()
    totTime = (dfstrong['CumulativeWalltime'] * dfstrong['NumNodes']).sum()
    print(f"For file {file} strong node seconds: {totTime}")
    totNodeHoursStrong += totTime
    
    dfweak = df[df["RunType"] == 'weak'].copy()
    totTime = (dfweak['CumulativeWalltime'] * dfweak['NumNodes']).sum()
    print(f"For file {file} weak node seconds: {totTime}")
    totNodeHoursWeak += totTime

#totNodeHoursStrong /= (60*60)
#totNodeHoursWeak /= (60*60)

print(f"Total strong node hours: {totNodeHoursStrong/(60*60)}")
print(f"Total weak node hours: {totNodeHoursWeak/(60*60)}")
print(f"Total strong core hours: {(totNodeHoursStrong*128)/(60*60)}")
print(f"Total weak core hours: {(totNodeHoursWeak*128)/(60*60)}")

print('----------------------------------------------------------')

# 2. % speedup
speedupDict = dict(zip(configTypes, ['0']* len(configTypes)))
files = glob.glob(f'../*outputs-par*/*120*.csv')
for file in files:
    df = pd.read_csv(file)
    
    dfstrong = df[df["RunType"] == 'strong'].copy()
    norbtimes = dfstrong.loc[(dfstrong["Config"] == configTypes[0]),'AvgWalltime'].values
    for conf in configTypes:
        dfstrong.loc[(dfstrong["Config"] == conf), 'Speedup'] = norbtimes/dfstrong.loc[(dfstrong["Config"] == conf), 'AvgWalltime']
        speedupDict[conf] = f"{dfstrong.loc[(dfstrong["Config"] == conf), 'Speedup'].mean()} + {dfstrong.loc[(dfstrong["Config"] == conf), 'Speedup'].std()}"

    print(f"Strong speedups for {file} : {speedupDict}")
    
for file in files:
    df = pd.read_csv(file)
    dfweak = df[df["RunType"] == 'weak'].copy()
    norbtimes = dfweak.loc[(dfweak["Config"] == configTypes[0]),'AvgWalltime'].values
    for conf in configTypes:
        dfweak.loc[(dfweak["Config"] == conf), 'Speedup'] = norbtimes/dfweak.loc[(dfweak["Config"] == conf), 'AvgWalltime']
        speedupDict[conf] = f"{dfweak.loc[(dfweak["Config"] == conf), 'Speedup'].mean()} + {dfweak.loc[(dfweak["Config"] == conf), 'Speedup'].std()}"

    print(f"Weak speedups for {file} : {speedupDict}")
