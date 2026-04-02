import math
import pygame

""" WINDOW FORMAT
window_width, window_height = screen.get_size()
simple_window_width = 250
simple_window_height = 150
margin = 30  # distance from the right edge

# Calculate position: center vertically, right-aligned
x = window_width - simple_window_width - margin
y = (window_height - simple_window_height) // 2

window_rect = pygame.Rect(x, y, simple_window_width, simple_window_height)
pygame.draw.rect(screen, (40, 40, 60), window_rect, border_radius=10)
pygame.draw.rect(screen, (120, 120, 180), window_rect, width=2, border_radius=10)

usage of pygame.draw.rect is pygame.draw.rect(surface, color, rect, width (default 0), border_radius (default 0))

"""



def gui_lightencolor(colorvalue, amount):
    amount = max(0.0, min(1.0, amount))
    red, green, blue = colorvalue
    return (
        int(red + (255 - red) * amount),
        int(green + (255 - green) * amount),
        int(blue + (255 - blue) * amount),
    )


def gui_drawbutton(screen, rectangle, textvalue, fontobject, enabled=True, pulse=False):
    if enabled:
        basecolor = (56, 116, 198)
        if pulse:
            timer = pygame.time.get_ticks() * 0.008
            glowamount = 0.2 + 0.35 * (0.5 + 0.5 * math.sin(timer))
            basecolor = gui_lightencolor(basecolor, glowamount)
    else:
        basecolor = (70, 70, 70)

    pygame.draw.rect(screen, basecolor, rectangle, border_radius=6)
    pygame.draw.rect(screen, (35, 35, 35), rectangle, width=1, border_radius=6)
    textcolor = (240, 240, 240) if enabled else (145, 145, 145)
    labelsurface = fontobject.render(textvalue, True, textcolor)
    screen.blit(labelsurface, labelsurface.get_rect(center=rectangle.center))


def gui_drawtroopcountbadge(screen, centerposition, troopcount, fontobject):
    labelsurface = fontobject.render(str(troopcount), True, (255, 255, 255))
    labelrectangle = labelsurface.get_rect()
    labelrectangle.inflate_ip(10, 6)
    labelrectangle.center = (int(centerposition[0]), int(centerposition[1]))
    pygame.draw.rect(screen, (0, 0, 0), labelrectangle, border_radius=4)
    pygame.draw.rect(screen, (165, 165, 165), labelrectangle, width=1, border_radius=4)
    screen.blit(labelsurface, labelsurface.get_rect(center=labelrectangle.center))


def gui_drawchoosecountryoverlay(screen, titlefontobject, fontobject, selectedcountry):
    windowwidth, windowheight = screen.get_size()
    darksurface = pygame.Surface((windowwidth, windowheight), pygame.SRCALPHA)
    darksurface.fill((0, 0, 0, 95))
    screen.blit(darksurface, (0, 0))

    titletext = titlefontobject.render("choose your country", True, (250, 250, 250))
    screen.blit(titletext, titletext.get_rect(midtop=(windowwidth // 2, 16)))

    helptext = fontobject.render("click on any provinces to select the country", True, (225, 225, 225))
    screen.blit(helptext, helptext.get_rect(midtop=(windowwidth // 2, 58)))

    choosebuttonrectangle = pygame.Rect(windowwidth - 210, windowheight - 56, 190, 38)
    canchoosecountry = selectedcountry is not None
    gui_drawbutton(
        screen,
        choosebuttonrectangle,
        "choose country",
        fontobject,
        enabled=canchoosecountry, # only enable the button if a country is selected
        pulse=canchoosecountry,
    )

    if selectedcountry:
        selectedlabel = fontobject.render(f"selected: {selectedcountry}", True, (240, 240, 240))
        screen.blit(selectedlabel, (20, windowheight - 48))

    return choosebuttonrectangle, canchoosecountry


def gui_drawcountryinteractionmenu(screen, fontobject, smallfontobject, targetcountry, alreadyatwar):
    placehldr, windowheight = screen.get_size()
    menuwidth = 280
    menuheight = 154
    menux = 0
    menuy = (windowheight - menuheight) // 2
    menurectangle = pygame.Rect(menux, menuy, menuwidth, menuheight)

    pygame.draw.rect(screen, (26, 26, 35), menurectangle, border_radius=10)
    pygame.draw.rect(screen, (92, 92, 116), menurectangle, width=2, border_radius=10)

    titlelabel = fontobject.render("Country actions", True, (240, 240, 240)) #titletext for country meus
    screen.blit(titlelabel, (menurectangle.x + 12, menurectangle.y + 10))

    countrylabel = fontobject.render(targetcountry, True, (220, 220, 220))
    screen.blit(countrylabel, (menurectangle.x + 12, menurectangle.y + 34))

    statustext = "status: at war" if alreadyatwar else "status: peace"
    statuslabel = smallfontobject.render(statustext, True, (205, 205, 215))
    screen.blit(statuslabel, (menurectangle.x + 12, menurectangle.y + 58))

    declarebuttonrectangle = pygame.Rect(menurectangle.x + 12, menurectangle.y + 82, menurectangle.width - 24, 38)
    gui_drawbutton(
        screen,
        declarebuttonrectangle,
        "already at war" if alreadyatwar else "declare war",
        fontobject,
        enabled=not alreadyatwar,
        pulse=not alreadyatwar,
    )

    hintlabel = smallfontobject.render("left click to confirm action", True, (178, 178, 188))
    screen.blit(hintlabel, (menurectangle.x + 12, menurectangle.y + 126))

    return menurectangle, declarebuttonrectangle


# GAMEPLAY HUD starts here, renders every frame during play phase
# might need to simplify this later its getting confusing
def gui_drawgameplayhud(
    screen,
    fontobject,
    smallfontobject,
    playercountry,
    currentturnnumber,
    currentgold,
    currentpopulation,
    selectedprovinceid,
    provincemap,
    recruitamount,
    recruitenabled,
    developmentmode,
    recruitgoldcost,
    recruitpopulationcost,
): 
    windowwidth, windowheight = screen.get_size()

    topsurface = pygame.Surface((windowwidth, 74), pygame.SRCALPHA) # semi-transparent surface for text background
    topsurface.fill((0, 0, 0, 120))
    screen.blit(topsurface, (0, 0))

    headertext = f"{playercountry} | turn {currentturnnumber} | gold {currentgold} | population {currentpopulation}" # header text with player info
    screen.blit(fontobject.render(headertext, True, (242, 242, 242)), (10, 8))

    if selectedprovinceid:
        selectedprovince = provincemap[selectedprovinceid]
        detailtext = (
            f"province: {selectedprovinceid} | troops: {selectedprovince['troops']} | "
            f"terrain: {selectedprovince['terrain']}"
        ) # detail text for selected province
        screen.blit(fontobject.render(detailtext, True, (236, 236, 236)), (10, 30))
    else:
        screen.blit(fontobject.render("select a province in your country", True, (205, 205, 205)), (10, 30))

    controltext = "left click: open state/select province | right click foreign province: country actions"
    screen.blit(smallfontobject.render(controltext, True, (215, 215, 215)), (10, 52))

    recruitbuttonrectangle = pygame.Rect(windowwidth - 390, windowheight - 56, 170, 38)
    endturnbuttonrectangle = pygame.Rect(windowwidth - 210, windowheight - 56, 190, 38)
    gui_drawbutton(screen, recruitbuttonrectangle, f"recruit +{recruitamount}", fontobject, enabled=recruitenabled)
    gui_drawbutton(screen, endturnbuttonrectangle, "end turn", fontobject, enabled=True)

    if not developmentmode:
        costtext = smallfontobject.render(
            f"cost: {recruitgoldcost}g, {recruitpopulationcost} pop",
            True,
            (210, 210, 210),
        )
        screen.blit(costtext, (windowwidth - 390, windowheight - 72))

    return recruitbuttonrectangle, endturnbuttonrectangle
