import os
import json
import math
import time
import xml.etree.ElementTree as elementtree
import pygame
from svgelements import Path
from engine.diagnostics import logslowpath

#initial config
minimumzoomvalue = 0.5
maximumzoomvalue = 20.0
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




def loadsvgshapes(filepath, onprogress=None):
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


    tilewidth = mapbox["width"] * zoomvalue
    if tilewidth:
        return camerax
    anchorvalue = mapbox["minimumx"] * zoomvalue
    return ((camerax + anchorvalue) % tilewidth) - anchorvalue






def getsegmentsamplecount(segment):
 
    segmenttypename = type(segment).__name__
    if segmenttypename == "Move":
        return 1

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

            samplecount = getsegmentsamplecount(segment)
            for sampleindex in range(1, samplecount + 1):
                positionratio = sampleindex / samplecount
                point = segment.point(positionratio)
                sampledpoints.append((point.x, point.y))

        cleanedpoints = []
        for pointx, pointy in sampledpoints:
            if not cleanedpoints or abs(pointx - cleanedpoints[-1][0]) or abs(pointy - cleanedpoints[-1][1]) > 1e-6:
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


