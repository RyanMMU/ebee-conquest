import os
import pickle
from pathlib import Path as filepathpath

from . import movement as movementmodule

# EBEE SUPER OPTIMIZATION (ESO) FUNCTIONS
esoversion = 1
esodirectory = ".ebee_super_optimization"


def getpath(sourcefilepath):
    return sourcefilepath.parent / esodirectory / f"{sourcefilepath.stem}.ebeecache_v{esoversion}.pkl"


def getnamedpath(sourcefilepath, cachelabel):
    return sourcefilepath.parent / esodirectory / f"{sourcefilepath.stem}.{cachelabel}.ebeecache_v{esoversion}.pkl"


def loadcache(filepath):
    sourcefilepath = filepathpath(filepath).resolve()
    try:
        sourcefilepath.stat()
    except OSError:
        return None

    cachefilepath = getpath(sourcefilepath)
    try:
        with open(cachefilepath, "rb") as cachefileobject:
            cacheready = pickle.load(cachefileobject)
    except OSError:
        return None

    if not isinstance(cacheready, dict):
        return None

    cachemeta = cacheready.get("meta")
    cachedshapelist = cacheready.get("shapes")
    if not isinstance(cachemeta, dict) or not isinstance(cachedshapelist, list):
        return None
    if cachemeta.get("formatversion") != esoversion:
        return None
    return cachedshapelist


def storecache(filepath, shapelist):
    sourcefilepath = filepathpath(filepath).resolve()
    try:
        sourcefilepath.stat()
    except OSError:
        return

    cachefilepath = getpath(sourcefilepath)
    temppath = cachefilepath.with_suffix(cachefilepath.suffix + ".ebeetemp")
    cacheready = {
        "meta": {"formatversion": esoversion},
        "shapes": shapelist,
    }

    try:
        cachefilepath.parent.mkdir(parents=True, exist_ok=True)
        with open(temppath, "wb") as cachefileobject:
            pickle.dump(cacheready, cachefileobject, protocol=pickle.HIGHEST_PROTOCOL)
        os.replace(temppath, cachefilepath)
    except OSError:
        try:
            if temppath.exists():
                temppath.unlink()
        except OSError:
            pass


def loadprovincegraphcache(filepath, allowedstateidset=None):
    sourcefilepath = filepathpath(filepath).resolve()
    cachefilepath = getnamedpath(sourcefilepath, "provincegraph")
    try:
        with open(cachefilepath, "rb") as cachefileobject:
            cacheready = pickle.load(cachefileobject)
    except OSError:
        return None

    if not isinstance(cacheready, dict):
        return None

    cachemeta = cacheready.get("meta")
    cachedgraph = cacheready.get("graph")
    if not isinstance(cachemeta, dict) or not isinstance(cachedgraph, dict):
        return None
    if cachemeta.get("formatversion") != esoversion or cachemeta.get("cachetype") != "provincegraph":
        return None

    expectedstateidlist = sorted(allowedstateidset) if allowedstateidset is not None else None
    if expectedstateidlist is not None and cachemeta.get("allowedstateids") != expectedstateidlist:
        return None

    normalizedgraph = {}
    for provinceid, neighborids in cachedgraph.items():
        if not isinstance(provinceid, str) or not isinstance(neighborids, (set, list, tuple)):
            return None
        try:
            normalizedgraph[provinceid] = {str(neighborid) for neighborid in neighborids}
        except Exception:
            return None
    return normalizedgraph


def storeprovincegraphcache(filepath, provincegraph, allowedstateidset=None):
    sourcefilepath = filepathpath(filepath).resolve()
    cachefilepath = getnamedpath(sourcefilepath, "provincegraph")
    temppath = cachefilepath.with_suffix(cachefilepath.suffix + ".ebeetemp")
    if not isinstance(provincegraph, dict):
        return

    serializedgraph = {}
    for provinceid, neighborids in provincegraph.items():
        if not isinstance(provinceid, str) or not isinstance(neighborids, (set, list, tuple)):
            return
        serializedgraph[provinceid] = set(neighborids)

    cacheready = {
        "meta": {
            "formatversion": esoversion,
            "cachetype": "provincegraph",
            "allowedstateids": sorted(allowedstateidset) if allowedstateidset is not None else None,
        },
        "graph": serializedgraph,
    }
    try:
        cachefilepath.parent.mkdir(parents=True, exist_ok=True)
        with open(temppath, "wb") as cachefileobject:
            pickle.dump(cacheready, cachefileobject, protocol=pickle.HIGHEST_PROTOCOL)
        os.replace(temppath, cachefilepath)
    except OSError:
        try:
            if temppath.exists():
                temppath.unlink()
        except OSError:
            pass


def updaterollingfpshistory(fpshistory, fpsvalue, maxsamples):
    fpshistory.append(float(max(0.0, fpsvalue)))
    overflowcount = len(fpshistory) - maxsamples
    if overflowcount > 0:
        del fpshistory[:overflowcount]


def buildcountryborderentries(provincemap, provinceedgepairlist, segmentcache):
    borderentrylist = []
    for firstprovinceid, secondprovinceid in provinceedgepairlist:
        firstprovince = provincemap.get(firstprovinceid)
        secondprovince = provincemap.get(secondprovinceid)
        if not firstprovince or not secondprovince:
            continue

        firstcontroller = movementmodule.getprovincecontroller(firstprovince)
        secondcontroller = movementmodule.getprovincecontroller(secondprovince)
        if firstcontroller is None or secondcontroller is None:
            continue
        if firstcontroller == secondcontroller:
            continue

        edgekey = (firstprovinceid, secondprovinceid)
        worldsegmentlist = segmentcache.get(edgekey)
        if worldsegmentlist is None:
            worldsegmentlist = movementmodule.getsharedbordersegments(
                firstprovince,
                secondprovince,
                linetolerancee=movementmodule.sharedLineTolerance,
                alignmenttolerance=movementmodule.sharedAlignmentTolerance,
                minlength=movementmodule.sharedMinLength,
            )
            segmentcache[edgekey] = worldsegmentlist

        for segmentstart, segmentend in worldsegmentlist or ():
            minx = min(segmentstart[0], segmentend[0])
            maxx = max(segmentstart[0], segmentend[0])
            miny = min(segmentstart[1], segmentend[1])
            maxy = max(segmentstart[1], segmentend[1])
            borderentrylist.append(
                {
                    "start": segmentstart,
                    "end": segmentend,
                    "minx": minx,
                    "maxx": maxx,
                    "miny": miny,
                    "maxy": maxy,
                }
            )

    return borderentrylist
