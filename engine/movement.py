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


entrenchmentturnrequired = 3
entrenchmentdefensemultiplier = 1.33


# Keep border rendering/selection aligned with adjacency builder tolerances.
sharedLineTolerance = 0.9
sharedAlignmentTolerance = 0.16
sharedMinLength = 0.48 * 0.4


def getprovincecontroller(province):
    # get the current controller
    return province.get("controllercountry", province.get("country"))


def getprovinceowner(province):
    # get the original owner
    return province.get("ownercountry", province.get("country"))


def setprovincecontroller(province, countryname, countrycolor=None):
    #set the controller of the provincewhen occupied or annexed
    province["controllercountry"] = countryname
    province["country"] = countryname
    if countrycolor is not None:
        province["countrycolor"] = countrycolor


def markprovincetroopactivity(province, currentturnnumber):
    if currentturnnumber is None or province is None:
        return
    province["lasttroopactivityturn"] = int(currentturnnumber)


def getprovinceentrenchmentturns(province, currentturnnumber):
    if province is None or currentturnnumber is None:
        return 0

    troopcount = int(province.get("troops", 0))
    if troopcount <= 0:
        return 0

    lastactivityturn = int(province.get("lasttroopactivityturn", 0))
    return max(0, int(currentturnnumber) - lastactivityturn)


def isprovinceentrenched(province, currentturnnumber):
    return getprovinceentrenchmentturns(province, currentturnnumber) >= entrenchmentturnrequired


# Movement starts
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
        enrichedprovince["lasttroopactivityturn"] = 0
        enrichedlist.append(enrichedprovince)
    return enrichedlist


def buildprovinceadjacencygraph(provincemap, onprogress=None):
    provinceidlist = list(provincemap.keys())
    totalprovincecount = len(provinceidlist)

    # TEST OPTIMIZATION 3 APRIL
    totalprogresssteps = max(1, totalprovincecount * 2)
    if onprogress and not onprogress(0, totalprogresssteps):
        return None
    # larger cells will = faster but not as accurate
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
                    #compare each pair once only, but avoid storing a global pair set
                    if candidateindex > provinceindex:
                        candidateindexset.add(candidateindex)




        for candidateindex in candidateindexset:
            candidateprovinceid, secondrectangle, dontneed, dontneed, dontneed, dontneed = provinceentrylist[candidateindex]
            if rectanglesclose(firstrectangle, secondrectangle, padding=adjacencytestpadding):
                firstprovince = provincemap.get(provinceid)
                secondprovince = provincemap.get(candidateprovinceid)
                if not firstprovince or not secondprovince:
                    continue

                # require a real shared border to avoid false positives from bounding-box proximity.
                sharedsegments = getsharedbordersegments(
                    firstprovince,
                    secondprovince,
                    linetolerancee=0.9,
                    alignmenttolerance=0.16,
                    minlength=0.48 * 0.4, # HIGHER WILL CAUSE BORDER ISSUES, LOWER WILL CAUSE PERFORMANCE ISSUES, 0.48 is the length of a diagonal of a grid cell, so this means the shared border must be at least 40% of that diagonal to count as adjacent
                )
                if not sharedsegments:
                    continue

                adjacencygraph[provinceid].add(candidateprovinceid)
                adjacencygraph[candidateprovinceid].add(provinceid)

        if onprogress and (provinceindex == 0 or (provinceindex + 1) % 100 == 0 or (provinceindex + 1) == totalprovincecount):
            if not onprogress(totalprovincecount + provinceindex + 1, totalprogresssteps):
                return None


    return adjacencygraph
    # optimization issue, cannot run on Benedict's AMD computer, might need to optimize the adjacency graph building


def getterrainmovecost(province):
    return terrainmovecostlookup.get(province.get("terrain", "plains"), 1.0)



# A* PATHFINDING ADAPTED FROM https://medium.com/@nicholas.w.swift/easy-a-star-pathfinding-7e6689c7f7b2
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

    #  A*
    while openheap:
        # total province with lowest cost
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


def processmovementorders(movementorderlist, provincemap, emit, currentturnnumber=None):
    # MOVEMENT processing
    finishedorderlist = []

    def markorderfinished(movementorder, reasontext):
        if movementorder not in finishedorderlist:
            finishedorderlist.append(movementorder)
        movementorder["_finishreason"] = reasontext

    def interruptdefendingorders(targetprovinceid, defendingcountry, excludedorder):
        interruptedorderlist = []
        totalmovingdefenders = 0
        for candidateorder in movementorderlist:
            if candidateorder is excludedorder:
                continue
            if int(candidateorder.get("amount", 0)) <= 0:
                continue
            if candidateorder.get("current") != targetprovinceid:
                continue

            candidatecountry = candidateorder.get("controllercountry", candidateorder.get("country"))
            if candidatecountry != defendingcountry:
                continue

            totalmovingdefenders += int(candidateorder.get("amount", 0))
            interruptedorderlist.append(candidateorder)

        return interruptedorderlist, totalmovingdefenders

    for movementorder in movementorderlist:
        if int(movementorder.get("amount", 0)) <= 0:
            markorderfinished(movementorder, movementorder.get("_finishreason", "depleted"))
            continue

        movementpoints = 1.0 * float(movementorder.get("speedmodifier", 1.0))
        pathlist = movementorder["path"]
        currentpathindex = movementorder["index"]
        movingcountry = movementorder.get("controllercountry", movementorder.get("country"))
        movingcountrycolor = movementorder.get("countrycolor")

        while currentpathindex < len(pathlist) - 1:
            nextprovinceid = pathlist[currentpathindex + 1]
            nextprovince = provincemap[nextprovinceid]
            movecost = getterrainmovecost(nextprovince)
            # move next turn if not enough
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
                and nextprovince["troops"] >= 0
            ):
                attackers = movementorder["amount"]
                interruptedorderlist, movingdefenders = interruptdefendingorders(
                    nextprovinceid,
                    nextcountry,
                    movementorder,
                )

                basedefenders = int(nextprovince.get("troops", 0))
                defenders = basedefenders + movingdefenders

                entrenched = isprovinceentrenched(nextprovince, currentturnnumber)
                defensemultiplier = entrenchmentdefensemultiplier if entrenched else 1.0
                effectivedefenders = int(math.ceil(defenders * defensemultiplier))

                if defenders > 0 and attackers <= effectivedefenders:
                    remainingeffective = effectivedefenders - attackers
                    remainingdefenders = int(math.ceil(remainingeffective / defensemultiplier)) if remainingeffective > 0 else 0
                    nextprovince["troops"] = max(0, min(defenders, remainingdefenders))

                    for interruptedorder in interruptedorderlist:
                        interruptedorder["amount"] = 0
                        markorderfinished(interruptedorder, "interrupted_defense")

                    markprovincetroopactivity(nextprovince, currentturnnumber)

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
                                "defenseMultiplier": defensemultiplier,
                                "defendersEntrenched": entrenched,
                            },
                        )

                    movementorder["amount"] = 0
                    markorderfinished(movementorder, "defeated")
                    break

                if defenders > 0:
                    movementorder["amount"] = max(0, int(math.ceil(attackers - effectivedefenders)))
                    nextprovince["troops"] = 0

                    for interruptedorder in interruptedorderlist:
                        interruptedorder["amount"] = 0
                        markorderfinished(interruptedorder, "interrupted_defense")

                    markprovincetroopactivity(nextprovince, currentturnnumber)

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
                                "defenseMultiplier": defensemultiplier,
                                "defendersEntrenched": entrenched,
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
                markprovincetroopactivity(nextprovince, currentturnnumber)
                if emit is not None:
                    emit(
                        EngineEventType.PROVINCECONTROLCHANGED,
                        {
                            "provinceId": nextprovinceid,
                            "previousController": previouscontroller,
                            "newController": movingcountry,
                        },
                    )  #link to event

            # Move at most one hop per turn so units cannot skip provinces.
            break

        movementorder["index"] = currentpathindex
        movementorder["current"] = pathlist[currentpathindex]

        if movementorder["amount"] <= 0:
            markorderfinished(movementorder, movementorder.get("_finishreason", "depleted"))


            if emit is not None:
                emit(
                    EngineEventType.MOVEORDERFINISHED,
                    {
                        "path": list(pathlist),
                        "finalProvinceId": pathlist[currentpathindex],
                        "remainingTroops": 0,
                        "reason": movementorder.get("_finishreason", "depleted"),
                    },
                )

        elif currentpathindex >= len(pathlist) - 1:
            destinationprovinceid = pathlist[-1]
            provincemap[destinationprovinceid]["troops"] += movementorder["amount"]
            markprovincetroopactivity(provincemap[destinationprovinceid], currentturnnumber)
            markorderfinished(movementorder, "arrived")


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
        finishedorder.pop("_finishreason", None)
        movementorderlist.remove(finishedorder)


def splitselectedtroops(provincemap, provincegraph, selectedprovinceids, playercountry):

    validselectedprovinceids = []
    for provinceid in sorted(set(selectedprovinceids or ())):
        province = provincemap.get(provinceid)
        if not province:
            continue
        if getprovincecontroller(province) != playercountry:
            continue
        validselectedprovinceids.append(provinceid)


    if not validselectedprovinceids:

        return {
            "success": False,
            "selectedprovinceids": [],
            "primaryprovinceid": None,
            "movedtroops": 0,
        }



    if len(validselectedprovinceids) == 1:
        sourceprovinceid = validselectedprovinceids[0]
        sourceprovince = provincemap[sourceprovinceid]
        sourcetroops = int(sourceprovince.get("troops", 0))


        if sourcetroops < 2:
            return {
                "success": False,
                "selectedprovinceids": validselectedprovinceids,
                "primaryprovinceid": sourceprovinceid,
                "movedtroops": 0,
            }

        friendlyneighborids = []


        for neighborprovinceid in provincegraph.get(sourceprovinceid, ()):
            neighborprovince = provincemap.get(neighborprovinceid)
            if not neighborprovince:
                continue
            if getprovincecontroller(neighborprovince) != playercountry:
                continue
            friendlyneighborids.append(neighborprovinceid)



        if not friendlyneighborids:
            return {
                "success": False,
                "selectedprovinceids": validselectedprovinceids,
                "primaryprovinceid": sourceprovinceid,
                "movedtroops": 0,
            }

        targetprovinceid = min(
            friendlyneighborids,
            key=lambda provinceid: int(provincemap[provinceid].get("troops", 0)),
        )
        movedtroops = sourcetroops // 2


        if movedtroops <= 0:
            return {
                "success": False,
                "selectedprovinceids": validselectedprovinceids,
                "primaryprovinceid": sourceprovinceid,
                "movedtroops": 0,
            }

        sourceprovince["troops"] = sourcetroops - movedtroops
        provincemap[targetprovinceid]["troops"] += movedtroops

        return {
            "success": True,
            "selectedprovinceids": [sourceprovinceid, targetprovinceid],
            "primaryprovinceid": sourceprovinceid,
            "movedtroops": movedtroops,
        }


    totaltroops = sum(int(provincemap[provinceid].get("troops", 0)) for provinceid in validselectedprovinceids)
    if totaltroops <= 0:
        return {
            "success": False,
            "selectedprovinceids": validselectedprovinceids,
            "primaryprovinceid": validselectedprovinceids[0],
            "movedtroops": 0,
        }
    

    provincecount = len(validselectedprovinceids)
    baseallocation = totaltroops // provincecount
    remainder = totaltroops % provincecount


    for provinceindex, provinceid in enumerate(validselectedprovinceids):
        provincemap[provinceid]["troops"] = baseallocation + (1 if provinceindex < remainder else 0)

    return {
        "success": True,
        "selectedprovinceids": validselectedprovinceids,
        "primaryprovinceid": validselectedprovinceids[0],
        "movedtroops": totaltroops,
    }




def mergeselectedtroops(provincemap, selectedprovinceids, playercountry, targetprovinceid=None):

    validselectedprovinceids = []
    for provinceid in sorted(set(selectedprovinceids or ())):
        province = provincemap.get(provinceid)
        if not province:
            continue
        if getprovincecontroller(province) != playercountry:
            continue
        validselectedprovinceids.append(provinceid)


    if not validselectedprovinceids:
        return {
            "success": False,
            "selectedprovinceids": [],
            "primaryprovinceid": None,
            "mergedtroops": 0,
        }


    if targetprovinceid not in validselectedprovinceids:
        targetprovinceid = validselectedprovinceids[0]

    totaltroops = sum(int(provincemap[provinceid].get("troops", 0)) for provinceid in validselectedprovinceids)

    for provinceid in validselectedprovinceids:

        provincemap[provinceid]["troops"] = 0
    provincemap[targetprovinceid]["troops"] = totaltroops



    return {
        "success": True,
        "selectedprovinceids": [targetprovinceid],
        "primaryprovinceid": targetprovinceid,
        "mergedtroops": totaltroops,
    }






def getborderedgekey(firstprovinceid, secondprovinceid):
    if firstprovinceid <= secondprovinceid:
        return (firstprovinceid, secondprovinceid)
    return (secondprovinceid, firstprovinceid)


bordersegmentcache = {}




def snappoint(point, precision=2):
    return (round(float(point[0]), precision), round(float(point[1]), precision))




def getedgekey(pointa, pointb, precision=2):
    snappeda = snappoint(pointa, precision=precision)
    snappedb = snappoint(pointb, precision=precision)
    if snappeda <= snappedb:
        return (snappeda, snappedb)
    return (snappedb, snappeda)


def iterateprovinceedge(province):
    for polygon in province.get("polygons", ()):
        polygonpoints = polygon.get("points", ())
        pointcount = len(polygonpoints)
        if pointcount < 2:
            continue
        for pointindex in range(pointcount):
            startpoint = polygonpoints[pointindex]
            endpoint = polygonpoints[(pointindex + 1) % pointcount]
            if abs(startpoint[0] - endpoint[0]) <= 1e-9 and abs(startpoint[1] - endpoint[1]) <= 1e-9:
                continue
            yield startpoint, endpoint


def getprovinceedgedata(province):
    cachedentries = province.get("_edgeentriescache")
    if cachedentries is not None:
        return cachedentries

    edgeentries = []
    for startpoint, endpoint in iterateprovinceedge(province):
        startx, starty = startpoint
        endx, endy = endpoint
        dx = endx - startx
        dy = endy - starty
        length = math.hypot(dx, dy)
        if length <= 1e-6:
            continue
        edgeentries.append(
            {
                "start": (float(startx), float(starty)),
                "end": (float(endx), float(endy)),
                "length": length,
                "ux": dx / length,
                "uy": dy / length,
                "minx": min(startx, endx),
                "maxx": max(startx, endx),
                "miny": min(starty, endy),
                "maxy": max(starty, endy),
            }
        )

    province["_edgeentriescache"] = edgeentries
    return edgeentries


def pointvsline_distance(point, lineentry):
    px, py = point
    sx, sy = lineentry["start"]
    ux = lineentry["ux"]
    uy = lineentry["uy"]
    # perpendicular line


    return abs((px - sx) * (-uy) + (py - sy) * ux)


def lineuppointonline(point, lineentry):
    px, py = point
    sx, sy = lineentry["start"]
    ux = lineentry["ux"]
    uy = lineentry["uy"]

    return (px - sx) * ux + (py - sy) * uy


def getoverlapsegment(firstentry, secondentry, linetolerancee, alignmenttolerance, minlength):
    # Quick reject by expanded bounding boxes.
    if firstentry["maxx"] + linetolerancee < secondentry["minx"]:
        return None
    if secondentry["maxx"] + linetolerancee < firstentry["minx"]:
        return None
    if firstentry["maxy"] + linetolerancee < secondentry["miny"]:
        return None
    if secondentry["maxy"] + linetolerancee < firstentry["miny"]:
        return None

    crossvalue = abs(firstentry["ux"] * secondentry["uy"] - firstentry["uy"] * secondentry["ux"])
    if crossvalue > alignmenttolerance:
        return None

    # need alignment for both ways
    if (
        pointvsline_distance(secondentry["start"], firstentry) > linetolerancee
        and pointvsline_distance(secondentry["end"], firstentry) > linetolerancee
    ):
        return None
    if (
        pointvsline_distance(firstentry["start"], secondentry) > linetolerancee
        and pointvsline_distance(firstentry["end"], secondentry) > linetolerancee
    ):
        return None



    secondstartprojection = lineuppointonline(secondentry["start"], firstentry)
    secondendprojection = lineuppointonline(secondentry["end"], firstentry)

    overlapstart = max(0.0, min(secondstartprojection, secondendprojection))
    overlapend = min(firstentry["length"], max(secondstartprojection, secondendprojection))
    if overlapend - overlapstart < minlength:
        return None

    segmentstart = (
        firstentry["start"][0] + firstentry["ux"] * overlapstart,
        firstentry["start"][1] + firstentry["uy"] * overlapstart,
    )
    segmentend = (
        firstentry["start"][0] + firstentry["ux"] * overlapend,
        firstentry["start"][1] + firstentry["uy"] * overlapend,
    )
    return segmentstart, segmentend


def getsharedbordersegments(
    playerprovince,
    foreignprovince,
    linetolerancee=1.1,
    alignmenttolerance=0.16,
    minlength=0.55,
    keyprecision=2,
):
    

    playerprovinceid = playerprovince.get("id")
    foreignprovinceid = foreignprovince.get("id")
    if playerprovinceid and foreignprovinceid:
        cachekey = (
            playerprovinceid if playerprovinceid <= foreignprovinceid else foreignprovinceid,
            foreignprovinceid if playerprovinceid <= foreignprovinceid else playerprovinceid,
        )
        cachedsegments = bordersegmentcache.get(cachekey)
        if cachedsegments is not None:
            return list(cachedsegments)

    playeredgeentries = getprovinceedgedata(playerprovince)
    foreignedgeentries = getprovinceedgedata(foreignprovince)
    sharedsegmentlookup = {}


    for playeredgeentry in playeredgeentries:
        for foreignedgeentry in foreignedgeentries:
            overlappedsegment = getoverlapsegment(
                playeredgeentry,
                foreignedgeentry,
                linetolerancee,
                alignmenttolerance,
                minlength,
            )
            if not overlappedsegment:
                continue

            segmentstart, segmentend = overlappedsegment
            segmentkey = getedgekey(segmentstart, segmentend, precision=keyprecision)
            existingsegment = sharedsegmentlookup.get(segmentkey)
            if existingsegment is None:
                sharedsegmentlookup[segmentkey] = overlappedsegment
                continue

            existinglength = math.hypot(
                existingsegment[1][0] - existingsegment[0][0],
                existingsegment[1][1] - existingsegment[0][1],
            )
            candidatelength = math.hypot(
                segmentend[0] - segmentstart[0],
                segmentend[1] - segmentstart[1],
            )
            if candidatelength > existinglength:
                sharedsegmentlookup[segmentkey] = overlappedsegment

    sharedsegmentlist = list(sharedsegmentlookup.values())
    if playerprovinceid and foreignprovinceid:
        bordersegmentcache[cachekey] = list(sharedsegmentlist)
    return sharedsegmentlist


def getcountryborderedges(provincemap, provincegraph, countryname):
    if not countryname:
        return []

    borderedgelist = []
    visitededgekeyset = set()


    for playerprovinceid, province in provincemap.items():

        if getprovincecontroller(province) != countryname:
            continue

        for foreignprovinceid in provincegraph.get(playerprovinceid, ()):
            foreignprovince = provincemap.get(foreignprovinceid)
            if not foreignprovince:
                continue

            foreigncountry = getprovincecontroller(foreignprovince)
            if foreigncountry == countryname:
                continue

            sharedsegments = getsharedbordersegments(
                province,
                foreignprovince,
                linetolerancee=sharedLineTolerance,
                alignmenttolerance=sharedAlignmentTolerance,
                minlength=sharedMinLength,
            )
            if not sharedsegments:
                continue

            edgekey = getborderedgekey(playerprovinceid, foreignprovinceid)
            if edgekey in visitededgekeyset:
                continue

            visitededgekeyset.add(edgekey)
            borderedgelist.append(
                {
                    "playerprovinceid": playerprovinceid,
                    "foreignprovinceid": foreignprovinceid,
                    "foreigncountry": foreigncountry,
                    "edgekey": edgekey,
                    "worldsegments": sharedsegments,
                }
            )

    borderedgelist.sort(key=lambda edge: edge["edgekey"]) #sort by edge key to ensure consistent order
    return borderedgelist




def getborderworldsegments(provincemap, borderedge):

    if not borderedge:
        return []

    cachedworldsegments = borderedge.get("worldsegments")
    if cachedworldsegments is not None:
        return list(cachedworldsegments)

    playerprovince = provincemap.get(borderedge.get("playerprovinceid"))
    foreignprovince = provincemap.get(borderedge.get("foreignprovinceid"))
    if not playerprovince or not foreignprovince:
        return []

    sharedsegments = getsharedbordersegments(
        playerprovince,
        foreignprovince,
        linetolerancee=sharedLineTolerance,
        alignmenttolerance=sharedAlignmentTolerance,
        minlength=sharedMinLength,
    )
    if sharedsegments:
        return sharedsegments

    return []


def getfrontlineprovinces(provincemap, provincegraph, playercountry, anchorprovinceid, targetcountry=None):


    anchorprovince = provincemap.get(anchorprovinceid)
    if not anchorprovince or getprovincecontroller(anchorprovince) != playercountry:
        return set()

    frontierprovinceidset = set()
    for provinceid, province in provincemap.items():
        if getprovincecontroller(province) != playercountry:
            continue

        provincehasmatchingborder = False
        for neighborprovinceid in provincegraph.get(provinceid, ()):
            neighborprovince = provincemap.get(neighborprovinceid)
            if not neighborprovince:
                continue
            neighborcountry = getprovincecontroller(neighborprovince)
            if neighborcountry == playercountry:
                continue
            if targetcountry is not None and neighborcountry != targetcountry:
                continue
            if not getsharedbordersegments(province, neighborprovince):
                continue
            provincehasmatchingborder = True
            break

        if provincehasmatchingborder:
            frontierprovinceidset.add(provinceid)

    if anchorprovinceid not in frontierprovinceidset:
        frontierprovinceidset.add(anchorprovinceid)

    frontlineprovinceidset = set()
    openlist = [anchorprovinceid]
    while openlist:
        currentprovinceid = openlist.pop(0)
        if currentprovinceid in frontlineprovinceidset:
            continue
        if currentprovinceid not in frontierprovinceidset:
            continue

        frontlineprovinceidset.add(currentprovinceid)

        for neighborprovinceid in provincegraph.get(currentprovinceid, ()):
            if neighborprovinceid in frontierprovinceidset:
                openlist.append(neighborprovinceid)

    return frontlineprovinceidset


def buildfrontlinetransferplan(provincemap, selectedprovinceids, frontlineprovinceids, playercountry):

    validsourceprovinceids = []
    for provinceid in sorted(set(selectedprovinceids or ())):
        province = provincemap.get(provinceid)
        if not province:
            continue
        if getprovincecontroller(province) != playercountry:
            continue
        if int(province.get("troops", 0)) <= 0:
            continue
        validsourceprovinceids.append(provinceid)

    if not validsourceprovinceids:
        return {
            "totalassignedtroops": 0,
            "transferplan": [],
            "targetprovinceids": [],
        }

    validtargetprovinceids = []
    for provinceid in frontlineprovinceids or ():
        province = provincemap.get(provinceid)
        if not province:
            continue
        if getprovincecontroller(province) != playercountry:
            continue
        if provinceid not in validtargetprovinceids:
            validtargetprovinceids.append(provinceid)

    if not validtargetprovinceids:
        return {
            "totalassignedtroops": 0,
            "transferplan": [],
            "targetprovinceids": [],
        }

    sourceremaininglookup = {
        provinceid: int(provincemap[provinceid].get("troops", 0)) for provinceid in validsourceprovinceids
    }
    totalavailabletroops = sum(sourceremaininglookup.values())


    if totalavailabletroops <= 0:
        return {
            "totalassignedtroops": 0,
            "transferplan": [],
            "targetprovinceids": [],
        }

    targetcount = len(validtargetprovinceids)
    baseallocation = totalavailabletroops // targetcount
    remainder = totalavailabletroops % targetcount
    targetdesiredlookup = {}


    for targetindex, provinceid in enumerate(validtargetprovinceids):
        targetdesiredlookup[provinceid] = baseallocation + (1 if targetindex < remainder else 0)

    transferplan = []
    sourcecursor = 0



    for targetprovinceid in validtargetprovinceids:
        neededtroops = targetdesiredlookup.get(targetprovinceid, 0)
        while neededtroops > 0 and sourcecursor < len(validsourceprovinceids):
            sourceprovinceid = validsourceprovinceids[sourcecursor]
            sourceavailable = sourceremaininglookup[sourceprovinceid]
            if sourceavailable <= 0:
                sourcecursor += 1
                continue

            assignedtroops = min(neededtroops, sourceavailable)
            if assignedtroops <= 0:
                sourcecursor += 1
                continue

            transferplan.append(
                {
                    "sourceprovinceid": sourceprovinceid,
                    "targetprovinceid": targetprovinceid,
                    "amount": assignedtroops,
                }
            )
            sourceremaininglookup[sourceprovinceid] -= assignedtroops
            neededtroops -= assignedtroops
            if sourceremaininglookup[sourceprovinceid] <= 0:
                sourcecursor += 1

    totalassignedtroops = sum(entry["amount"] for entry in transferplan)
    effectivefrontlineprovinceids = []
    seenprovinceids = set()


    for transferentry in transferplan:
        targetprovinceid = transferentry["targetprovinceid"]
        if targetprovinceid in seenprovinceids:
            continue
        seenprovinceids.add(targetprovinceid)
        effectivefrontlineprovinceids.append(targetprovinceid)

    return {
        "totalassignedtroops": totalassignedtroops,
        "transferplan": transferplan,
        "targetprovinceids": effectivefrontlineprovinceids,
    }


def createfrontline(provincemap, provincegraph, playercountry, selectedprovinceids, borderedge, nearbydepth=2):

    if not borderedge:
        return {
            "success": False,
            "assignedtroops": 0,
            "frontlineprovinceids": [],
            "frontlineedgekeys": set(),
            "anchorprovinceid": None,
            "transferplan": [],
        }

    anchorprovinceid = borderedge.get("playerprovinceid")
    anchorprovince = provincemap.get(anchorprovinceid)



    if not anchorprovince or getprovincecontroller(anchorprovince) != playercountry:
        return {
            "success": False,
            "assignedtroops": 0,
            "frontlineprovinceids": [],
            "frontlineedgekeys": set(),
            "anchorprovinceid": None,
            "transferplan": [],
        }


    targetcountry = borderedge.get("foreigncountry")
    nearbyfrontlineprovinceidset = getfrontlineprovinces(
        provincemap,
        provincegraph,
        playercountry,
        anchorprovinceid,
        targetcountry=targetcountry,
    )
    if not nearbyfrontlineprovinceidset:
        nearbyfrontlineprovinceidset = {anchorprovinceid}

    frontlineprovinceids = sorted(nearbyfrontlineprovinceidset)
    if anchorprovinceid in frontlineprovinceids:
        frontlineprovinceids.remove(anchorprovinceid)
        frontlineprovinceids.insert(0, anchorprovinceid)

    frontlineplan = buildfrontlinetransferplan(
        provincemap,
        selectedprovinceids,
        frontlineprovinceids,
        playercountry,
    )
    assignedtroops = frontlineplan["totalassignedtroops"]
    assignedprovinceids = frontlineplan["targetprovinceids"]


    if assignedtroops <= 0 or not assignedprovinceids:
        return {
            "success": False,
            "assignedtroops": 0,
            "frontlineprovinceids": frontlineprovinceids,
            "frontlineedgekeys": set(),
            "anchorprovinceid": anchorprovinceid,
            "transferplan": [],
        }

    frontlineedgekeys = set()
    frontlineedgelist = []

    for playerprovinceid in assignedprovinceids:
        for foreignprovinceid in provincegraph.get(playerprovinceid, ()):
            foreignprovince = provincemap.get(foreignprovinceid)
            if not foreignprovince:
                continue

            foreigncountry = getprovincecontroller(foreignprovince)
            if foreigncountry == playercountry:
                continue
            if targetcountry is not None and foreigncountry != targetcountry:
                continue

            playerprovince = provincemap.get(playerprovinceid)
            if not playerprovince:
                continue
            sharedsegments = getsharedbordersegments(playerprovince, foreignprovince)
            if not sharedsegments:
                continue

            edgekey = getborderedgekey(playerprovinceid, foreignprovinceid)
            if edgekey in frontlineedgekeys:
                continue
            frontlineedgekeys.add(edgekey)
            frontlineedgelist.append(
                {
                    "playerprovinceid": playerprovinceid,
                    "foreignprovinceid": foreignprovinceid,
                    "edgekey": edgekey,
                    "foreigncountry": foreigncountry,
                    "worldsegments": sharedsegments,
                }
            )

    if not frontlineedgekeys:
        fallbackedgekey = getborderedgekey(
            anchorprovinceid,
            borderedge.get("foreignprovinceid"),
        )
        frontlineedgekeys.add(fallbackedgekey)
        frontlineedgelist.append(
            {
                "playerprovinceid": anchorprovinceid,
                "foreignprovinceid": borderedge.get("foreignprovinceid"),
                "edgekey": fallbackedgekey,
            }
        )

    return {

        "success": True,
        "assignedtroops": assignedtroops,
        "frontlineprovinceids": assignedprovinceids,
        "frontlineedgekeys": frontlineedgekeys,
        "frontlineedges": frontlineedgelist,
        "anchorprovinceid": anchorprovinceid,
        "transferplan": frontlineplan["transferplan"],
    }


def pointtosegmentdistance(point, segmentstart, segmentend):
    pointx, pointy = point
    startx, starty = segmentstart
    endx, endy = segmentend

    segmentdx = endx - startx
    segmentdy = endy - starty
    segmentsquaredlength = segmentdx * segmentdx + segmentdy * segmentdy

    
    if segmentsquaredlength <= 1e-9:
        return math.hypot(pointx - startx, pointy - starty)

    projectionratio = ((pointx - startx) * segmentdx + (pointy - starty) * segmentdy) / segmentsquaredlength
    projectionratio = max(0.0, min(1.0, projectionratio))
    nearestx = startx + projectionratio * segmentdx
    nearesty = starty + projectionratio * segmentdy

    return math.hypot(pointx - nearestx, pointy - nearesty) # distnace from point to nearest point, hypotenuse




# Movement ends