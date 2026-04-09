import heapq
import math
from .core import getparentstateidfromprovinceid, getshapecenter, rectanglesclose
from .events import EngineEventType


terrainmovecostlookup = {
    "plains": 1.0,
    "forest": 1.25,
    "hills": 1.35,
    "mountains": 1.8,
    "desert": 1.2,
    "swamp": 1.5,
    "urban": 1.1,
}




def getprovincecontroller(province):
    return province.get("controllercountry", province.get("country"))


def getprovinceowner(province):
    return province.get("ownercountry", province.get("country"))


def setprovincecontroller(province, countryname, countrycolor=None):
    province["controllercountry"] = countryname
    province["country"] = countryname
    if countrycolor is not None:
        province["countrycolor"] = countrycolor


def prepareprovincemetadata(provincelist):
    enrichedlist = []
    for province in provincelist:
        enrichedprovince = dict(province)
        enrichedprovince["parentstateid"] = getparentstateidfromprovinceid(enrichedprovince["id"])
        enrichedprovince["terrain"] = "plains"
        enrichedprovince["troops"] = 0
        enrichedprovince["center"] = getshapecenter(enrichedprovince)
        enrichedprovince["ownercountry"] = None
        enrichedprovince["controllercountry"] = None
        enrichedprovince["country"] = None
        enrichedlist.append(enrichedprovince)
    return enrichedlist


def buildprovinceadjacencygraph(provincemap, onprogress=None):
    provinceidlist = list(provincemap.keys())
    totalprovincecount = len(provinceidlist)
    totalprogresssteps = max(1, totalprovincecount * 2)
    if onprogress and not onprogress(0, totalprogresssteps):
        return None
    gridcellsize = 32.0
    adjacencytestpadding = 1
    gridlookup = {}
    provinceentrylist = []
    for provinceindex, provinceid in enumerate(provinceidlist):
        provincerectangle = provincemap[provinceid]["rectangle"]
        minimumgridx = int(math.floor((provincerectangle.left - adjacencytestpadding) / gridcellsize))
        maximumgridx = int(math.floor((provincerectangle.right + adjacencytestpadding) / gridcellsize))
        minimumgridy = int(math.floor((provincerectangle.top - adjacencytestpadding) / gridcellsize))
        maximumgridy = int(math.floor((provincerectangle.bottom + adjacencytestpadding) / gridcellsize))
        provinceentrylist.append((provinceid, provincerectangle, minimumgridx, maximumgridx, minimumgridy, maximumgridy))
        for gridx in range(minimumgridx, maximumgridx + 1):
            for gridy in range(minimumgridy, maximumgridy + 1):
                gridlookup.setdefault((gridx, gridy), []).append(provinceindex)

        if onprogress and (provinceindex == 0 or (provinceindex + 1) % 200 == 0 or (provinceindex + 1) == totalprovincecount):
            if not onprogress(provinceindex + 1, totalprogresssteps):
                return None
    adjacencygraph = {provinceid: set() for provinceid in provinceidlist}
    for provinceindex, provinceentry in enumerate(provinceentrylist):
        provinceid, firstrectangle, minimumgridx, maximumgridx, minimumgridy, maximumgridy = provinceentry
        candidateindexset = set()

        for gridx in range(minimumgridx, maximumgridx + 1):
            for gridy in range(minimumgridy, maximumgridy + 1):
                for candidateindex in gridlookup.get((gridx, gridy), ()):
                    if candidateindex > provinceindex:
                        candidateindexset.add(candidateindex)

        for candidateindex in candidateindexset:
            candidateprovinceid, secondrectangle, _, _, _, _ = provinceentrylist[candidateindex]
            if rectanglesclose(firstrectangle, secondrectangle, padding=adjacencytestpadding):
                adjacencygraph[provinceid].add(candidateprovinceid)
                adjacencygraph[candidateprovinceid].add(provinceid)

        if onprogress and (provinceindex == 0 or (provinceindex + 1) % 100 == 0 or (provinceindex + 1) == totalprovincecount):
            if not onprogress(totalprovincecount + provinceindex + 1, totalprogresssteps):
                return None

    return adjacencygraph





def getterrainmovecost(province):
    return terrainmovecostlookup.get(province.get("terrain", "plains"), 1.0)





def findprovincepath(startprovinceid, goalprovinceid, provincemap, provincegraph, allowedprovinceidset=None):
    if startprovinceid not in provincemap or goalprovinceid not in provincemap:
        return []
    if allowedprovinceidset is not None:
        if startprovinceid not in allowedprovinceidset or goalprovinceid not in allowedprovinceidset:
            return []
    if startprovinceid == goalprovinceid:
        return [startprovinceid]




    goalcenter = provincemap[goalprovinceid]["center"]
    openheap = [(0.0, startprovinceid)]
    parentlookup = {}
    costlookup = {startprovinceid: 0.0}
    visitedset = set()




    while openheap:
        _, currentprovinceid = heapq.heappop(openheap)
        if currentprovinceid in visitedset:
            continue

        if currentprovinceid == goalprovinceid:
            pathlist = [goalprovinceid]
            while pathlist[-1] in parentlookup:
                pathlist.append(parentlookup[pathlist[-1]])
            pathlist.reverse()
            return pathlist

        visitedset.add(currentprovinceid)
        currentcenter = provincemap[currentprovinceid]["center"]

        for nextprovinceid in provincegraph.get(currentprovinceid, ()):
            if allowedprovinceidset is not None and nextprovinceid not in allowedprovinceidset:
                continue
            if nextprovinceid in visitedset:
                continue

            nextcenter = provincemap[nextprovinceid]["center"]
            stepdistance = math.hypot(nextcenter[0] - currentcenter[0], nextcenter[1] - currentcenter[1])
            moveenergy = stepdistance * getterrainmovecost(provincemap[nextprovinceid])
            newcost = costlookup[currentprovinceid] + moveenergy

            if newcost >= costlookup.get(nextprovinceid, float("inf")):
                continue

            parentlookup[nextprovinceid] = currentprovinceid
            costlookup[nextprovinceid] = newcost
            estimateddistance = math.hypot(goalcenter[0] - nextcenter[0], goalcenter[1] - nextcenter[1])

            
            heapq.heappush(openheap, (newcost + estimateddistance, nextprovinceid))

    return []




def processmovementorders(movementorderlist, provincemap):
    finishedorderlist = []


    
    for movementorder in movementorderlist:



        movementpoints = 1.0 * float(movementorder.get("speedmodifier", 1.0))
        pathlist = movementorder["path"]
        currentpathindex = movementorder["index"]
        movingcountry = movementorder.get("controllercountry", movementorder.get("country"))
        movingcountrycolor = movementorder.get("countrycolor")

        while currentpathindex < len(pathlist) - 1:
            nextprovinceid = pathlist[currentpathindex + 1]
            nextprovince = provincemap[nextprovinceid]
            movecost = getterrainmovecost(nextprovince)
            if movementpoints < movecost:
                break

            if movingcountry is None:
                movingcountry = getprovincecontroller(provincemap[pathlist[currentpathindex]])
                movementorder["controllercountry"] = movingcountry
                movementorder["country"] = movingcountry

            nextcountry = getprovincecontroller(nextprovince)
            if (
                movingcountry is not None
                and nextcountry is not None
                and nextcountry != movingcountry
                and nextprovince["troops"] > 0
            ):
                attackers = movementorder["amount"]
                defenders = nextprovince["troops"]
                if attackers <= defenders:
                    nextprovince["troops"] = defenders - attackers



                    # combat resolved
                    if emit is not None:
                        emit(
                            EngineEventType.COMBATRESOLVED,
                            {
                                "provinceId": nextprovinceid,
                                "attackersBefore": attackers,
                                "defendersBefore": defenders,
                                "attackersAfter": 0,
                                "defendersAfter": nextprovince["troops"],
                            },
                        )


                    movementorder["amount"] = 0
                    break

                movementorder["amount"] = attackers - defenders
                nextprovince["troops"] = 0


                #comabt resolved
                if emit is not None:
                    emit(
                        EngineEventType.COMBATRESOLVED,
                        {
                            "provinceId": nextprovinceid,
                            "attackersBefore": attackers,
                            "defendersBefore": defenders,
                            "attackersAfter": movementorder["amount"],
                            "defendersAfter": 0,
                        },
                    )



            movementpoints -= movecost
            currentpathindex += 1

            if (
                movingcountry is not None
                and nextcountry is not None
                and nextcountry != movingcountry
                and nextprovince["troops"] <= 0
            ):
                previouscontroller = nextcountry
                setprovincecontroller(nextprovince, movingcountry, movingcountrycolor)
                if emit is not None:
                    emit(
                        EngineEventType.PROVINCECONTROLCHANGED,
                        {
                            "provinceId": nextprovinceid,
                            "previousController": previouscontroller,
                            "newController": movingcountry,
                        },
                    )

        movementorder["index"] = currentpathindex
        movementorder["current"] = pathlist[currentpathindex]

        if movementorder["amount"] <= 0:
            finishedorderlist.append(movementorder)
            if emit is not None:
                emit(
                    EngineEventType.MOVEORDERFINISHED,
                    {
                        "path": list(pathlist),
                        "finalProvinceId": pathlist[currentpathindex],
                        "remainingTroops": 0,
                        "reason": "destroyed",
                    },
                )
        elif currentpathindex >= len(pathlist) - 1:
            destinationprovinceid = pathlist[-1]
            provincemap[destinationprovinceid]["troops"] += movementorder["amount"]
            finishedorderlist.append(movementorder)

            if emit is not None:
                emit(
                    EngineEventType.MOVEORDERFINISHED,
                    {
                        "path": list(pathlist),
                        "finalProvinceId": destinationprovinceid,
                        "remainingTroops": movementorder["amount"],
                        "reason": "arrived",
                    },
                )

    for finishedorder in finishedorderlist:
        movementorderlist.remove(finishedorder)


