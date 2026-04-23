import math
import pygame
clock = pygame.time.Clock()
#dev console will not be included in the final 



def loaddevmodeflag(filepath="dev.txt"):
    try:
        with open(filepath, "r", encoding="utf-8") as fileobject:
            return fileobject.read().strip().lower() == "true"
    except OSError:
        return False




def rundevcommand(
    commandline,
    provincemap,
    playercountry,
    countrytocolor,
    fallbackcolor,
    troopbadgelist,
    eventbus=None,
    currentturnnumber=0,
):
    commandparts = commandline.strip().split() # arguments
    if not commandparts:
        return "empty command"

    commandname = commandparts[0].lower()
    lowercaselookup = {provinceid.lower(): provinceid for provinceid in provincemap.keys()}


    def getprovinceid(rawtext):
        return lowercaselookup.get(rawtext.lower())

    def getowner(province):
        return province.get("ownercountry", province.get("country"))

    def getcontroller(province):
        return province.get("controllercountry", province.get("country"))

    validterrainset = {"plains", "forest", "hills", "mountains", "desert", "swamp", "urban"}

    knowncountrylookup = {}
    for province in provincemap.values():
        for key in ("ownercountry", "controllercountry", "country"):
            countryname = province.get(key)
            if not countryname:
                continue
            countrytext = str(countryname).strip()
            if not countrytext:
                continue
            lowercountry = countrytext.lower()
            if lowercountry not in knowncountrylookup:
                knowncountrylookup[lowercountry] = countrytext

    def resolvecountry(rawtext):
        if rawtext is None:
            return None
        countrytext = str(rawtext).strip()
        if not countrytext:
            return None
        return knowncountrylookup.get(countrytext.lower())




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
        provincemap[provinceid]["ownercountry"] = playercountry
        provincemap[provinceid]["controllercountry"] = playercountry
        provincemap[provinceid]["country"] = playercountry
        provincemap[provinceid]["countrycolor"] = countrytocolor.get(playercountry, fallbackcolor)
        return f"ok annexed {provinceid} to {playercountry}"


    if commandname == "set_troops" and len(commandparts) == 3:

        provinceid = getprovinceid(commandparts[1])

        if provinceid is None:
            return "province not found"
        try:
            amountvalue = max(0, int(commandparts[2]))
        except ValueError:
            return "not int"
        

        provincemap[provinceid]["troops"] = amountvalue


        return f"ok {provinceid} troops={provincemap[provinceid]['troops']}"


    if commandname == "set_terrain" and len(commandparts) == 3:
        provinceid = getprovinceid(commandparts[1])

        if provinceid is None:
            return "province not found"
        terrainvalue = commandparts[2].lower().strip()
        if terrainvalue not in validterrainset:
            return f"invalid terrain. use: {', '.join(sorted(validterrainset))}"
        
        
        provincemap[provinceid]["terrain"] = terrainvalue


        return f"ok {provinceid} terrain={terrainvalue}"


    if commandname == "set_owner" and len(commandparts) >= 3:

        provinceid = getprovinceid(commandparts[1])

        if provinceid is None:
            return "province not found"
        newowner = " ".join(commandparts[2:]).strip()
        if not newowner:
            return "owner required"
        

        provincemap[provinceid]["ownercountry"] = newowner


        return f"ok {provinceid} owner={newowner}"


    if commandname == "set_controller" and len(commandparts) >= 3:
        provinceid = getprovinceid(commandparts[1])


        if provinceid is None:
            return "province not found"
        newcontroller = " ".join(commandparts[2:]).strip()
        if not newcontroller:
            return "controller required"
        

        provincemap[provinceid]["controllercountry"] = newcontroller
        provincemap[provinceid]["country"] = newcontroller
        provincemap[provinceid]["countrycolor"] = countrytocolor.get(newcontroller, fallbackcolor)


        return f"ok {provinceid} controller={newcontroller}"


    if commandname == "province" and len(commandparts) == 2:
        provinceid = getprovinceid(commandparts[1])

        if provinceid is None:
            return "province not found"



        province = provincemap[provinceid]
        owner = getowner(province)
        controller = getcontroller(province)
        troops = province.get("troops", 0)
        terrain = province.get("terrain", "plains")



        return f"{provinceid} | owner={owner} controller={controller} troops={troops} terrain={terrain}"




    if commandname == "find" and len(commandparts) >= 2:

        keyword = " ".join(commandparts[1:]).strip().lower()

        if not keyword:
            return "keyword pls"
        matches = [provinceid for provinceid in provincemap.keys() if keyword in provinceid.lower()]
        if not matches:
            return "no matches"
        

        return f"matches({len(matches)}): {', '.join(matches[:12])}" + (" ..." if len(matches) > 12 else "")




    if commandname == "stats" and len(commandparts) == 1:
        totalprovincecount = len(provincemap)
        totaltroops = sum(max(0, int(province.get("troops", 0))) for province in provincemap.values())
        controllercountlookup = {}


        for province in provincemap.values():
            controller = getcontroller(province) or "None"
            controllercountlookup[controller] = controllercountlookup.get(controller, 0) + 1
        topcontrollers = sorted(controllercountlookup.items(),key=lambda item:item[1],reverse=True)[:6]
        topcontrollertext = ", ".join(f"{name}:{count}" for name, count in topcontrollers)



        return f"provinces={totalprovincecount} troops={totaltroops} controllers[{topcontrollertext}]"





    if commandname == "country_stats":
        rawtargetcountry = " ".join(commandparts[1:]).strip() if len(commandparts) >= 2 else ""

        if not rawtargetcountry:
            countrystatlist = []
            knowncountryset = set()
            for province in provincemap.values():
                owner = getowner(province)
                controller = getcontroller(province)
                if owner:
                    knowncountryset.add(owner)
                if controller:
                    knowncountryset.add(controller)

            for countryname in sorted(knowncountryset):
                owned = [p for p in provincemap.values() if getowner(p) == countryname]
                controlled = [p for p in provincemap.values() if getcontroller(p) == countryname]
                controlledtroops = sum(max(0, int(p.get("troops", 0))) for p in controlled)
                countrystatlist.append((countryname, len(owned), len(controlled), controlledtroops))

            if not countrystatlist:
                return "no countries"

            countrystatlist.sort(key=lambda entry: (-entry[3], entry[0]))
            maxrows = 8
            visibleentries = countrystatlist[:maxrows]
            summarytext = " ; ".join(
                f"{name} owned={owned} controlled={controlled} controlled_troops={troops}"
                for name, owned, controlled, troops in visibleentries
            )
            if len(countrystatlist) > maxrows:
                summarytext += " ; ..."
            return summarytext

        targetcountry = resolvecountry(rawtargetcountry)
        if targetcountry is None:
            return f"unknown country: {rawtargetcountry}"

        owned = [p for p in provincemap.values() if getowner(p) == targetcountry]
        controlled = [p for p in provincemap.values() if getcontroller(p) == targetcountry]
        controlledtroops = sum(max(0, int(p.get("troops", 0))) for p in controlled)

        return (
            f"{targetcountry} | owned={len(owned)} controlled={len(controlled)} controlled_troops={controlledtroops}"
        )


    if commandname == "news" and len(commandparts) >= 2:
        if eventbus is None:
            return "eventbus unavailable"

        
        rawtext = commandline.strip()[len(commandparts[0]):].strip()
        titletext = rawtext
        descriptiontext = "No description."
        if "|" in rawtext:
            left, right = rawtext.split("|", 1)
            titletext = left.strip() or "NEWS UPDATE"
            descriptiontext = right.strip() or "No description."

        eventbus.emit(
            "newspopup",
            {
                "title": titletext,
                "description": descriptiontext,
                "imagekey": "placeholder",
                "priority": 1,
            },
        )
        return f"ok queued news popup: {titletext}"

    if commandname == "collapse" and len(commandparts) >= 2:
        if eventbus is None:
            return "eventbus unavailable"
        countryname = commandparts[1]
        descriptiontext = " ".join(commandparts[2:]).strip()
        if not descriptiontext:
            descriptiontext = f"{countryname} has collapsed."
        eventbus.emit(
            "countrycollapsed",
            {
                "country": countryname,
                "description": descriptiontext,
            },
        )
        return f"queued collapse news for {countryname}"

    if commandname == "war" and len(commandparts) == 3:
        if eventbus is None:
            return "eventbus unavailable"

        if not commandparts[1].strip() or not commandparts[2].strip():
            return "usage: war [country1] [country2]"

        attackercountry = resolvecountry(commandparts[1])
        if attackercountry is None:
            return f"unknown country: {commandparts[1]}"

        defendercountry = resolvecountry(commandparts[2])
        if defendercountry is None:
            return f"unknown country: {commandparts[2]}"

        if attackercountry.lower() == defendercountry.lower():
            return "countries must differ"

        eventbus.emit(
            "wardeclared",
            {
                "attacker": attackercountry,
                "defender": defendercountry,
                "turn": int(currentturnnumber),
                "source": "devconsole",
            },
        )
        return f"ok war declared: {attackercountry} -> {defendercountry}"
    

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
                "troopbadgelist": troopbadgelist
            }
            result = eval(code, {"__builtins__": {}}, whitelist)
            return f"eval result: {result}"
        except Exception as e:
            return f"eval error: {e}"
        """ example:
        provincemap.keys() = see all province id for debug
        provincemap['provinceid'] = read info about specific province
        playercountry = current country
        fallbackcolor = test color rendering
        """

    if commandname == "help:debug" and len(commandparts) == 1:
        return (
            "debug: province [id], find [text], stats, country_stats [country], "
            "set_troops [id] [n], set_terrain [id] [terrain], set_owner [id] [country], set_controller [id] [country]"
        )

    if commandname == "help" and len(commandparts) == 1:
        return (
            "commands: add_troops [province] [amount], remove_troops [province] [amount], annex [province], "
            "province [id], find [text], stats, country_stats [country], news [title | description], "
            "collapse [country] [description], war [country1] [country2], help:debug, help, exit"
        )



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
            basecolor = (255, 20, 90) #blue
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

        pygame.draw.rect(screen, basecolor, rectangle, border_radius=1)
        pygame.draw.rect(screen, (35, 35, 35), rectangle, width=1, border_radius=1) #dark border
        textcolor = (240, 240, 240) if enabled else (145, 145, 145) # light if enabled dark if not
        labelsurface = fontobject.render(textvalue, True, textcolor)
        screen.blit(labelsurface, labelsurface.get_rect(center=rectangle.center))



    def wraptext(self, text, font, maxwidth):

        # fix clip
        words = text.split()
        lines = []
        current = []

        for word in words:
            test = " ".join(current + [word])
            if font.size(test)[0] <= maxwidth:
                current.append(word)
            else:
                lines.append(" ".join(current))
                current = [word]
        if current:
            lines.append(" ".join(current))

        return lines
    # the gui render code 
    #TODO: move this to gui.py

    def draw(self, screen, fontobject, smallfontobject,clock, text):
        if not self.enabled:
            self.buttonrectangle = None
            self.panelrectangle = None
            self.closerectangle = None
            return

        windowwidth, windowheight = screen.get_size()
        self.buttonrectangle = pygame.Rect(windowwidth - 132, 10, 122, 30)

        currentfps = clock.get_fps()
        self.drawbutton(
            screen,
            self.buttonrectangle,
            f"{text} {currentfps:.1f} FPS",
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
        #window
        pygame.draw.rect(screen, (18, 18, 18), self.panelrectangle, border_radius=1)
        pygame.draw.rect(screen, (120, 120, 120), self.panelrectangle, width=1, border_radius=1)

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


        lineheight = 16
        maxtextwidth = logviewrectangle.width - 12
        wrapped = []

        for linevalue in self.loglines:
            wrapped.extend(self.wraptext(linevalue, smallfontobject, maxtextwidth))

        maxrows = max(1, (logviewrectangle.height - 8) // lineheight)
        visiblelines = wrapped[-maxrows:]


        #render to console
        for rowindex, linevalue in enumerate(visiblelines):
            linesurface = smallfontobject.render(linevalue, True, (180, 220, 180))
            screen.blit(linesurface, (logviewrectangle.x + 6, logviewrectangle.y + 4 + rowindex * lineheight))


        # maxrows = max(1, (logviewrectangle.height - 8) // 16)
        # visiblelines = self.loglines[-maxrows:]


        # #TO render log line into cosole
        # for rowindex, linevalue in enumerate(visiblelines):
        #     linesurface = smallfontobject.render(linevalue, True, (180, 220, 180))
        #     screen.blit(linesurface, (logviewrectangle.x + 6, logviewrectangle.y + 4 + rowindex * 16))



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


    def handlekeydown(
        self,
        keyboardevent,
        provincemap,
        playercountry,
        countrytocolor,
        fallbackcolor,
        troopbadgelist,
        eventbus=None,
        currentturnnumber=0,
    ):
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
                    troopbadgelist,
                    eventbus=eventbus,
                    currentturnnumber=currentturnnumber,
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


