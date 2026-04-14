import os
import json
import math
import heapq
import time
import platform
import pygame
import xml.etree.ElementTree as elementtree
from svgelements import Path
#Local module
from engine.console import developmentconsole, loaddevmodeflag 
from engine.gui import EngineUI, gui_lightencolor
from engine.diagnostics import logstartupdiagnostics, createloadingprogresscallback, logslowpath
from . import core as coremodule
from . import gameplay as gameplaymodule
from . import economy as economymodule
from . import api as apimodule
from .events import EventBus, EngineEventType


from .apicalltest.newsbannereventtest import NewsSystem, NewsPopup # TEST API CALL


print("CURRENT VERSION - APRIL 8 2024")
# MAIN GAME LOOP FILE


# configuration

#filepath = "map.csv"
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
] # placeholder colors, will make a dynamic color generator later 
# TODO: dynamic color generation


# MAP LOADINGG STARTS

#def loadhexagonmap(filepath):
#   shapelist = []
#   with open(filepath, "r") as fileobject:
#       for line in fileobject:
#           parts = line.strip().split()
#           if len(parts) >= 3:
#               shapeid = parts[0]
#               try:
#                   x = float(parts[1])
#                   y = float(parts[2])
#                   shapelist.append({"id": shapeid, "points": [(x, y)]})
#               except ValueError:
#                   continue
#   return shapelist
#ignore code, hexagon not used



#CURRENT ATTRIBUTES:
# PROVINCE: id, polygons, rectangle, parentid, terrain, troops, ownercountry, controllercountry, country (compat alias to controllercountry), countrycolor
# Example: {
#   "id": "Malaya_01",
#   "polygons": [{"points": [(x1, y1), (x2, y2), ...],
#   "rectangle": pygame.Rect(...),
#   "parentid": "Indochina",
#   "terrain": "plains",
#   "troops": 100,
#   "ownercountry": "Malaysia",
#   "controllercountry": "Malaysia",
#   "country": "Malaysia",
#   "countrycolor": (r, g, b),
# }

# STATE: id, polygons, rectangle, ownercountry, controllercountry, country (compat alias), countrycolor, subdivisions (list of provinces)
# COUNTRY: name, color (from json or auto assigned)





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

        pathstarttimestamp = time.perf_counter()
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

        pathelapsedseconds = time.perf_counter() - pathstarttimestamp
        logslowpath(filepath, currentindex, totalcount, shapeid, pathelapsedseconds)

        if onprogress and (currentindex == 1 or currentindex % 20 == 0 or currentindex == totalcount):
            if not onprogress(currentindex, totalcount):

                return []
    #print(shapelist[0]) 
    return shapelist




def getmapbox(shapelist):
    allXValues = [shape["rectangle"].left for shape in shapelist] + [shape["rectangle"].right for shape in shapelist]
    allYValues = [shape["rectangle"].top for shape in shapelist] + [shape["rectangle"].bottom for shape in shapelist]
    minX = min(allXValues)
    maxX = max(allXValues)
    minY = min(allYValues)
    maxY = max(allYValues)
    tempVar = 0 
    # print("Debug: minX=", minX, "maxX=", maxX)  
    #print(f"box |  x={minX} to {maxX}, y={minY} to {maxY}")
    return {
        "minimumx": minX,
        "maximumx": maxX,
        "minimumy": minY,
        "maximumy": maxY,
        "width": maxX - minX,
        "height": maxY - minY,
    }
# MAP LOADINGG ENDSS




# UTILITY FUNCTIONS STARTS



def getscreenpoints(pointlist, zoomvalue, offsetx, offsety):
    #print(pointlist)
    #return (pointlist)
    return [(x * zoomvalue + offsetx, y * zoomvalue + offsety) for x, y in pointlist]




def getscreenrectangle(rectangle, zoomvalue, offsetx, offsety):
    # print(rectangle)
    testrectangle1 = None 
    # screen rectangle to screen coordinates
    return pygame.Rect(
        int(rectangle.x * zoomvalue + offsetx),
        int(rectangle.y * zoomvalue + offsety),
        max(1, int(rectangle.width * zoomvalue)),
        max(1, int(rectangle.height * zoomvalue)),
    )




def getminimumzoomforheight(windowheight, mapbox):

    if mapbox["height"] <= 0:
        return min(maximumzoomvalue, minimumzoomvalue)
    # print("getminmumzoom height", windowheight)

    return min(maximumzoomvalue, max(minimumzoomvalue, windowheight / mapbox["height"]))




def clampverticalcamera(cameray, zoomvalue, windowheight, mapbox):

    clamptest = 1  
    toplimit = -mapbox["minimumy"] * zoomvalue
    bottomlimit = windowheight - mapbox["maximumy"] * zoomvalue
    if bottomlimit > toplimit:
        return (toplimit + bottomlimit) * 0.5
    # print(cameray)
    return max(bottomlimit, min(toplimit, cameray))





def wraphorizontalcamera(camerax, zoomvalue, mapbox):


    tilewidth = mapbox["width"] * zoomvalue # map wider than window then allow horizontal wrapping else wrap center
    if tilewidth:
        return camerax
    anchorvalue = mapbox["minimumx"] * zoomvalue



    return ((camerax + anchorvalue) % tilewidth) - anchorvalue

# UTILITY FUNCTIONS ENDSS




# GAME LOGIC AND RENDERING STARTS

# a* pathfinding adpated from https://www.redblobgames.com/pathfinding/a-star/introduction


def getsegmentsamplecount(segment):
    segmenttypename = type(segment).__name__
    if segmenttypename == "Move":
        return 1 #no need to sample this

    if hasattr(segment, "start") and hasattr(segment, "end"):
        dx = segment.end.x - segment.start.x 
        dy = segment.end.y - segment.start.y
        approximatelength = math.hypot(dx, dy)
    else:
        approximatelength = 0.0

    samplecount = max(1, min(maxsegmentsteps, int(approximatelength / curvesamplestep)))
    if segmenttypename in {"Arc", "CubicBezier", "QuadraticBezier"}:
        samplecount = min(maxsegmentsteps, max(2, samplecount * 2))
    return samplecount


#TODO: OPTIMIZATION for curve sampling



def convertpathtopolygons(svgpath):

    polygonlist = []

    for subpath in svgpath.as_subpaths():
        sampledpoints = []
        for segment in subpath:
            segmenttypename = type(segment).__name__
            if segmenttypename == "Move":
                sampledpoints.append((segment.end.x, segment.end.y))
                continue
            #print(segment)
            if not sampledpoints and hasattr(segment, "start"):
                sampledpoints.append((segment.start.x, segment.start.y))

            samplecount = getsegmentsamplecount(segment)


            for sampleindex in range(1, samplecount + 1):
                positionratio = sampleindex / samplecount
                point = segment.point(positionratio)
                sampledpoints.append((point.x, point.y))

        cleanedpoints = []


        for pointx, pointy in sampledpoints:
            if not cleanedpoints or abs(pointx - cleanedpoints[-1][0]) or abs(pointy - cleanedpoints[-1][1]) > 1e-6: #1e-6 is a threshold to consider points different
                cleanedpoints.append((pointx, pointy))
                #print(cleanedpoints[-1])

        #OLD CODE THIS ONE IS TOO SLOW
        #if not pointx, pointy in cleanedpoints:
        #   cleanedpoints.append((pointx, pointy))


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
                    int(colorstring[0:2], 16), # red
                    int(colorstring[2:4], 16), # green
                    int(colorstring[4:6], 16), # blue
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

#  from https://stackoverflow.com/a/29643643  




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

# group subdivision to their parent state for rendering 


def groupsubdivisionsbystate(provincelist, statelist):

    stateidset = {state["id"] for state in statelist}
    groupedlookup = {stateid: [] for stateid in stateidset}


    for province in provincelist:
        parentstateid = getparentstateidfromprovinceid(province["id"])
        if parentstateid not in stateidset:
            continue
        province["parentid"] = parentstateid
        groupedlookup[parentstateid].append(province)
        #print(province["id"], "parent", parentstateid)
    #print(groupedlookup)

    return groupedlookup # stateid to list of provinces for example ("Malaya" -> [province1, province2])


# check if rect are close to be considered adjacent to build provinece graph for path finding


def rectanglesclose(firstrectangle, secondrectangle, padding=1):
    return not (
        firstrectangle.right + padding < secondrectangle.left
        or secondrectangle.right + padding < firstrectangle.left
        or firstrectangle.bottom + padding < secondrectangle.top
        or secondrectangle.bottom + padding < firstrectangle.top
    )



def getshapecenter(shape):
    return (shape["rectangle"].centerx, shape["rectangle"].centery)




def getprovincecontroller(province): # get the current controller
    return province.get("controllercountry", province.get("country"))




def getprovinceowner(province): # get the original owner
    return province.get("ownercountry", province.get("country"))




def setprovincecontroller(province, countryname, countrycolor=None): #set the controller of the provincewhen occupied or annexed
    province["controllercountry"] = countryname
    province["country"] = countryname  # compatibility alias
    if countrycolor is not None:
        province["countrycolor"] = countrycolor



# Movement starts


def prepareprovincemetadata(provincelist):
    enrichedList = []
    testCounter = 0  
    for province in provincelist:
        enrichedProvince = dict(province)
        enrichedProvince["parentstateid"] = getparentstateidfromprovinceid(enrichedProvince["id"])
        enrichedProvince["terrain"] = "plains"
        enrichedProvince["troops"] = 0
        enrichedProvince["center"] = getshapecenter(enrichedProvince)
        enrichedProvince["ownercountry"] = None
        enrichedProvince["controllercountry"] = None
        enrichedProvince["country"] = None

        
        # print("Debug: province center =", enrichedProvince["center"])  
        enrichedList.append(enrichedProvince)
        testCounter += 1  

    # print("Total provinces:", testCounter)
    #print(enrichedList[0])
    return enrichedList




def buildprovinceadjacencygraph(provincemap, onprogress=None):
    provinceidlist = list(provincemap.keys())
    totalprovincecount = len(provinceidlist)


    # TEST OPTIMIZATION 3 APRIL
    totalprogresssteps = max(1, totalprovincecount * 2)
    if onprogress and not onprogress(0, totalprogresssteps):
        #print("PROGRES", totalprogresssteps)
        return None

    # larger cells will = faster but not as accurate
    gridcellsize = 32.0
    adjacencytestpadding = 1
    gridlookup = {}
    provinceentrylist = []

    for provinceindex, provinceid in enumerate(provinceidlist):
        #print(provinceindex, provinceid, provinceidlist[0])
        provincerectangle = provincemap[provinceid]["rectangle"]
        minimumgridx = int(math.floor((provincerectangle.left - adjacencytestpadding) / gridcellsize))
        maximumgridx = int(math.floor((provincerectangle.right + adjacencytestpadding) / gridcellsize))
        minimumgridy = int(math.floor((provincerectangle.top - adjacencytestpadding) / gridcellsize))
        maximumgridy = int(math.floor((provincerectangle.bottom + adjacencytestpadding) / gridcellsize))

        provinceentrylist.append((provinceid, provincerectangle, minimumgridx, maximumgridx, minimumgridy, maximumgridy))

        for gridx in range(minimumgridx, maximumgridx + 1):
            for gridy in range(minimumgridy, maximumgridy + 1):
                gridlookup.setdefault((gridx, gridy), []).append(provinceindex)

        #if onprogress and provinceindex % 100 == 0:
        #    onprogress(provinceindex, totalprogresssteps)
        #       if not onprogress(provinceindex, totalprogresssteps):
        #          return None

        if onprogress and (provinceindex == 0 or (provinceindex + 1) % 200 == 0 or (provinceindex + 1) == totalprovincecount):
            if not onprogress(provinceindex + 1, totalprogresssteps):
                return None

    adjacencygraph = {provinceid: set() for provinceid in provinceidlist}
    #print("graph adjacent", adjacencygraph)
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
            candidateprovinceid, secondrectangle, _, _, _, _ = provinceentrylist[candidateindex] 
            if rectanglesclose(firstrectangle, secondrectangle, padding=adjacencytestpadding):
                adjacencygraph[provinceid].add(candidateprovinceid)
                adjacencygraph[candidateprovinceid].add(provinceid)

        if onprogress and (provinceindex == 0 or (provinceindex + 1) % 100 == 0 or (provinceindex + 1) == totalprovincecount):
            if not onprogress(totalprovincecount + provinceindex + 1, totalprogresssteps):
                return None
            

    #print(adjacencygraph)
    return adjacencygraph
    
    # optimization issue, cannot run on Benedict's AMD computer, might need to optimize the adjacency graph building 



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

    #  A* 
    while openheap:
        _, currentprovinceid = heapq.heappop(openheap) # total province with lowest cost
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




# def processmovementorders(movementorderlist, provincemap):
#     finishedorderlist = []
# 
# 
# 
#     for movementorder in movementorderlist:
#         movementpoints = 1.0 * float(movementorder.get("speedmodifier", 1.0))
#         pathlist = movementorder["path"]
#         currentpathindex = movementorder["index"]
#         movingcountry = movementorder.get("controllercountry", movementorder.get("country"))
#         movingcountrycolor = movementorder.get("countrycolor")
# 
#         while currentpathindex < len(pathlist) - 1:
# 
# 
#             nextprovinceid = pathlist[currentpathindex + 1]
#             nextprovince = provincemap[nextprovinceid]
#             movecost = getterrainmovecost(nextprovince)
# 
#             if movementpoints < movecost: # move next turn if not enough
#                 break
# 
#             if movingcountry is None: 
#                 movingcountry = getprovincecontroller(provincemap[pathlist[currentpathindex]])
#                 movementorder["controllercountry"] = movingcountry
#                 movementorder["country"] = movingcountry
# 
#             nextcountry = getprovincecontroller(nextprovince)
#             if (
#                 movingcountry is not None
#                 and nextcountry is not None
#                 and nextcountry != movingcountry
#                 and nextprovince["troops"] > 0
#             ):
#                 attackers = movementorder["amount"]
#                 defenders = nextprovince["troops"]
#                 if attackers <= defenders:
#                     nextprovince["troops"] = defenders - attackers
#                     movementorder["amount"] = 0
#                     break
# 
#                 movementorder["amount"] = attackers - defenders
#                 nextprovince["troops"] = 0
# 
# 
# 
#             movementpoints -= movecost
#             currentpathindex += 1
# 
#             if (
#                 movingcountry is not None
#                 and nextcountry is not None
#                 and nextcountry != movingcountry
#                 and nextprovince["troops"] <= 0
#             ):
#                 setprovincecontroller(nextprovince, movingcountry, movingcountrycolor)
# 
#         movementorder["index"] = currentpathindex
#         movementorder["current"] = pathlist[currentpathindex]
# 
# 
# 
# 
#         if movementorder["amount"] <= 0:
#             finishedorderlist.append(movementorder)
#         elif currentpathindex >= len(pathlist) - 1:
#             destinationprovinceid = pathlist[-1]
#             provincemap[destinationprovinceid]["troops"] += movementorder["amount"]
#             finishedorderlist.append(movementorder)
# 
#     for finishedorder in finishedorderlist:
#         movementorderlist.remove(finishedorder)




# TODO: handle occupation, changing the province ownership when all enemy troops are removed and the player moves into the province, or the npc moves into the province or the players province


# Movement ends
# GAME LOGIC AND RENDERING ENDSS


# get the current province at mouse position
def getprovinceatmouse(mouseposition, provincelist, zoomvalue, camerax, cameray, screenrectangle=None):
    # Delegate to API module to keep runtime thin.
    return apimodule.getprovinceatmouse(mouseposition, provincelist, zoomvalue, camerax, cameray, screenrectangle)

# Loading screen and main loop starts 
# start after main()




def drawloadingscreen(screen, largefont, smallfont, completedcount, totalcount):
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            return False


    progressvalue = 0.0 if totalcount <= 0 else completedcount / totalcount


    progressvalue = max(0.0, min(1.0, progressvalue))

    screen.fill((18, 18, 22))
    #print("progress", progressvalue, completedcount, totalcount)
    windowwidth, windowheight = screen.get_size()




    titletextabovebar = largefont.render("Engine: Precompiling map data...", True, (240, 240, 240))
    screen.blit(titletextabovebar, titletextabovebar.get_rect(center=(windowwidth // 2, windowheight // 2 - 40)))



    barwidth = min(640, windowwidth - 120)
    barheight = 22
    barx = (windowwidth - barwidth) // 2
    bary = windowheight // 2 + 4

    pygame.draw.rect(screen, (60, 60, 70), (barx, bary, barwidth, barheight), border_radius=1)
    pygame.draw.rect(screen, (120, 190, 255), (barx, bary, int(barwidth * progressvalue), barheight), border_radius=1)
    pygame.draw.rect(screen, (120, 120, 130), (barx, bary, barwidth, barheight), 1, border_radius=1)

    progresstext = smallfont.render(f"{completedcount}/{totalcount} provinces", True, (255, 255, 255))
    screen.blit(progresstext, progresstext.get_rect(center=(windowwidth // 2, bary + 10)))

    pygame.display.flip()
    return True





def main(eventbus=None):
    if eventbus is None:
        eventbus = EventBus()

    startupbegintimestamp = time.perf_counter()
    pygame.init()


    logstartupdiagnostics(startupbegintimestamp, "pygame init", f"python={platform.python_version()} pygame={pygame.version.ver}")
    screen = pygame.display.set_mode((defaultwindowwidth, defaultwindowheight), pygame.RESIZABLE)
    logstartupdiagnostics(
        startupbegintimestamp,
        "window created",
        f"size={defaultwindowwidth}x{defaultwindowheight} driver={pygame.display.get_driver()}",
    )

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




    logstartupdiagnostics(startupbegintimestamp, "fonts done", f"development_mode={developmentmode}")
    if not drawloadingscreen(screen, loadingtitlefont, loadingtextfont, 0, 1):
        pygame.quit()
        return

    #TODO: make loading screen better, preferably show which file is loading,
    # current state, it just says provinces and never update


    stateprogresscallback = createloadingprogresscallback(
        lambda completed, total: drawloadingscreen(screen, loadingtitlefont, loadingtextfont, completed, total),
        startupbegintimestamp,
        "loading states.svg",
    )


    stateshapelist = loadsvgshapes(
        statefilepath,
        onprogress=stateprogresscallback,
    )
    if not stateshapelist:
        pygame.quit()
        return
    

    logstartupdiagnostics(startupbegintimestamp, "states loaded", f"count={len(stateshapelist)}")
    statetocountrylookup, countrytocolorlookup = loadcountrydata(countrydatafilepath)


    logstartupdiagnostics(
        startupbegintimestamp,
        "countries loaded",
        f"state_links={len(statetocountrylookup)} country_colors={len(countrytocolorlookup)}",
    )
    for stateshape in stateshapelist: # to prepare to load province data and assign countries to state 
        statecountry = statetocountrylookup.get(stateshape["id"])
        stateshape["ownercountry"] = statecountry
        stateshape["controllercountry"] = statecountry
        stateshape["country"] = statecountry
        stateshape["countrycolor"] = countrytocolorlookup.get(statecountry, (85, 85, 85)) 




    provinceprogresscallback = createloadingprogresscallback(
        lambda completed, total: drawloadingscreen(screen, loadingtitlefont, loadingtextfont, completed, total),
        startupbegintimestamp,
        "loading provinces.svg",
    )



    provinceshapelist = loadsvgshapes(
        provincefilepath if False else provincefilepath,
        onprogress=provinceprogresscallback,
    )



    # fix accidental typo safely
    if not provinceshapelist:
        provinceprogresscallback = createloadingprogresscallback(
            lambda completed, total: drawloadingscreen(screen, loadingtitlefont, loadingtextfont, completed, total),
            startupbegintimestamp,
            "loading provinces.svg (retry)",
        )
        provinceshapelist = loadsvgshapes(
            provincefilepath if False else provincefilepath,
            onprogress=provinceprogresscallback,
        )
    if not provinceshapelist:
        pygame.quit()
        return
    


    logstartupdiagnostics(startupbegintimestamp, "provinces loaded", f"count={len(provinceshapelist)}")
    provinceenrichedlist = prepareprovincemetadata(provinceshapelist)
    logstartupdiagnostics(startupbegintimestamp, "province metadata done", f"count={len(provinceenrichedlist)}")



    for province in provinceenrichedlist:
        provincecountry = statetocountrylookup.get(province["parentstateid"])
        province["ownercountry"] = provincecountry
        province["controllercountry"] = provincecountry
        province["country"] = provincecountry
        province["countrycolor"] = countrytocolorlookup.get(provincecountry, (85, 85, 85))

    provincemap = {province["id"]: province for province in provinceenrichedlist} 



    graphprogresscallback = createloadingprogresscallback(
        lambda completed, total: drawloadingscreen(screen, loadingtitlefont, loadingtextfont, completed, total),
        startupbegintimestamp,
        "building province graph",
    )
    provincegraph = buildprovinceadjacencygraph(
        provincemap,
        # if not graphprogresscallback:
        #     pygame.quit()
        #     return

        onprogress=graphprogresscallback,
    )



    #CRASH if no provincegraph, this is for Benedict's AMD issue
    if provincegraph is None:
        pygame.quit()
        return
    totaledges = sum(len(neighborset) for neighborset in provincegraph.values()) // 2
    logstartupdiagnostics(
        startupbegintimestamp,
        "province graph done",
        f"nodes={len(provincegraph)} edges={totaledges}",
    )



    groupedsubdivisionlookup = groupsubdivisionsbystate(provinceenrichedlist, stateshapelist)

    for stateshape in stateshapelist:

        subdivisionsforstate = groupedsubdivisionlookup.get(stateshape["id"], [])
        
        for province in subdivisionsforstate:
            ownercountry = stateshape.get("ownercountry", stateshape.get("country"))
            controllercountry = stateshape.get("controllercountry", stateshape.get("country"))
            province["ownercountry"] = ownercountry
            setprovincecontroller(province, controllercountry, stateshape.get("countrycolor", (85, 85, 85)))
        stateshape["subdivisions"] = subdivisionsforstate



    mapbox = getmapbox(stateshapelist)
    logstartupdiagnostics(
        startupbegintimestamp,
        "startup complete",
        f"map_size={mapbox['width']:.1f}x{mapbox['height']:.1f}",
    )
    eventbus.emit(
        EngineEventType.WORLDLOADED,
        {
            "stateCount": len(stateshapelist),
            "provinceCount": len(provincemap),
            "edgeCount": totaledges,
        },
    )


    
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

    # Economy defaults come from economy module
    currentturnnumber = 1
    economyconfig = getdefaulteconomyconfig()
    (
        playergold,
        playerpopulation,
        recruitamount,
        recruitgoldcostperunit,
        recruitpopulationcostperunit,
    ) = initializeplayereconomy(economyconfig)


    movementorderlist = []
    routepreviewset = set()
    countriesatwarset = set() # track countries at war
    countrymenutarget = None

    devconsole = developmentconsole(enabled=developmentmode)
    newssystem = NewsSystem(eventbus)
    newssystem.start()
    newspopup = NewsPopup()
    runtimeui = EngineUI((windowwidth, windowheight))








    isrunning = True
    while isrunning:
        elapsedseconds = clock.tick(60) / 1000.0
        mouseposition = pygame.mouse.get_pos()
        #this gives x and y (0 and 1)
        windowwidth, windowheight = screen.get_size()

        panpixels = edgepanspeed * elapsedseconds
        # pan the camera
        if mouseposition[0] <= edgepanmargin:
            camerax += panpixels
        elif mouseposition[0] >= windowwidth - edgepanmargin:
            camerax -= panpixels

        """ disabled for now, because everytime i click any button near the edge the camera will pan and itis getting annoying
        if mouseposition[1] <= edgepanmargin:
            cameray += panpixels
        elif mouseposition[1] >= windowheight - edgepanmargin:
            cameray -= panpixels
        """

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
        troopbadgelist = [] # store troop badge info



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
                    subdivisions = stateshape.get("subdivisions", [])
                    if subdivisions:
                        controllercountries = {getprovincecontroller(province) for province in subdivisions}
                        controllercountries.discard(None)
                        if len(controllercountries) == 1:
                            statecontroller = next(iter(controllercountries))
                            stateshape["controllercountry"] = statecontroller
                            stateshape["country"] = statecontroller
                            stateshape["countrycolor"] = subdivisions[0].get("countrycolor", stateshape.get("countrycolor", defaultshapecolor))
                        else:
                            stateshape["controllercountry"] = None
                            stateshape["country"] = None

                    hasmixedcontrol = False #contested state 
                    if subdivisions:
                        subdivisioncontrollers = {getprovincecontroller(province) for province in subdivisions}
                        hasmixedcontrol = len(subdivisioncontrollers) > 1

                    if (expandedstateid == stateshape["id"] and subdivisions) or hasmixedcontrol:
                        drawitemlist = subdivisions
                    else:
                        drawitemlist = [stateshape]
            # FOR QUICK SEARCH: "mixed control state"


                # for quick search: "drawitemlist loop"
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




                    # determine fill color based on game state and interactions
                    if gamephase == "choosecountry":
                        if stateshape.get("country"):
                            basefillcolor = stateshape.get("countrycolor", defaultshapecolor)

                        else:
                            basefillcolor = (75, 75, 75)

                        if pendingcountry and stateshape.get("country") == pendingcountry:
                            pulsevalue = 0.35 + 0.45 * (0.5 + 0.5 * math.sin(pygame.time.get_ticks() * 0.008))
                            basefillcolor = gui_lightencolor(basefillcolor, pulsevalue)


                    elif drawitem.get("id") == selectedprovinceid:
                        basefillcolor = (232, 214, 103)


                    elif drawitem.get("id") in routepreviewset:
                        basefillcolor = (95, 145, 255)


                    elif any(order["current"] == drawitem.get("id") for order in movementorderlist):
                        basefillcolor = (132, 96, 226)



                    else:
                        if drawitem is stateshape and stateshape.get("subdivisions"):
                            ownercolors = {
                                province.get("countrycolor")
                                for province in stateshape["subdivisions"]
                                if province.get("countrycolor") is not None
                            }
                            if len(ownercolors) == 1:
                                basefillcolor = next(iter(ownercolors))
                            else:
                                basefillcolor = drawitem.get("countrycolor", stateshape.get("countrycolor", defaultshapecolor))
                        else:
                            basefillcolor = drawitem.get("countrycolor", stateshape.get("countrycolor", defaultshapecolor))



                    finalfillcolor = hovercolor if itemhovered else basefillcolor
                    for drawpolygon in drawpolygonlist:
                        pygame.draw.polygon(screen, finalfillcolor, drawpolygon)
                        pygame.draw.polygon(screen, (50, 50, 50), drawpolygon, 1)

                    if gamephase == "play" and "troops" in drawitem and drawitem["troops"] > 0 and itemrectanglescreen.colliderect(screenrectangle):
                        troopbadgelist.append((itemrectanglescreen.center, drawitem["troops"])) #store as screen coords, troop count

        canrecruit = selectedprovinceid is not None and getprovincecontroller(provincemap[selectedprovinceid]) == playercountry
        recruitgoldcost, recruitpopulationcost = getrecruitcosts(
            recruitamount,
            recruitgoldcostperunit,
            recruitpopulationcostperunit,
        )
        recruitenabled = canrecruit and canrecruittroops(
            playergold,
            playerpopulation,
            recruitgoldcost,
            recruitpopulationcost,
            developmentmode=developmentmode,
        )

        runtimeui.sync(
            gamephase,
            pendingcountry,
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
            countrymenutarget,
            countriesatwarset,
            hovertext,
            mouseposition,
            troopbadgelist,
        )
        runtimeui.update(elapsedseconds)
        runtimeui.draw(screen)





        #DRAW GUIS, ON TOP
        devconsole.draw(screen, normalfont, smallfont) # draw dev console after ui so that it appears on top
        newspopup.draw(screen, (titlefont, normalfont), newssystem.current)





        for event in pygame.event.get():
            uiaction = runtimeui.process_event(event)

            if uiaction == EngineUI.actiondeclarewar and gamephase == "play":
                if countrymenutarget and countrymenutarget != playercountry:
                    countriesatwarset.add(countrymenutarget)
                    eventbus.emit(
                        EngineEventType.WARDECLARED,
                        {
                            "attacker": playercountry,
                            "defender": countrymenutarget,
                            "turn": currentturnnumber,
                        },
                    )
                countrymenutarget = None
                continue

            if uiaction == EngineUI.actionrecruit and gamephase == "play":
                if selectedprovinceid:
                    selectedprovince = provincemap[selectedprovinceid]
                    if getprovincecontroller(selectedprovince) == playercountry:
                        requiredgold, requiredpopulation = getrecruitcosts(
                            recruitamount,
                            recruitgoldcostperunit,
                            recruitpopulationcostperunit,
                        )
                        if canrecruittroops(
                            playergold,
                            playerpopulation,
                            requiredgold,
                            requiredpopulation,
                            developmentmode=developmentmode,
                        ):
                            selectedprovince["troops"] += recruitamount
                            if not developmentmode:
                                playergold -= requiredgold
                                playerpopulation -= requiredpopulation
                            eventbus.emit(
                                EngineEventType.TROOPSRECRUITED,
                                {
                                    "country": playercountry,
                                    "provinceId": selectedprovinceid,
                                    "amount": recruitamount,
                                    "turn": currentturnnumber,
                                },
                            )
                continue

            if uiaction == EngineUI.actionendturn and gamephase == "play":
                processmovementorders(movementorderlist, provincemap, emit=eventbus.emit)
                playergold,playerpopulation = applyendturneconomy(
                    playercountry,
                    provincemap,
                    playergold,
                    playerpopulation,
                )
                currentturnnumber += 1
                routepreviewset = set()
                eventbus.emit(
                    EngineEventType.NEXTTURN,
                    {
                        "turn": currentturnnumber,
                        "playerCountry": playercountry,
                        "playerGold": playergold,
                        "playerPopulation": playerpopulation,
                    },
                )
                continue

            if event.type == pygame.QUIT:
                isrunning = False





            #GUI INTERACTIONS

           # elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # if newssystem.current and newspopup.handleclick(event.pos):
                #     newssystem.closecurrent()
                #     continue
                # if newssystem.current:
                #     continue
                # 
                # if devconsole.handleleftclick(event.pos):
   
   
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if newssystem.current and newspopup.handleclick(event.pos):
                    newssystem.closecurrent()
                    continue

                if devconsole.handleleftclick(event.pos):
                    continue


                #fix issue where choose country button is blocked
                if gamephase != "choosecountry" and runtimeui.ispointeroverui(event.pos):
                    continue

                if gamephase == "choosecountry":

                    if hoveredstateid:
                        selectedstateobject = next((state for state in stateshapelist if state["id"] == hoveredstateid), None)
                        if selectedstateobject and selectedstateobject.get("country"):

                            #engine bus

                            pendingcountry = selectedstateobject["country"]
                            eventbus.emit(
                                EngineEventType.COUNTRYCANDIDATESELECTED,
                                {
                                    "country": pendingcountry,
                                    "stateId": selectedstateobject["id"],
                                },
                            )

                    if runtimeui.clickchoosebutton(event.pos) and pendingcountry:
                        playercountry = pendingcountry
                        gamephase = "play"
                        expandedstateid = None
                        selectedprovinceid = None
                        routepreviewset = set()
                        countriesatwarset = set()
                        countrymenutarget = None
                        eventbus.emit(
                            EngineEventType.PLAYERCOUNTRYSELECTED,
                            {
                                "country": playercountry,
                            },
                        )


                    continue



                # collidepoint checks button and country menu interacts
                if gamephase == "play":
                    if countrymenutarget:
                        countrymenutarget = None
                        continue





                    if hoveredprovinceid:
                        selectedprovince = provincemap.get(hoveredprovinceid)
                        if selectedprovince and getprovincecontroller(selectedprovince) == playercountry:
                            selectedprovinceid = hoveredprovinceid
                            expandedstateid = selectedprovince.get("parentid", hoveredstateid)
                            routepreviewset = set()
                            countrymenutarget = None
                            eventbus.emit(
                                EngineEventType.PROVINCESELECTED,
                                {
                                    "provinceId": selectedprovinceid,
                                    "stateId": selectedprovince.get("parentid"),
                                    "country": getprovincecontroller(selectedprovince),
                                },
                            )
                            continue

                    if hoveredstateid is not None:
                        expandedstateid = hoveredstateid
                        eventbus.emit(
                            EngineEventType.STATESELECTED,
                            {
                                "stateId": expandedstateid,
                            },
                        )
                    else:
                        expandedstateid = None
                        selectedprovinceid = None
                        routepreviewset = set()

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 3: # right click for move orders
                if devconsole.visible or gamephase != "play":
                    continue

                # Only open the country interaction menu when the click is on a state (no hovered province).
                if hoveredprovinceid is None:
                    if hoveredstateid is not None:
                        selectedstateobject = next((state for state in stateshapelist if state["id"] == hoveredstateid), None)
                        if selectedstateobject:
                            destinationcountry = selectedstateobject.get("controllercountry", selectedstateobject.get("country"))
                            if playercountry and destinationcountry and destinationcountry != playercountry:
                                countrymenutarget = destinationcountry
                                routepreviewset = set()
                                continue
                    countrymenutarget = None
                    continue

                destinationprovince = provincemap.get(hoveredprovinceid)
                if not destinationprovince:
                    continue

                destinationcountry = getprovincecontroller(destinationprovince)
                if playercountry and destinationcountry and destinationcountry != playercountry:
                    if destinationcountry not in countriesatwarset:
                        countrymenutarget = destinationcountry
                        routepreviewset = set() # set() is an empty set to clear route preview
                        continue

                countrymenutarget = None





                if selectedprovinceid is None:
                    continue
                if hoveredprovinceid == selectedprovinceid:
                    continue

                sourceprovince = provincemap.get(selectedprovinceid)
                if not sourceprovince:
                    continue
                if getprovincecontroller(sourceprovince) != playercountry:
                    continue
                if sourceprovince["troops"] <= 0:
                    continue





                allowedcountryset = {playercountry} | countriesatwarset
                if destinationcountry not in allowedcountryset:
                    continue


                allowedprovinceidset = {
                    provinceid for provinceid, province in provincemap.items() if getprovincecontroller(province) in allowedcountryset
                } # this allows movement thrugh your own province and supposedly the enemy provinces
                # TODO: fix the issue that you cannot move through enemy provinces



                #Path findign

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
                            "path": foundpath, # list of province ids to move through in order per turn
                            "index": 0, # the current provincei n the path list
                            "current": foundpath[0],
                            "speedmodifier": 1.0,
                            "controllercountry": getprovincecontroller(sourceprovince),
                            "country": getprovincecontroller(sourceprovince),
                            "countrycolor": sourceprovince.get("countrycolor"),
                        }
                    )
                    eventbus.emit(
                        EngineEventType.MOVEORDERCREATED,
                        {
                            "sourceProvinceId": selectedprovinceid,
                            "destinationProvinceId": hoveredprovinceid,
                            "path": list(foundpath),
                            "troops": movingtroopcount,
                            "country": getprovincecontroller(sourceprovince),
                            "turn": currentturnnumber,
                        },
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

            # (for quick ctrl f: developer console)
                if devconsole.handlekeydown(event, provincemap, playercountry, countrytocolorlookup, defaultshapecolor, troopbadgelist, eventbus=eventbus):
                    continue # handle dev console input




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
                runtimeui.setwindowsize((newwindowwidth, newwindowheight))



        pygame.display.flip()

    newssystem.stop()
    pygame.quit()
# loading screen and main loop ends






























# DEFINITIONS
loadsvgshapes = coremodule.loadsvgshapes
getmapbox = coremodule.getmapbox
getscreenpoints = coremodule.getscreenpoints
getscreenrectangle = coremodule.getscreenrectangle
getminimumzoomforheight = coremodule.getminimumzoomforheight
clampverticalcamera = coremodule.clampverticalcamera
wraphorizontalcamera = coremodule.wraphorizontalcamera
ispointinsidepolygon = coremodule.ispointinsidepolygon
loadcountrydata = coremodule.loadcountrydata
groupsubdivisionsbystate = coremodule.groupsubdivisionsbystate

getprovincecontroller = gameplaymodule.getprovincecontroller
getprovinceowner = gameplaymodule.getprovinceowner
setprovincecontroller = gameplaymodule.setprovincecontroller
prepareprovincemetadata = gameplaymodule.prepareprovincemetadata
buildprovinceadjacencygraph = gameplaymodule.buildprovinceadjacencygraph
getterrainmovecost = gameplaymodule.getterrainmovecost
findprovincepath = gameplaymodule.findprovincepath
processmovementorders = gameplaymodule.processmovementorders

getrecruitcosts = economymodule.getrecruitcosts
canrecruittroops = economymodule.canrecruittroops
applyendturneconomy = economymodule.applyendturneconomy
getdefaulteconomyconfig = economymodule.getdefaulteconomyconfig
initializeplayereconomy = economymodule.initializeplayereconomy



main()

