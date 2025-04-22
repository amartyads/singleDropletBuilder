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
from helperscripts.utils import checkMakeFolder


colors = ['co-', 'ro-', 'go-', 'bo-', 'mo-']
colors2 = ['c--', 'r--', 'g--', 'b--', 'm--']
csvSource = "hawk-outputs-parcfd"
graphsDest = "graphs-parcfd"
files = glob.glob(f'../{csvSource}/*120*.csv')

checkMakeFolder(graphsDest, True)

fig1 = plt.figure(figsize=(6,4))
ax = fig1.add_subplot(111)

for file in files:
    df = pd.read_csv(file)
    filename = Path(file).name
    filename = filename[7:-4]
    # strong
    dfstrong = df[df["RunType"] == 'strong'].copy()
    #configTypes = dfstrong['Config'].unique()
    configTypes = ['default','balance7_5_1D','balance7_5']
    configTypesPretty = ['Default','1DB','3DB']
    numNodes = dfstrong['NumNodes'].unique()
    
    for config in configTypes:
        baseTime = dfstrong.loc[(dfstrong["Config"] == config) & (dfstrong['NumNodes'] == 1), 'AvgWalltime'].values[0]
        dfstrong.loc[(dfstrong["Config"] == config), 'IdealWalltime'] = np.divide(baseTime, numNodes)
    
    ax.cla()
    for i in range(len(configTypes)):
        ax.plot(numNodes, dfstrong.loc[dfstrong["Config"] == configTypes[i], "AvgWalltime"], colors[i], label=configTypesPretty[i])
        ax.plot(numNodes, dfstrong.loc[dfstrong["Config"] == configTypes[i], "IdealWalltime"], colors2[i], label=configTypesPretty[i]+' Ideal')
    #ax.set_xticks([x for x in range(0,numFolders)])
    ax.legend()
    ax.set_title(f'Strong scaling - Droplet diameter {filename[5:-4]}', fontsize=14)
    ax.set_xlabel('#nodes', fontsize=14)
    ax.set_ylabel('walltime (s)', fontsize=14)
    ax.set_xscale('log')
    ax.set_xticks(numNodes)
    ax.set_yscale('log')
    #ax.minorticks_on()
    #ax.xaxis.set_tick_params(which='minor', bottom=False)
    ax.get_yaxis().set_minor_locator(mticker.LogLocator(numticks=2, subs=(0.25, 0.5, 0.75)))
    ax.get_yaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
    ax.get_yaxis().set_minor_formatter(matplotlib.ticker.ScalarFormatter())
    ax.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
    ax.grid(True)
    fig1.savefig(f"{graphsDest}/{filename}strong.pdf", format="pdf", bbox_inches='tight', dpi=300)

    # weak
    dfweak = df[df["RunType"] == 'weak'].copy()
    numNodes = dfweak['NumNodes'].unique()
    
    for config in configTypes:
        baseTime = dfweak.loc[(dfweak["Config"] == config) & (dfweak['NumNodes'] == 1), 'AvgWalltime'].values[0]
        dfweak.loc[(dfweak["Config"] == config), 'IdealWalltime'] = baseTime
    
    ax.cla()
    for i in range(len(configTypes)):
        ax.plot(numNodes, dfweak.loc[dfweak["Config"] == configTypes[i], "AvgWalltime"], colors[i], label=configTypesPretty[i])
        ax.plot(numNodes, dfweak.loc[dfweak["Config"] == configTypes[i], "IdealWalltime"], colors2[i], label=configTypesPretty[i]+' Ideal')
    #ax.set_xticks([x for x in range(0,numFolders)])
    ax.legend()
    ax.set_title(f'Weak scaling - Droplet diameter {filename[5:-4]}', fontsize=14)
    ax.set_xlabel('#nodes', fontsize=14)
    ax.set_ylabel('walltime (s)', fontsize=14)
    ax.set_xscale('log')
    ax.set_xticks(numNodes)
    #ax.set_yscale('log')
    #ax.minorticks_on()
    #ax.xaxis.set_tick_params(which='minor', bottom=False)
    ax.get_yaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
    ax.get_yaxis().set_minor_formatter(matplotlib.ticker.ScalarFormatter())
    ax.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
    ax.grid(True)
    fig1.savefig(f"{graphsDest}/{filename}weak.pdf", format="pdf", bbox_inches='tight', dpi=300)