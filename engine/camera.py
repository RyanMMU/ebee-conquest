import pygame

minimumzoomvalue = 0.5
maximumzoomvalue = 20.0


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
