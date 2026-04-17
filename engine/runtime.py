import os
import json
import math
import time
import platform
import pygame
import xml.etree.ElementTree as elementtree
from svgelements import Path
import ctypes
ctypes.windll.user32.SetProcessDPIAware()

#Local module
from engine.console import developmentconsole, loaddevmodeflag 
from engine.gui import EngineUI, gui_lightencolor, gui_gettroopbadgerect
from engine.diagnostics import logstartupdiagnostics, createloadingprogresscallback, logslowpath
from . import core as coremodule
from . import movement as movementmodule
from . import economy as economymodule
from . import api as apimodule
from . import camera as cameramodule
from .events import EventBus, EngineEventType


from .apicalltest.newsbannereventtest import NewsSystem, NewsPopup # TEST API CALL





print("CURRENT VERSION - APRIL 17 2024")
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
minimumzoomvalue = cameramodule.minimumzoomvalue
maximumzoomvalue = cameramodule.maximumzoomvalue
zoomstepvalue = cameramodule.zoomstepvalue
edgepanmargin = cameramodule.defaultpanconfig.margin
edgepanspeed = cameramodule.defaultpanconfig.speed
curvesamplestep = 1.5
maxsegmentsteps = 48
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


# GAME LOGIC AND RENDERING STARTS



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



# TROOP BADGE MULTISELECT

def makerectfrompoints(startposition, endposition):
    startx, starty = startposition
    endx, endy = endposition
    left = min(startx, endx)
    top = min(starty, endy)
    width = abs(endx - startx)
    height = abs(endy - starty)
    return pygame.Rect(left, top, width, height)


def getbadgehitprovinceid(mouseposition, badgehitlist):
    for badgeentry in reversed(badgehitlist):
        if badgeentry["rect"].collidepoint(mouseposition):
            return badgeentry["provinceid"]
    return None


def getdragselectedprovinceids(selectionrect, badgehitlist, provincemap, playercountry):
    selectedids = []
    for badgeentry in badgehitlist:
        provinceid = badgeentry["provinceid"]
        province = provincemap.get(provinceid)
        if not province:
            continue
        if getprovincecontroller(province) != playercountry:
            continue
        if badgeentry["rect"].colliderect(selectionrect):
            selectedids.append(provinceid)
    return selectedids

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
    camerastate = cameramodule.createcamerastate(windowwidth, windowheight, mapbox)









    clock = pygame.time.Clock()
    expandedstateid = None
    selectedprovinceid = None
    selectedprovinceidset = set()

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

    dragselectstart = None
    dragselectcurrent = None
    isdragselecting = False
    dragminimumdistance = 8








    isrunning = True
    while isrunning:
        elapsedseconds = clock.tick(60) / 1000.0
        mouseposition = pygame.mouse.get_pos()
        #this gives x and y (0 and 1)
        windowwidth, windowheight = screen.get_size()

        cameramodule.applyedgepan(
            camerastate,
            mouseposition[0],
            windowwidth,
            elapsedseconds,
            edgepanmargin,
            edgepanspeed,
        )

        """ disabled for now, because everytime i click any button near the edge the camera will pan and itis getting annoying
        if mouseposition[1] <= edgepanmargin:
            cameray += panpixels
        elif mouseposition[1] >= windowheight - edgepanmargin:
            cameray -= panpixels
        """

        cameramodule.enforceminimumzoom(camerastate, windowwidth, windowheight, mapbox)
        cameramodule.clampcamerastate(camerastate, windowheight, mapbox)

        zoomvalue = camerastate.zoom
        camerax = camerastate.x
        cameray = camerastate.y

        screen.fill(backgroundcolor)

        hovertext = None
        hoveredstateid = None
        hoveredprovinceid = None
        screenrectangle = screen.get_rect()
        troopbadgelist = [] # store troop badge info
        troopbadgehitlist = []



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
                    # province color
                    if gamephase == "choosecountry":
                        if stateshape.get("country"):
                            basefillcolor = stateshape.get("countrycolor", defaultshapecolor)

                        else:
                            basefillcolor = (75, 75, 75)

                        if pendingcountry and stateshape.get("country") == pendingcountry:
                            pulsevalue = 0.35 + 0.45 * (0.5 + 0.5 * math.sin(pygame.time.get_ticks() * 0.008))
                            basefillcolor = gui_lightencolor(basefillcolor, pulsevalue)


                    elif drawitem.get("id") in selectedprovinceidset:
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

                        # for quick search: "troop badge hitbox"
                        troopbadgerect = gui_gettroopbadgerect(itemrectanglescreen.center, drawitem["troops"], runtimeui.troopbadgefont)
                        troopbadgehitlist.append(
                            {
                                "provinceid": drawitem["id"],
                                "rect": troopbadgerect,
                            }
                        )

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





        # DRAG SELECT RECTANGLE
        if gamephase == "play" and isdragselecting and dragselectstart and dragselectcurrent:
            selectionrect = makerectfrompoints(dragselectstart, dragselectcurrent)
            if selectionrect.width > 0 or selectionrect.height > 0:
                overlaysurface = pygame.Surface((selectionrect.width or 1, selectionrect.height or 1), pygame.SRCALPHA)
                overlaysurface.fill((95, 145, 255, 45))
                screen.blit(overlaysurface, selectionrect.topleft)
                pygame.draw.rect(screen, (95, 145, 255), selectionrect, width=1)





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




            # for quick search: "end turn button"
            # ON END TURN, process movement orders, apply economy, increment turn, emit next turn event
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
                        selectedprovinceidset = set()
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

                    dragselectstart = event.pos
                    dragselectcurrent = event.pos
                    isdragselecting = True

            elif event.type == pygame.MOUSEMOTION:
                if isdragselecting:
                    dragselectcurrent = event.pos

            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if gamephase != "play" or not isdragselecting:
                    continue

                dragselectcurrent = event.pos
                selectionrect = makerectfrompoints(dragselectstart, dragselectcurrent)
                isdragselecting = False

                hasdragdistance = max(selectionrect.width, selectionrect.height) >= dragminimumdistance
                if hasdragdistance:
                    selectedids = getdragselectedprovinceids(selectionrect, troopbadgehitlist, provincemap, playercountry)
                    selectedprovinceidset = set(selectedids)

                    if selectedids:
                        selectedprovinceid = selectedids[0]
                        selectedprovince = provincemap.get(selectedprovinceid)
                        expandedstateid = selectedprovince.get("parentid") if selectedprovince else expandedstateid
                        routepreviewset = set()
                        countrymenutarget = None
                        if selectedprovince:
                            eventbus.emit(
                                EngineEventType.PROVINCESELECTED,
                                {
                                    "provinceId": selectedprovinceid,
                                    "stateId": selectedprovince.get("parentid"),
                                    "country": getprovincecontroller(selectedprovince),
                                },
                            )
                    else:
                        selectedprovinceid = None
                        selectedprovinceidset = set()
                        routepreviewset = set()

                    dragselectstart = None
                    dragselectcurrent = None
                    continue

                clickedbadgeprovinceid = getbadgehitprovinceid(event.pos, troopbadgehitlist)
                if clickedbadgeprovinceid:
                    selectedprovince = provincemap.get(clickedbadgeprovinceid)
                    if selectedprovince and getprovincecontroller(selectedprovince) == playercountry:
                        selectedprovinceid = clickedbadgeprovinceid
                        selectedprovinceidset = {clickedbadgeprovinceid}
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
                        dragselectstart = None
                        dragselectcurrent = None
                        continue

                if hoveredprovinceid:
                    selectedprovince = provincemap.get(hoveredprovinceid)
                    if selectedprovince and getprovincecontroller(selectedprovince) == playercountry:
                        selectedprovinceid = hoveredprovinceid
                        selectedprovinceidset = {hoveredprovinceid}
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
                        dragselectstart = None
                        dragselectcurrent = None
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
                    selectedprovinceidset = set()
                    routepreviewset = set()

                dragselectstart = None
                dragselectcurrent = None

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


                # allows for multiple source provinces if you have multiple selected, prioritizes the hovered province if it is in the selection, then prioritizes the order of selection, then just goes through them in id order
                sourceprovinceidlist = []
                if selectedprovinceidset:
                    sourceprovinceidlist.extend(sorted(provinceid for provinceid in selectedprovinceidset if provinceid in provincemap))
                    if selectedprovinceid in sourceprovinceidlist:
                        sourceprovinceidlist.remove(selectedprovinceid)
                        sourceprovinceidlist.insert(0, selectedprovinceid)
                elif selectedprovinceid:
                    sourceprovinceidlist.append(selectedprovinceid)
                else:
                    continue

                routepreviewset = set()
                for sourceprovinceid in sourceprovinceidlist:
                    if sourceprovinceid == hoveredprovinceid:
                        continue

                    sourceprovince = provincemap.get(sourceprovinceid)
                    if not sourceprovince:
                        continue
                    if getprovincecontroller(sourceprovince) != playercountry:
                        continue
                    if sourceprovince["troops"] <= 0:
                        continue

                    foundpath = findprovincepath(
                        sourceprovinceid,
                        hoveredprovinceid,
                        provincemap,
                        provincegraph,
                        allowedprovinceidset=allowedprovinceidset,
                    )

                    routepreviewset.update(foundpath)
                    if len(foundpath) < 2:
                        continue

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
                            "sourceProvinceId": sourceprovinceid,
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

                
                mousex, mousey = pygame.mouse.get_pos()
                cameramodule.applywheelzoom(camerastate, event.y, windowheight, mapbox, mousex, mousey)
                cameramodule.clampcamerastate(camerastate, windowheight, mapbox)
                zoomvalue = camerastate.zoom
                camerax = camerastate.x
                cameray = camerastate.y

            elif event.type == pygame.KEYDOWN:

            # (for quick ctrl f: developer console)
                if devconsole.handlekeydown(event, provincemap, playercountry, countrytocolorlookup, defaultshapecolor, troopbadgelist, eventbus=eventbus):
                    continue # handle dev console input




            elif event.type == pygame.VIDEORESIZE:
                oldwindowwidth, oldwindowheight = screen.get_size()
                newwindowwidth = max(400, event.w)
                newwindowheight = max(300, event.h)

                screen = pygame.display.set_mode((newwindowwidth, newwindowheight), pygame.RESIZABLE)
                cameramodule.resizecamerastate(
                    camerastate,
                    oldwindowwidth,
                    oldwindowheight,
                    newwindowwidth,
                    newwindowheight,
                    mapbox,
                )
                cameramodule.clampcamerastate(camerastate, newwindowheight, mapbox)
                zoomvalue = camerastate.zoom
                camerax = camerastate.x
                cameray = camerastate.y
                runtimeui.setwindowsize((newwindowwidth, newwindowheight))



        pygame.display.flip()

    newssystem.stop()
    pygame.quit()
# loading screen and main loop ends






























# DEFINITIONS
loadsvgshapes = coremodule.loadsvgshapes
getmapbox = coremodule.getmapbox
getscreenpoints = cameramodule.getscreenpoints
getscreenrectangle = cameramodule.getscreenrectangle
getminimumzoomforheight = cameramodule.getminimumzoomforheight
clampverticalcamera = cameramodule.clampverticalcamera
wraphorizontalcamera = cameramodule.wraphorizontalcamera
ispointinsidepolygon = coremodule.ispointinsidepolygon
loadcountrydata = coremodule.loadcountrydata
groupsubdivisionsbystate = coremodule.groupsubdivisionsbystate

getprovincecontroller = movementmodule.getprovincecontroller
getprovinceowner = movementmodule.getprovinceowner
setprovincecontroller = movementmodule.setprovincecontroller
prepareprovincemetadata = movementmodule.prepareprovincemetadata
buildprovinceadjacencygraph = movementmodule.buildprovinceadjacencygraph
getterrainmovecost = movementmodule.getterrainmovecost
findprovincepath = movementmodule.findprovincepath
processmovementorders = movementmodule.processmovementorders

getrecruitcosts = economymodule.getrecruitcosts
canrecruittroops = economymodule.canrecruittroops
applyendturneconomy = economymodule.applyendturneconomy
getdefaulteconomyconfig = economymodule.getdefaulteconomyconfig
initializeplayereconomy = economymodule.initializeplayereconomy

