import math
import pygame

#dev console will not be included in the final 

def loaddevmodeflag(filepath="dev.txt"):
    try:
        with open(filepath, "r", encoding="utf-8") as fileobject:
            return fileobject.read().strip().lower() == "true"
    except OSError:
        return False


def rundevcommand(commandline, provincemap, playercountry, countrytocolor, fallbackcolor):
    commandparts = commandline.strip().split() # arguments
    if not commandparts:
        return "empty command"

    commandname = commandparts[0].lower()
    lowercaselookup = {provinceid.lower(): provinceid for provinceid in provincemap.keys()}

    def getprovinceid(rawtext):
        return lowercaselookup.get(rawtext.lower())




    if commandname == "add_troops" and len(commandparts) == 3:
        provinceid = getprovinceid(commandparts[1])
        if provinceid is None:
            return "province not found"
        try:
            amountvalue = max(0, int(commandparts[2]))
        except ValueError:
            return "amount must be int"
        provincemap[provinceid]["troops"] += amountvalue
        return f"ok {provinceid} troops={provincemap[provinceid]['troops']}"




    if commandname == "remove_troops" and len(commandparts) == 3:
        provinceid = getprovinceid(commandparts[1])
        if provinceid is None:
            return "province not found"
        try:
            amountvalue = max(0, int(commandparts[2]))
        except ValueError:
            return "amount must be int"
        provincemap[provinceid]["troops"] = max(0, provincemap[provinceid]["troops"] - amountvalue)
        return f"ok {provinceid} troops={provincemap[provinceid]['troops']}"




    if commandname == "annex" and len(commandparts) == 2:
        if not playercountry:
            return "pick country first"
        provinceid = getprovinceid(commandparts[1])
        if provinceid is None:
            return "province not found"
        provincemap[provinceid]["country"] = playercountry
        provincemap[provinceid]["countrycolor"] = countrytocolor.get(playercountry, fallbackcolor)
        return f"ok annexed {provinceid} to {playercountry}"
    

    if commandname == "exit" and len(commandparts) == 1:
        pygame.quit()
        exit(0)



    if commandname == "evaluate"  and len(commandparts) >= 2:
        code = " ".join(commandparts[1:])
        try:            # only allow access to a limited set of variables and functions for safety
            whitelist = {
                "provincemap": provincemap,
                "playercountry": playercountry,
                "countrytocolor": countrytocolor,
                "fallbackcolor": fallbackcolor,
            }
            result = eval(code, {"__builtins__": {}}, whitelist)
            return f"eval result: {result}"
        except Exception as e:
            return f"eval error: {e}"
        """ Example eval:
        provincemap.keys() = see all province id for debug
        provincemap['provinceid'] = read info about specific province
        playercountry = current country
        fallbackcolor = test color rendering
        """

    if commandname == "help" and len(commandparts) == 1:
        return "commands: add_troops [province] [amount], remove_troops [province] [amount], annex [province], help, exit"



    return "what??"


class developmentconsole:
    # in game console

    #init is the only time we can load the dev mode flag
    def __init__(self, enabled):
        self.enabled = enabled
        self.visible = False
        self.inputtext = ""
        self.loglines = ["dev console ready"]
        self.buttonrectangle = None
        self.panelrectangle = None
        self.closerectangle = None

    def drawbutton(self, screen, rectangle, textvalue, fontobject, enabled=True, pulse=False):
        if enabled:
            basecolor = (56, 116, 198) #blue
            if pulse:
                timer = pygame.time.get_ticks() * 0.008
                glowamount = 0.2 + 0.35 * (0.5 + 0.5 * math.sin(timer))
                basecolor = (
                    int(basecolor[0] + (255 - basecolor[0]) * glowamount),
                    int(basecolor[1] + (255 - basecolor[1]) * glowamount),
                    int(basecolor[2] + (255 - basecolor[2]) * glowamount),
                )
        else:
            basecolor = (70, 70, 70)#gray

        pygame.draw.rect(screen, basecolor, rectangle, border_radius=6)
        pygame.draw.rect(screen, (35, 35, 35), rectangle, width=1, border_radius=6) #dark border
        textcolor = (240, 240, 240) if enabled else (145, 145, 145) # light if enabled dark if not
        labelsurface = fontobject.render(textvalue, True, textcolor)
        screen.blit(labelsurface, labelsurface.get_rect(center=rectangle.center))


    # the gui render code 
    #TODO: move this to gui.py
    def draw(self, screen, fontobject, smallfontobject):
        if not self.enabled:
            self.buttonrectangle = None
            self.panelrectangle = None
            self.closerectangle = None
            return

        windowwidth, windowheight = screen.get_size()
        self.buttonrectangle = pygame.Rect(windowwidth - 132, 10, 122, 30)


        self.drawbutton(
            screen,
            self.buttonrectangle,
            "dev console",
            smallfontobject,
            enabled=True,
            pulse=self.visible,
        )




        if not self.visible:
            self.panelrectangle = None
            self.closerectangle = None
            return

        self.panelrectangle = pygame.Rect(
            int(windowwidth * 0.14),
            int(windowheight * 0.14),
            int(windowwidth * 0.72),
            int(windowheight * 0.72),
        )
        pygame.draw.rect(screen, (18, 18, 18), self.panelrectangle, border_radius=8)
        pygame.draw.rect(screen, (120, 120, 120), self.panelrectangle, width=1, border_radius=8)

        titletext = fontobject.render("dev console", True, (240, 240, 240))
        screen.blit(titletext, (self.panelrectangle.x + 12, self.panelrectangle.y + 10))

        self.closerectangle = pygame.Rect(self.panelrectangle.right - 76, self.panelrectangle.y + 8, 64, 24)
        self.drawbutton(screen, self.closerectangle, "close", smallfontobject, enabled=True)

        logviewrectangle = pygame.Rect(
            self.panelrectangle.x + 12,
            self.panelrectangle.y + 42,
            self.panelrectangle.width - 24,
            self.panelrectangle.height - 94,
        )
        pygame.draw.rect(screen, (10, 10, 10), logviewrectangle)
        pygame.draw.rect(screen, (70, 70, 70), logviewrectangle, width=1)

        maxrows = max(1, (logviewrectangle.height - 8) // 16)
        visiblelines = self.loglines[-maxrows:]
        for rowindex, linevalue in enumerate(visiblelines):
            linesurface = smallfontobject.render(linevalue, True, (180, 220, 180))
            screen.blit(linesurface, (logviewrectangle.x + 6, logviewrectangle.y + 4 + rowindex * 16))

        inputrectangle = pygame.Rect(
            self.panelrectangle.x + 12,
            self.panelrectangle.bottom - 42,
            self.panelrectangle.width - 24,
            30,
        )
        pygame.draw.rect(screen, (22, 22, 22), inputrectangle)
        pygame.draw.rect(screen, (110, 110, 110), inputrectangle, width=1)
        inputsurface = smallfontobject.render("> " + self.inputtext, True, (230, 230, 230))
        screen.blit(inputsurface, (inputrectangle.x + 6, inputrectangle.y + 8))

    def handleleftclick(self, mouseposition):
        if not self.enabled:
            return False

        if self.buttonrectangle and self.buttonrectangle.collidepoint(mouseposition):
            self.visible = not self.visible
            return True

        if self.visible:
            if self.closerectangle and self.closerectangle.collidepoint(mouseposition):
                self.visible = False
            return True

        return False

    def handlekeydown(self, keyboardevent, provincemap, playercountry, countrytocolor, fallbackcolor):
        if not self.visible:
            return False

        if keyboardevent.key == pygame.K_ESCAPE:
            self.visible = False
        elif keyboardevent.key == pygame.K_RETURN:
            commandline = self.inputtext.strip()
            if commandline:
                self.loglines.append("> " + commandline)
                outputline = rundevcommand(
                    commandline,
                    provincemap,
                    playercountry,
                    countrytocolor,
                    fallbackcolor,
                )
                self.loglines.append(outputline)
            self.inputtext = ""
        elif keyboardevent.key == pygame.K_BACKSPACE:
            self.inputtext = self.inputtext[:-1]
        else:


            # TODO: filter some characters that could mess up the font rendering
            if keyboardevent.unicode and keyboardevent.unicode.isprintable():
                self.inputtext += keyboardevent.unicode

        return True
