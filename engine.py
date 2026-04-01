import os
import json
import math
import heapq
import pygame
import xml.etree.ElementTree as elementtree
from svgelements import Path

from console import developmentconsole, loaddevmodeflag
from gui import drawchoosecountryoverlay, drawgameplayhud, drawtroopcountbadge, lightencolor

# configuration
statefilepath = "states.svg"
provincefilepath = "provinces.svg"
countrydatafilepath = "countries.json"
defaultwindowwidth = 1280
defaultwindowheight = 720
backgroundcolor = (30, 30, 30)
defaultshapecolor = (200, 200, 200)
hovercolor = (255, 100, 100)
minimumzoomvalue = 0.5
maximumzoomvalue = 20.0
zoomstepvalue = 1.15
edgepanmargin = 40
edgepanspeed = 600
curvesamplestep = 1.5
maxsegmentsteps = 48
terrainmovecostlookup = {
    "plains": 1.0,
    "forest": 1.25,
    "hills": 1.35,
    "mountains": 1.8,
    "desert": 1.2,
    "swamp": 1.5,
    "urban": 1.1,
}
autocountrycolors = [
    (197, 92, 92),
    (88, 157, 216),
    (96, 176, 118),
    (212, 154, 79),
    (166, 120, 199),
    (101, 187, 180),
    (214, 124, 162),
    (191, 196, 84),
    (129, 144, 224),
    (206, 138, 112),
]


def loadsvgshapes(filepath, onprogress=None):
    # read svg and convert paths into polygons
    tree = elementtree.parse(filepath)
    root = tree.getroot()
    namespacelookup = {"svg": "http://www.w3.org/2000/svg"}
    shapelist = []

    mapnode = root.find(".//svg:svg[@id='map']", namespacelookup)
    if mapnode is not None:
        pathelementlist = mapnode.findall("svg:path", namespacelookup)
    else:
        pathelementlist = root.findall(".//svg:path", namespacelookup)

    totalcount = len(pathelementlist)
    if onprogress and not onprogress(0, totalcount):
        return []

    for currentindex, pathelement in enumerate(pathelementlist, start=1):
        shapeid = pathelement.get("id", "Unknown")
        pathdata = pathelement.get("d")

        if not pathdata:
            if onprogress and (currentindex == 1 or currentindex % 20 == 0 or currentindex == totalcount):
                if not onprogress(currentindex, totalcount):
                    return []
            continue

        svgpath = Path(pathdata)
        polygonlist = convertpathtopolygons(svgpath)
        if polygonlist:
            allxvalues = [x for polygon in polygonlist for x, _ in polygon["points"]]
            allyvalues = [y for polygon in polygonlist for _, y in polygon["points"]]
            shapelist.append(
                {
                    "id": shapeid,
                    "polygons": polygonlist,
                    "rectangle": pygame.Rect(
                        min(allxvalues),
                        min(allyvalues),
                        max(allxvalues) - min(allxvalues),
                        max(allyvalues) - min(allyvalues),
                    ),
                }
            )

        if onprogress and (currentindex == 1 or currentindex % 20 == 0 or currentindex == totalcount):
            if not onprogress(currentindex, totalcount):
                return []

    return shapelist


def getmapbox(shapelist):
    allxvalues = [shape["rectangle"].left for shape in shapelist] + [shape["rectangle"].right for shape in shapelist]
    allyvalues = [shape["rectangle"].top for shape in shapelist] + [shape["rectangle"].bottom for shape in shapelist]
    minimumx = min(allxvalues)
    maximumx = max(allxvalues)
    minimumy = min(allyvalues)
    maximumy = max(allyvalues)
    return {
        "minimumx": minimumx,
        "maximumx": maximumx,
        "minimumy": minimumy,
        "maximumy": maximumy,
        "width": maximumx - minimumx,
        "height": maximumy - minimumy,
    }


def getscreenpoints(pointlist, zoomvalue, offsetx, offsety):
    return [(x * zoomvalue + offsetx, y * zoomvalue + offsety) for x, y in pointlist]


def getscreenrectangle(rectangle, zoomvalue, offsetx, offsety):
    return pygame.Rect(
        int(rectangle.x * zoomvalue + offsetx),
        int(rectangle.y * zoomvalue + offsety),
        max(1, int(rectangle.width * zoomvalue)),
        max(1, int(rectangle.height * zoomvalue)),
    )


def getminimumzoomforheight(windowheight, mapbox):
    if mapbox["height"] <= 0:
        return min(maximumzoomvalue, minimumzoomvalue)
    return min(maximumzoomvalue, max(minimumzoomvalue, windowheight / mapbox["height"]))


def clampverticalcamera(cameray, zoomvalue, windowheight, mapbox):
    toplimit = -mapbox["minimumy"] * zoomvalue
    bottomlimit = windowheight - mapbox["maximumy"] * zoomvalue
    if bottomlimit > toplimit:
        return (toplimit + bottomlimit) * 0.5
    return max(bottomlimit, min(toplimit, cameray))


def wraphorizontalcamera(camerax, zoomvalue, mapbox):
    tilewidth = mapbox["width"] * zoomvalue # map wider than window then allow horizontal wrapping else wrap center
    if tilewidth <= 1e-6:
        return camerax
    anchorvalue = mapbox["minimumx"] * zoomvalue
    return ((camerax + anchorvalue) % tilewidth) - anchorvalue


def convertpathtopolygons(svgpath):
    polygonlist = []

    for subpath in svgpath.as_subpaths():
        sampledpoints = []
        for segment in subpath:
            segmenttypename = type(segment).__name__
            if segmenttypename == "Move":
                sampledpoints.append((segment.end.x, segment.end.y))
                continue

            if not sampledpoints and hasattr(segment, "start"):
                sampledpoints.append((segment.start.x, segment.start.y))

            segmentlength = float(segment.length()) if hasattr(segment, "length") else 0.0
            samplecount = max(1, min(maxsegmentsteps, int(segmentlength / curvesamplestep)))
            for sampleindex in range(1, samplecount + 1):
                positionratio = sampleindex / samplecount
                point = segment.point(positionratio)
                sampledpoints.append((point.x, point.y))

        cleanedpoints = []
        for pointx, pointy in sampledpoints:
            if not cleanedpoints or abs(pointx - cleanedpoints[-1][0]) > 1e-6 or abs(pointy - cleanedpoints[-1][1]) > 1e-6:
                cleanedpoints.append((pointx, pointy))

        if len(cleanedpoints) >= 3:
            polygonxvalues = [point[0] for point in cleanedpoints]
            polygonyvalues = [point[1] for point in cleanedpoints]
            polygonlist.append(
                {
                    "points": cleanedpoints,
                    "rectangle": pygame.Rect(
                        min(polygonxvalues),
                        min(polygonyvalues),
                        max(polygonxvalues) - min(polygonxvalues),
                        max(polygonyvalues) - min(polygonyvalues),
                    ),
                }
            )

    return polygonlist


def ispointinsidepolygon(point, polygon):
    mousex, mousey = point
    inside = False
    previousindex = len(polygon) - 1

    for currentindex in range(len(polygon)):
        currentx, currenty = polygon[currentindex]
        previousx, previousy = polygon[previousindex]
        crossed = ((currenty > mousey) != (previousy > mousey)) and (
            mousex < (previousx - currentx) * (mousey - currenty) / ((previousy - currenty) or 1e-9) + currentx
        )
        if crossed:
            inside = not inside
        previousindex = currentindex

    return inside


def getparentstateidfromprovinceid(provinceid):
    if "_" not in provinceid:
        return provinceid
    parentname = provinceid.rsplit("_", 1)[0]
    namemismatchlookup = {"Trung_Bo": "Trong_Bo"}
    return namemismatchlookup.get(parentname, parentname)


def parsecolorvalue(rawcolorvalue):
    if isinstance(rawcolorvalue, str):
        colorstring = rawcolorvalue.strip()
        if colorstring.startswith("#"):
            colorstring = colorstring[1:]
        if len(colorstring) == 6:
            try:
                return (
                    int(colorstring[0:2], 16),
                    int(colorstring[2:4], 16),
                    int(colorstring[4:6], 16),
                )
            except ValueError:
                return None

    if isinstance(rawcolorvalue, (list, tuple)) and len(rawcolorvalue) == 3:
        try:
            redvalue = int(rawcolorvalue[0])
            greenvalue = int(rawcolorvalue[1])
            bluevalue = int(rawcolorvalue[2])
            return (
                max(0, min(255, redvalue)),
                max(0, min(255, greenvalue)),
                max(0, min(255, bluevalue)),
            )
        except (TypeError, ValueError):
            return None

    return None


def loadcountrydata(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as fileobject:
            rawdata = json.load(fileobject)
    except (OSError, json.JSONDecodeError):
        return {}, {}

    if not isinstance(rawdata, list):
        return {}, {}

    statetocountrylookup = {}
    countrytocolorlookup = {}


    for countryindex, countryentry in enumerate(rawdata):
        if not isinstance(countryentry, dict):
            continue

        countryname = str(countryentry.get("Country", "")).strip()
        if not countryname:
            continue

        # No color in new format, assign default (CHATGPT)
        parsedcolor = autocountrycolors[countryindex % len(autocountrycolors)]
        countrytocolorlookup[countryname] = parsedcolor

        statesdict = countryentry.get("States", {})
        if not isinstance(statesdict, dict):
            continue

        for statename in statesdict.keys():
            if isinstance(statename, str) and statename.strip():
                statetocountrylookup[statename.strip()] = countryname

    return statetocountrylookup, countrytocolorlookup


def groupsubdivisionsbystate(provincelist, statelist):
    stateidset = {state["id"] for state in statelist}
    groupedlookup = {stateid: [] for stateid in stateidset}

    for province in provincelist:
        parentstateid = getparentstateidfromprovinceid(province["id"])
        if parentstateid not in stateidset:
            continue
        province["parentid"] = parentstateid
        groupedlookup[parentstateid].append(province)

    return groupedlookup


def rectanglesclose(firstrectangle, secondrectangle, padding=1):
    return not (
        firstrectangle.right + padding < secondrectangle.left
        or secondrectangle.right + padding < firstrectangle.left
        or firstrectangle.bottom + padding < secondrectangle.top
        or secondrectangle.bottom + padding < firstrectangle.top
    )


def getshapecenter(shape):
    return (shape["rectangle"].centerx, shape["rectangle"].centery)


def prepareprovincemetadata(provincelist):
    enrichedlist = []
    for province in provincelist:
        enrichedprovince = dict(province)
        enrichedprovince["parentstateid"] = getparentstateidfromprovinceid(enrichedprovince["id"])
        enrichedprovince["terrain"] = "plains"
        enrichedprovince["troops"] = 0
        enrichedprovince["center"] = getshapecenter(enrichedprovince)
        enrichedlist.append(enrichedprovince)
    return enrichedlist


def buildprovinceadjacencygraph(provincemap, onprogress=None):
    provinceidlist = list(provincemap.keys())
    totalprovincecount = len(provinceidlist)
    if onprogress and not onprogress(0, totalprovincecount):
        return {}

    gridcellsize = 12.0
    gridlookup = {}

    for provinceindex, provinceid in enumerate(provinceidlist, start=1):
        provincerectangle = provincemap[provinceid]["rectangle"]
        minimumgridx = int(math.floor(provincerectangle.left / gridcellsize))
        maximumgridx = int(math.floor(provincerectangle.right / gridcellsize))
        minimumgridy = int(math.floor(provincerectangle.top / gridcellsize))
        maximumgridy = int(math.floor(provincerectangle.bottom / gridcellsize))

        for gridx in range(minimumgridx, maximumgridx + 1):
            for gridy in range(minimumgridy, maximumgridy + 1):
                gridlookup.setdefault((gridx, gridy), []).append(provinceid)

        if onprogress and (provinceindex == 1 or provinceindex % 200 == 0 or provinceindex == totalprovincecount):
            if not onprogress(provinceindex, totalprovincecount):
                return {}

    adjacencygraph = {provinceid: set() for provinceid in provinceidlist}
    processedpairset = set()

    for bucketprovinceids in gridlookup.values():
        paircount = len(bucketprovinceids)
        for firstindex in range(paircount):
            firstprovinceid = bucketprovinceids[firstindex]
            firstrectangle = provincemap[firstprovinceid]["rectangle"]

            for secondindex in range(firstindex + 1, paircount):
                secondprovinceid = bucketprovinceids[secondindex]
                if firstprovinceid == secondprovinceid:
                    continue

                if firstprovinceid < secondprovinceid:
                    pairkey = (firstprovinceid, secondprovinceid)
                else:
                    pairkey = (secondprovinceid, firstprovinceid)

                if pairkey in processedpairset:
                    continue
                processedpairset.add(pairkey)

                secondrectangle = provincemap[secondprovinceid]["rectangle"]
                if rectanglesclose(firstrectangle, secondrectangle, padding=1):
                    adjacencygraph[firstprovinceid].add(secondprovinceid)
                    adjacencygraph[secondprovinceid].add(firstprovinceid)

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

        while currentpathindex < len(pathlist) - 1:
            nextprovinceid = pathlist[currentpathindex + 1]
            movecost = getterrainmovecost(provincemap[nextprovinceid])
            if movementpoints + 1e-9 < movecost:
                break
            movementpoints -= movecost
            currentpathindex += 1

        movementorder["index"] = currentpathindex
        movementorder["current"] = pathlist[currentpathindex]

        if currentpathindex >= len(pathlist) - 1:
            destinationprovinceid = pathlist[-1]
            provincemap[destinationprovinceid]["troops"] += movementorder["amount"]
            finishedorderlist.append(movementorder)

    for finishedorder in finishedorderlist:
        movementorderlist.remove(finishedorder)


def drawloadingscreen(screen, largefont, smallfont, completedcount, totalcount):
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            return False

    progressvalue = 0.0 if totalcount <= 0 else completedcount / totalcount
    progressvalue = max(0.0, min(1.0, progressvalue))
    screen.fill((18, 18, 22))

    windowwidth, windowheight = screen.get_size()
    titletextsurface = largefont.render("Loading engine...", True, (240, 240, 240))
    screen.blit(titletextsurface, titletextsurface.get_rect(center=(windowwidth // 2, windowheight // 2 - 40)))

    barwidth = min(640, windowwidth - 120)
    barheight = 22
    barx = (windowwidth - barwidth) // 2
    bary = windowheight // 2 + 4

    pygame.draw.rect(screen, (60, 60, 70), (barx, bary, barwidth, barheight), border_radius=6)
    pygame.draw.rect(screen, (120, 190, 255), (barx, bary, int(barwidth * progressvalue), barheight), border_radius=6)
    pygame.draw.rect(screen, (120, 120, 130), (barx, bary, barwidth, barheight), 1, border_radius=6)

    progresstext = smallfont.render(f"{completedcount}/{totalcount} provinces", True, (205, 205, 215))
    screen.blit(progresstext, progresstext.get_rect(center=(windowwidth // 2, bary + 42)))

    pygame.display.flip()
    return True


def main():
    pygame.init()
    screen = pygame.display.set_mode((defaultwindowwidth, defaultwindowheight), pygame.RESIZABLE)
    if os.path.exists("dev.txt"):
        pygame.display.set_caption("ebee engine playtest apr 1 - dev mode")
    else:
        pygame.display.set_caption("ebee engine playtest apr 1")

    normalfont = pygame.font.SysFont("Arial", 14)
    smallfont = pygame.font.SysFont("Arial", 12)
    titlefont = pygame.font.SysFont("Arial", 32, bold=True)
    loadingtitlefont = pygame.font.SysFont("Arial", 36, bold=True)
    loadingtextfont = pygame.font.SysFont("Arial", 18)
    developmentmode = loaddevmodeflag("dev.txt")

    if not drawloadingscreen(screen, loadingtitlefont, loadingtextfont, 0, 1):
        pygame.quit()
        return

    stateshapelist = loadsvgshapes(
        statefilepath,
        onprogress=lambda completed, total: drawloadingscreen(screen, loadingtitlefont, loadingtextfont, completed, total),
    )
    if not stateshapelist:
        pygame.quit()
        return

    statetocountrylookup, countrytocolorlookup = loadcountrydata(countrydatafilepath)
    for stateshape in stateshapelist:
        statecountry = statetocountrylookup.get(stateshape["id"])
        stateshape["country"] = statecountry
        stateshape["countrycolor"] = countrytocolorlookup.get(statecountry, (85, 85, 85))

    provinceshapelist = loadsvgshapes(
        provincefilepath if False else provincefilepath,
        onprogress=lambda completed, total: drawloadingscreen(screen, loadingtitlefont, loadingtextfont, completed, total),
    )
    # fix accidental typo safely
    if not provinceshapelist:
        provinceshapelist = loadsvgshapes(
            provincefilepath if False else provincefilepath,
            onprogress=lambda completed, total: drawloadingscreen(screen, loadingtitlefont, loadingtextfont, completed, total),
        )
    if not provinceshapelist:
        pygame.quit()
        return

    provinceenrichedlist = prepareprovincemetadata(provinceshapelist)
    for province in provinceenrichedlist:
        provincecountry = statetocountrylookup.get(province["parentstateid"])
        province["country"] = provincecountry
        province["countrycolor"] = countrytocolorlookup.get(provincecountry, (85, 85, 85))

    provincemap = {province["id"]: province for province in provinceenrichedlist}
    provincegraph = buildprovinceadjacencygraph(
        provincemap,
        onprogress=lambda completed, total: drawloadingscreen(screen, loadingtitlefont, loadingtextfont, completed, total),
    )

    groupedsubdivisionlookup = groupsubdivisionsbystate(provinceenrichedlist, stateshapelist)
    for stateshape in stateshapelist:
        subdivisionsforstate = groupedsubdivisionlookup.get(stateshape["id"], [])
        for province in subdivisionsforstate:
            province["country"] = stateshape.get("country")
            province["countrycolor"] = stateshape.get("countrycolor", (85, 85, 85))
        stateshape["subdivisions"] = subdivisionsforstate

    mapbox = getmapbox(stateshapelist)
    windowwidth, windowheight = screen.get_size()
    zoomvalue = getminimumzoomforheight(windowheight, mapbox)
    camerax = (windowwidth - mapbox["width"] * zoomvalue) / 2 - mapbox["minimumx"] * zoomvalue
    cameray = (windowheight - mapbox["height"] * zoomvalue) / 2 - mapbox["minimumy"] * zoomvalue
    cameray = clampverticalcamera(cameray, zoomvalue, windowheight, mapbox)
    camerax = wraphorizontalcamera(camerax, zoomvalue, mapbox)

    clock = pygame.time.Clock()
    expandedstateid = None
    selectedprovinceid = None

    gamephase = "choosecountry"
    pendingcountry = None
    playercountry = None

    currentturnnumber = 1
    playergold = 1200
    playerpopulation = 2500
    recruitamount = 100
    recruitgoldcostperunit = 1
    recruitpopulationcostperunit = 1
    movementorderlist = []
    routepreviewset = set()

    devconsole = developmentconsole(enabled=developmentmode)

    isrunning = True
    while isrunning:
        elapsedseconds = clock.tick(60) / 1000.0
        mouseposition = pygame.mouse.get_pos()
        windowwidth, windowheight = screen.get_size()

        panpixels = edgepanspeed * elapsedseconds
        if mouseposition[0] <= edgepanmargin:
            camerax += panpixels
        elif mouseposition[0] >= windowwidth - edgepanmargin:
            camerax -= panpixels

        if mouseposition[1] <= edgepanmargin:
            cameray += panpixels
        elif mouseposition[1] >= windowheight - edgepanmargin:
            cameray -= panpixels

        minimumzoom = getminimumzoomforheight(windowheight, mapbox)
        if zoomvalue < minimumzoom:
            oldzoomvalue = zoomvalue
            zoomvalue = minimumzoom
            centerx, centery = windowwidth * 0.5, windowheight * 0.5
            centerworldx = (centerx - camerax) / oldzoomvalue
            centerworldy = (centery - cameray) / oldzoomvalue
            camerax = centerx - centerworldx * zoomvalue
            cameray = centery - centerworldy * zoomvalue

        cameray = clampverticalcamera(cameray, zoomvalue, windowheight, mapbox)
        camerax = wraphorizontalcamera(camerax, zoomvalue, mapbox)

        screen.fill(backgroundcolor)

        hovertext = None
        hoveredstateid = None
        hoveredprovinceid = None
        screenrectangle = screen.get_rect()
        troopbadgelist = []

        tilewidth = mapbox["width"] * zoomvalue
        if tilewidth > 1:
            copieseachside = int(windowwidth / tilewidth) + 2
            copyshiftlist = [copyindex * tilewidth for copyindex in range(-copieseachside, copieseachside + 1)]
        else:
            copyshiftlist = [0]

        for copyshift in copyshiftlist:
            drawcamerax = camerax + copyshift

            for stateshape in stateshapelist:
                staterectanglescreen = getscreenrectangle(stateshape["rectangle"], zoomvalue, drawcamerax, cameray)
                if not staterectanglescreen.colliderect(screenrectangle):
                    continue

                if gamephase == "choosecountry":
                    drawitemlist = [stateshape]
                else:
                    if expandedstateid == stateshape["id"] and stateshape["subdivisions"]:
                        drawitemlist = stateshape["subdivisions"]
                    else:
                        drawitemlist = [stateshape]

                for drawitem in drawitemlist:
                    itemhovered = False
                    drawpolygonlist = []

                    itemrectanglescreen = getscreenrectangle(drawitem["rectangle"], zoomvalue, drawcamerax, cameray)
                    if not itemrectanglescreen.colliderect(screenrectangle):
                        continue

                    for polygon in drawitem["polygons"]:
                        polygonrectanglescreen = getscreenrectangle(polygon["rectangle"], zoomvalue, drawcamerax, cameray)
                        if not polygonrectanglescreen.colliderect(screenrectangle):
                            continue

                        polygonpointsscreen = getscreenpoints(polygon["points"], zoomvalue, drawcamerax, cameray)
                        polygonpointsscreenint = [(int(pointx), int(pointy)) for pointx, pointy in polygonpointsscreen]
                        if len(polygonpointsscreenint) < 3:
                            continue
                        drawpolygonlist.append(polygonpointsscreenint)

                        if not itemhovered and polygonrectanglescreen.collidepoint(mouseposition) and ispointinsidepolygon(mouseposition, polygonpointsscreen):
                            if gamephase == "choosecountry" and not stateshape.get("country"):
                                continue
                            itemhovered = True
                            hovertext = drawitem["id"]
                            hoveredstateid = drawitem.get("parentid", stateshape["id"])
                            hoveredprovinceid = drawitem["id"] if "parentid" in drawitem else None

                    if gamephase == "choosecountry":
                        if stateshape.get("country"):
                            basefillcolor = stateshape.get("countrycolor", defaultshapecolor)
                        else:
                            basefillcolor = (75, 75, 75)
                        if pendingcountry and stateshape.get("country") == pendingcountry:
                            pulsevalue = 0.35 + 0.45 * (0.5 + 0.5 * math.sin(pygame.time.get_ticks() * 0.008))
                            basefillcolor = lightencolor(basefillcolor, pulsevalue)
                    elif drawitem.get("id") == selectedprovinceid:
                        basefillcolor = (232, 214, 103)
                    elif drawitem.get("id") in routepreviewset:
                        basefillcolor = (95, 145, 255)
                    elif any(order["current"] == drawitem.get("id") for order in movementorderlist):
                        basefillcolor = (132, 96, 226)
                    else:
                        basefillcolor = drawitem.get("countrycolor", stateshape.get("countrycolor", defaultshapecolor))

                    finalfillcolor = hovercolor if itemhovered else basefillcolor
                    for drawpolygon in drawpolygonlist:
                        pygame.draw.polygon(screen, finalfillcolor, drawpolygon)
                        pygame.draw.polygon(screen, (50, 50, 50), drawpolygon, 1)

                    if gamephase == "play" and "troops" in drawitem and drawitem["troops"] > 0 and itemrectanglescreen.colliderect(screenrectangle):
                        troopbadgelist.append((itemrectanglescreen.center, drawitem["troops"]))

        for badgecenter, badgetroops in troopbadgelist:
            drawtroopcountbadge(screen, badgecenter, badgetroops, smallfont)

        choosebuttonrectangle = None
        recruitbuttonrectangle = None
        endturnbuttonrectangle = None

        if gamephase == "choosecountry":
            choosebuttonrectangle, _ = drawchoosecountryoverlay(screen, titlefont, normalfont, pendingcountry)
        else:
            canrecruit = selectedprovinceid is not None and provincemap[selectedprovinceid]["country"] == playercountry
            recruitgoldcost = recruitamount * recruitgoldcostperunit
            recruitpopulationcost = recruitamount * recruitpopulationcostperunit
            recruitenabled = canrecruit and (developmentmode or (playergold >= recruitgoldcost and playerpopulation >= recruitpopulationcost))
            recruitbuttonrectangle, endturnbuttonrectangle = drawgameplayhud(
                screen,
                normalfont,
                smallfont,
                playercountry,
                currentturnnumber,
                playergold,
                playerpopulation,
                selectedprovinceid,
                provincemap,
                recruitamount,
                recruitenabled,
                developmentmode,
                recruitgoldcost,
                recruitpopulationcost,
            )

        if hovertext:
            hoverlabel = normalfont.render(hovertext, True, (255, 255, 255))
            screen.blit(hoverlabel, (10, 10))

        devconsole.draw(screen, normalfont, smallfont)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                isrunning = False

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if devconsole.handleleftclick(event.pos):
                    continue

                if gamephase == "choosecountry":
                    if hoveredstateid:
                        selectedstateobject = next((state for state in stateshapelist if state["id"] == hoveredstateid), None)
                        if selectedstateobject and selectedstateobject.get("country"):
                            pendingcountry = selectedstateobject["country"]
                    if choosebuttonrectangle and choosebuttonrectangle.collidepoint(event.pos) and pendingcountry:
                        playercountry = pendingcountry
                        gamephase = "play"
                        expandedstateid = None
                        selectedprovinceid = None
                        routepreviewset = set()
                    continue

                if gamephase == "play":
                    if recruitbuttonrectangle and recruitbuttonrectangle.collidepoint(event.pos):
                        if selectedprovinceid:
                            selectedprovince = provincemap[selectedprovinceid]
                            if selectedprovince["country"] == playercountry:
                                requiredgold = recruitamount * recruitgoldcostperunit
                                requiredpopulation = recruitamount * recruitpopulationcostperunit
                                if developmentmode or (playergold >= requiredgold and playerpopulation >= requiredpopulation):
                                    selectedprovince["troops"] += recruitamount
                                    if not developmentmode:
                                        playergold -= requiredgold
                                        playerpopulation -= requiredpopulation
                        continue

                    if endturnbuttonrectangle and endturnbuttonrectangle.collidepoint(event.pos):
                        processmovementorders(movementorderlist, provincemap)
                        if playercountry:
                            ownedprovincecount = sum(1 for province in provincemap.values() if province.get("country") == playercountry)
                            playergold += max(5, ownedprovincecount // 5)
                            playerpopulation += max(10, ownedprovincecount // 3)
                        currentturnnumber += 1
                        routepreviewset = set()
                        continue

                    if hoveredstateid is not None:
                        expandedstateid = hoveredstateid
                    else:
                        expandedstateid = None
                        selectedprovinceid = None
                        routepreviewset = set()

                    if hoveredprovinceid:
                        selectedprovince = provincemap.get(hoveredprovinceid)
                        if selectedprovince and selectedprovince.get("country") == playercountry:
                            selectedprovinceid = hoveredprovinceid

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
                if devconsole.visible or gamephase != "play":
                    continue
                if selectedprovinceid is None or hoveredprovinceid is None:
                    continue
                if hoveredprovinceid == selectedprovinceid:
                    continue

                sourceprovince = provincemap.get(selectedprovinceid)
                destinationprovince = provincemap.get(hoveredprovinceid)
                if not sourceprovince or not destinationprovince:
                    continue
                if sourceprovince.get("country") != playercountry or destinationprovince.get("country") != playercountry:
                    continue
                if sourceprovince["troops"] <= 0:
                    continue

                allowedprovinceidset = {provinceid for provinceid, province in provincemap.items() if province.get("country") == playercountry}
                foundpath = findprovincepath(
                    selectedprovinceid,
                    hoveredprovinceid,
                    provincemap,
                    provincegraph,
                    allowedprovinceidset=allowedprovinceidset,
                )
                routepreviewset = set(foundpath)
                if len(foundpath) >= 2:
                    movingtroopcount = sourceprovince["troops"]
                    sourceprovince["troops"] -= movingtroopcount
                    movementorderlist.append(
                        {
                            "amount": movingtroopcount,
                            "path": foundpath,
                            "index": 0,
                            "current": foundpath[0],
                            "speedmodifier": 1.0,
                        }
                    )

            elif event.type == pygame.MOUSEWHEEL:
                if devconsole.visible:
                    continue
                oldzoomvalue = zoomvalue
                zoomvalue *= zoomstepvalue ** event.y
                minimumzoom = getminimumzoomforheight(windowheight, mapbox)
                zoomvalue = max(minimumzoom, min(maximumzoomvalue, zoomvalue))
                if zoomvalue != oldzoomvalue:
                    mousex, mousey = pygame.mouse.get_pos()
                    mouseworldx = (mousex - camerax) / oldzoomvalue
                    mouseworldy = (mousey - cameray) / oldzoomvalue
                    camerax = mousex - mouseworldx * zoomvalue
                    cameray = mousey - mouseworldy * zoomvalue
                    cameray = clampverticalcamera(cameray, zoomvalue, windowheight, mapbox)
                    camerax = wraphorizontalcamera(camerax, zoomvalue, mapbox)

            elif event.type == pygame.KEYDOWN:
                if devconsole.handlekeydown(event, provincemap, playercountry, countrytocolorlookup, defaultshapecolor):
                    continue

            elif event.type == pygame.VIDEORESIZE:
                oldwindowwidth, oldwindowheight = screen.get_size()
                newwindowwidth = max(400, event.w)
                newwindowheight = max(300, event.h)

                centerworldx = (oldwindowwidth * 0.5 - camerax) / zoomvalue
                centerworldy = (oldwindowheight * 0.5 - cameray) / zoomvalue

                screen = pygame.display.set_mode((newwindowwidth, newwindowheight), pygame.RESIZABLE)
                camerax = newwindowwidth * 0.5 - centerworldx * zoomvalue
                cameray = newwindowheight * 0.5 - centerworldy * zoomvalue

                minimumzoom = getminimumzoomforheight(newwindowheight, mapbox)
                if zoomvalue < minimumzoom:
                    zoomvalue = minimumzoom
                    camerax = newwindowwidth * 0.5 - centerworldx * zoomvalue
                    cameray = newwindowheight * 0.5 - centerworldy * zoomvalue

                cameray = clampverticalcamera(cameray, zoomvalue, newwindowheight, mapbox)
                camerax = wraphorizontalcamera(camerax, zoomvalue, mapbox)

        pygame.display.flip()

    pygame.quit()


main()
