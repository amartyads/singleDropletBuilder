import xml.etree.cElementTree as ET

def strtobool (val):
    """Convert a string representation of truth to true (1) or false (0).
    True values are 'y', 'yes', 't', 'true', 'on', and '1'; false values
    are 'n', 'no', 'f', 'false', 'off', and '0'.  Raises ValueError if
    'val' is anything else.
    """
    val = val.lower()
    if val in ('y', 'yes', 't', 'true', 'on', '1'):
        return 1
    elif val in ('n', 'no', 'f', 'false', 'off', '0'):
        return 0
    else:
        raise ValueError("invalid truth value %r" % (val,))

def convertJsonLBtols1XML(lb):
    textXML = "<subdomainWeights>\n<x>"
    for item in lb[0]:
        textXML += str(item) + ','
    textXML = textXML[:-1]
    textXML += "</x>\n<y>"
    for item in lb[1]:
        textXML += str(item) + ','
    textXML = textXML[:-1]
    textXML += "</y>\n<z>"
    for item in lb[2]:
        textXML += str(item) + ','
    textXML = textXML[:-1]
    textXML += "</z>\n</subdomainWeights>"
    return ET.fromstring(textXML)

def convertLBRowtoMamicoRow(lb):
    ret = str(lb[0])
    for i in range(len(lb)-1):
        ret += ' ; ' + str(lb[i+1])
    return ret

def getJobID(output, cluster):
    if cluster == "hsuper":
        return output.split()[-1]
    return output

def getPartition(clusterName, numNodes):
    return ' '

def zeroPad(digits):
    maxDigs = len(str(max(digits)))
    toRet = [str(x).zfill(maxDigs) for x in digits]
    return toRet
