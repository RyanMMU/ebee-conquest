import pygame
import pygame_gui

#FOR ANY GUI PLEASE PUT IT IN HERE
# THIS SHOULD BE THE ONLY FILE WITH GUI CODE IN IT
# TO USE, CALL THE SYNC FUNCTION
# SYNC FUNCTION ARGUMENTS:
# gamephase: "choosecountry" or "play"
# pendingcountry: the country currently selected in the choosecountry phase, or None if no selection
# playercountry: the country currently controlled by the player, or None if not yet chosen
# currentturnnumber: the current turn number, starting at 1
# playergold: the current gold amount of the player
# playerpopulation: the current population amount of the player
# selectedprovinceid: the id of the currently selected province, or None if no selection
# provincemap: a dict mapping province ids to province data dicts
# recruitamount: the current recruit amount based on economy config and owned province count
# recruitenabled: whether the recruit button should be enabled based on player resources
# developmentmode: whether the game is in development mode (ignores recruit costs)
# recruitgoldcost: the current gold cost to recruit based on recruit amount and economy config
# recruitpopulationcost: the current population cost to recruit based on recruit amount and economy config
# countrymenutarget: the country currently targeted by the country interaction menu, or None if no menu
# countriesatwarset: a set of country names that the player country is currently at war with
# hovertext: the current hover text to display based on hovered province, or None if no hover
# mouseposition: the current mouse position in screen coordinates, used for hover text positioning
# troopbadgelist: a list of (centerposition, troopcount) tuples for rendering troop count badges on provinces


#def DEBUG():
#    pass




def gui_lightencolor(colorvalue, amount):


    #print("gui_lightencolor called", colorvalue, amount)


    amount = max(0.0, min(1.0, amount))
    red, green, blue = colorvalue
    return (
        int(red + (255 - red) * amount),
        int(green + (255 - green) * amount),
        int(blue + (255 - blue) * amount),
    )


class EngineUI:
    actionchoosecountry = "choosecountry"
    actionrecruit = "recruit"
    actionendturn = "endturn"
    actiondeclarewar = "declarewar"


    def __init__(self, window_size):
        #print("EngineUI init start", window_size)
        self.window_size = window_size
        self.manager = pygame_gui.UIManager(window_size)
        self.troopbadgelist = []
        self.troopbadgefont = pygame.font.SysFont("Arial", 12)
        self.hudfont = pygame.font.SysFont("Arial", 14)
        self.hudsmallfont = pygame.font.SysFont("Arial", 12)
        self.hoverfont = pygame.font.SysFont("Arial", 14)
        self.choosetitlefont = pygame.font.SysFont("Arial", 32, bold=True)
        self.choosetextfont = pygame.font.SysFont("Arial", 16)
        self.choosebuttonrect = pygame.Rect(0, 0, 190, 38)
        self.gamephase = "choosecountry"
        self.pendingcountry = None
        self.choosebuttonenabled = False
        self.hovertextcurrent = None
        self.hovermousepos = (0, 0)
        self.hudheadertext = ""
        self.huddetailtext = ""
        self.hudcontrolstext = ""

        #print("build elementstest")
        self.buildelements()
        #print("layout")
        self.applylayout()








    def buildelements(self):
        #print("function element")
        self.choose_title = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(0, 0, 420, 28),
            text="choose your country",
            manager=self.manager,
        )


        self.choose_help = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(0, 0, 620, 24),
            text="click on any province to select the country",
            manager=self.manager,
        )

        self.choose_selected = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(0, 0, 520, 24),
            text="selected: none",
            manager=self.manager,
        )
        self.choose_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(0, 0, 190, 38),
            text="choose country",
            manager=self.manager,
        )



        self.hud_panel = pygame_gui.elements.UIPanel(
            relative_rect=pygame.Rect(0, 0, 100, 74),
            manager=self.manager,
        )
        self.hud_header = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(10, 8, 1100, 20),
            text="",
            manager=self.manager,
            container=self.hud_panel,
            object_id="#hudheader",
        )
        self.hud_detail = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(10, 30, 1100, 20),
            text="",
            manager=self.manager,
            container=self.hud_panel,
            object_id="#huddetail",
        )
        self.hud_controls = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(10, 52, 1100, 20),
            text="",
            manager=self.manager,
            container=self.hud_panel,
            object_id="#hudcontrols",
        )
        self.hud_header.hide()
        self.hud_detail.hide()
        self.hud_controls.hide()





        self.recruit_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(0, 0, 170, 38),
            text="recruit",
            manager=self.manager,
        )
        self.end_turn_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(0, 0, 190, 38),
            text="end turn",
            manager=self.manager,
        )
        self.recruit_cost_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(0, 0, 330, 20),
            text="",
            manager=self.manager,
            object_id="#recruitcost",
        )


        self.country_panel = pygame_gui.elements.UIPanel(
            relative_rect=pygame.Rect(0, 0, 280, 154),
            manager=self.manager,
        )
        self.country_title = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(12, 10, 240, 22),
            text="Country actions",
            manager=self.manager,
            container=self.country_panel,
        )
        self.country_name = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(12, 34, 240, 22),
            text="",
            manager=self.manager,
            container=self.country_panel,
        )
        self.country_status = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(12, 58, 240, 22),
            text="",
            manager=self.manager,
            container=self.country_panel,
        )




        self.declare_war_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(12, 82, 256, 38),
            text="declare war",
            manager=self.manager,
            container=self.country_panel,
        )
        self.country_hint = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(12, 126, 240, 20),
            text="left click to confirm action",
            manager=self.manager,
            container=self.country_panel,
        )



        self.hideplayelements()
        self.hidechooseelements()
        self.country_panel.hide()


    #def applylayout(self):
        #print("applylayout running")
        #window_width, window_height = self.window_size
        #self.choose_title.set_relative_position((window_width // 2 - 210, 14))
        #self.choose_help.set_relative_position((window_width // 2 - 310, 46))
        #self.choose_selected.set_relative_position((20, window_height - 48))
        #self.choose_button.set_relative_position((window_width - 210, window_height - 56))
        #self.choosebuttonrect = pygame.Rect(window_width - 210, window_height - 56, 190, 38)
        #self.hud_panel.set_dimensions((window_width, 74))

    def applylayout(self):


        #print("applylayout running")
        window_width, window_height = self.window_size

        self.choose_title.set_relative_position((window_width // 2 - 210, 14))
        self.choose_help.set_relative_position((window_width // 2 - 310, 46))
        self.choose_selected.set_relative_position((20, window_height - 48))
        self.choose_button.set_relative_position((window_width - 210, window_height - 56))
        self.choosebuttonrect = pygame.Rect(window_width - 210, window_height - 56, 190, 38)


        self.hud_panel.set_dimensions((window_width, 74))
        self.hud_panel.set_relative_position((0, 0))


        self.recruit_button.set_relative_position((window_width - 390, window_height - 56))
        self.end_turn_button.set_relative_position((window_width - 210, window_height - 56))
        self.recruit_cost_label.set_relative_position((window_width - 390, window_height - 72))


        self.country_panel.set_relative_position((0, (window_height - 154) // 2))



    def showchooseelements(self):


        #print("showchooseelements")

        self.choose_title.show()
        self.choose_help.show()
        self.choose_selected.show()
        self.choose_button.show()

    def hidechooseelements(self):


        #print("hidechooseelements")

        self.choose_title.hide()
        self.choose_help.hide()
        self.choose_selected.hide()
        self.choose_button.hide()

    def showplayelements(self):
        #print("showplayelements")


        self.hud_panel.show()
        self.recruit_button.show()
        self.end_turn_button.show()

    def hideplayelements(self):

        #print("hideplayelements")


        self.hud_panel.hide()
        self.hud_header.hide()
        self.hud_detail.hide()
        self.hud_controls.hide()
        self.recruit_button.hide()
        self.end_turn_button.hide()
        self.recruit_cost_label.hide()

    def setwindowsize(self, window_size):

        #print("setwindowsize", window_size)
        self.window_size = window_size
        self.manager.set_window_resolution(window_size)
        self.applylayout()







    # FUNCITON TO UPDATE EVERY TIME SYNC IS CALLED, UPDATE UI WITH NEW DATA
    def sync(
        self,
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
    ):
        
        #print("sync", gamephase, pendingcountry)
        self.applylayout()
        self.gamephase = gamephase
        self.pendingcountry = pendingcountry
        self.choosebuttonenabled = pendingcountry is not None

        if gamephase == "choosecountry":
            #print("sync choosecountry phase")
            self.hideplayelements()
            self.country_panel.hide()
            self.hidechooseelements()
            


        else:
            #print("sync play phase")

            self.hidechooseelements()
            self.showplayelements()


            headertext = (
                f"{playercountry} | turn {currentturnnumber} | gold {playergold} | population {playerpopulation}"
            )
            self.hudheadertext = headertext



            if selectedprovinceid:
                #print("selected province", selectedprovinceid)
                selectedprovince = provincemap[selectedprovinceid]
                detailtext = (
                    f"province: {selectedprovinceid} | troops: {selectedprovince['troops']} | "
                    f"terrain: {selectedprovince['terrain']}"
                )



            else:
                #print("no selected province")
                detailtext = "select a province in your country"
            self.huddetailtext = detailtext



            self.hudcontrolstext = (
                "left click: open state/select province | right click foreign province: country actions"
            )



            self.recruit_button.set_text(f"recruit +{recruitamount}")


            if recruitenabled:

                #print("recruit enabled")
                self.recruit_button.enable()
            else:
                #print("recruit disabled")
                self.recruit_button.disable()



            if developmentmode:
                #print("dev mode on")
                self.recruit_cost_label.hide()

            else:
                #print("dev mode off show cost")
                self.recruit_cost_label.set_text(
                    f"cost: {recruitgoldcost}g, {recruitpopulationcost} pop"
                )
                self.recruit_cost_label.show()




            if countrymenutarget:

                #print("country menu target", countrymenutarget)
                self.country_panel.show()
                self.country_name.set_text(countrymenutarget)
                alreadyatwar = countrymenutarget in countriesatwarset
                self.country_status.set_text("status: at war" if alreadyatwar else "status: peace")
                self.declare_war_button.set_text("already at war" if alreadyatwar else "declare war")


                if alreadyatwar:
                    self.declare_war_button.disable()
                else:
                    self.declare_war_button.enable()
            else:
                #print("hide country menu")
                self.country_panel.hide()



        self.hovertextcurrent = hovertext
        self.hovermousepos = mouseposition

        self.troopbadgelist = list(troopbadgelist)  


    def process_event(self, event):

        #print("process_event", event)
        self.manager.process_events(event)



        if event.type == pygame.USEREVENT and event.user_type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.recruit_button:
                return self.actionrecruit
            if event.ui_element == self.end_turn_button:
                return self.actionendturn
            if event.ui_element == self.declare_war_button:
                return self.actiondeclarewar


        return None


    def update(self, elapsedseconds):

        #print("update", elapsedseconds)
        self.manager.update(elapsedseconds)



    # RENDER FUNCTION
    def draw(self, screen):
        #print("draw")


        # this is for choose country overlay
        if self.gamephase == "choosecountry":
            self.drawchooseoverlay(screen)


        # this is for main gameplay 
        self.manager.draw_ui(screen)
        if self.gamephase != "choosecountry":
            screen.blit(self.hudfont.render(self.hudheadertext, True, (242, 242, 242)), (10, 8))
            screen.blit(self.hudfont.render(self.huddetailtext, True, (236, 236, 236)), (10, 30))
            screen.blit(self.hudsmallfont.render(self.hudcontrolstext, True, (215, 215, 215)), (10, 52))
        for badgecenter, badgetroops in self.troopbadgelist:
            gui_drawtroopcountbadge(screen, badgecenter, badgetroops, self.troopbadgefont)
        if self.hovertextcurrent:
            hoverlabel = self.hoverfont.render("id:" + self.hovertextcurrent, True, (255, 255, 255))
            mousex, mousey = self.hovermousepos
            drawx = min(mousex + 16, max(0, self.window_size[0] - hoverlabel.get_width()))
            drawy = min(mousey + 16, max(0, self.window_size[1] - hoverlabel.get_height()))
            screen.blit(hoverlabel, (drawx, drawy))






    def drawchooseoverlay(self, screen):

        #print("drawchooseoverlay")
        window_width, window_height = self.window_size

        darksurface = pygame.Surface((window_width, window_height), pygame.SRCALPHA)
        darksurface.fill((0, 0, 0, 95))
        screen.blit(darksurface, (0, 0))

        titletext = self.choosetitlefont.render("choose your country", True, (250, 250, 250))
        screen.blit(titletext, titletext.get_rect(midtop=(window_width // 2, 16)))

        helptext = self.choosetextfont.render("click on any province to select the country", True, (225, 225, 225))
        screen.blit(helptext, helptext.get_rect(midtop=(window_width // 2, 60)))

        selectedtext = f"selected: {self.pendingcountry}" if self.pendingcountry else "selected: none"
        selectedlabel = self.choosetextfont.render(selectedtext, True, (240, 240, 240))
        screen.blit(selectedlabel, (20, window_height - 48))

        buttoncolor = (56, 116, 198) if self.choosebuttonenabled else (70, 70, 70)
        pygame.draw.rect(screen, buttoncolor, self.choosebuttonrect, border_radius=1)
        pygame.draw.rect(screen, (35, 35, 35), self.choosebuttonrect, width=1, border_radius=1)
        buttontext = self.choosetextfont.render("choose country", True, (240, 240, 240))
        screen.blit(buttontext, buttontext.get_rect(center=self.choosebuttonrect.center))





    def clickchoosebutton(self, mouseposition):
        #print("clickchoosebutton", mouseposition)
        if self.gamephase != "choosecountry":
            return False
        if not self.choosebuttonenabled:
            return False
        return self.choosebuttonrect.collidepoint(mouseposition)






    def ispointeroverui(self, mouseposition):
        #print("ispointeroverui", mouseposition)

        # choosecountry button is drawn manually, so check its rect directly
        if self.gamephase == "choosecountry":
            if self.choosebuttonrect.collidepoint(mouseposition):
                return True
            return False

        # in play phase, only block map clicks for actual clickable UI controls
        hittestelements = [
            self.recruit_button,
            self.end_turn_button,
            self.declare_war_button,
        ]

        for element in hittestelements:
            if not getattr(element, "visible", True):
                continue
            if element.get_abs_rect().collidepoint(mouseposition):
                return True

        # country menu panel should block map clicks while visible
        if getattr(self.country_panel, "visible", True) and self.country_panel.get_abs_rect().collidepoint(mouseposition):
            return True

        return False


#def helperAaa():
#    pass





















# for old_engien | IGNORE!
def gui_drawtroopcountbadge(screen, centerposition, troopcount, fontobject):
    labelsurface = fontobject.render(str(troopcount), True, (255, 255, 255))
    labelrectangle = labelsurface.get_rect()
    labelrectangle.inflate_ip(10, 6)
    labelrectangle.center = (int(centerposition[0]), int(centerposition[1]))
    pygame.draw.rect(screen, (0, 0, 0), labelrectangle, border_radius=1)
    pygame.draw.rect(screen, (165, 165, 165), labelrectangle, width=1, border_radius=1)
    screen.blit(labelsurface, labelsurface.get_rect(center=labelrectangle.center))


def gui_drawhoverlabel(screen, fontobject, hovertext, mouseposition):
    if not hovertext:
        return

    labelsurface = fontobject.render("id:" + hovertext, True, (255, 255, 255))
    screen.blit(labelsurface, (mouseposition[0] + 16, mouseposition[1] + 16))


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
    pygame.draw.rect(screen, (56, 116, 198), choosebuttonrectangle, border_radius=1)
    pygame.draw.rect(screen, (35, 35, 35), choosebuttonrectangle, width=1, border_radius=1)
    labelsurface = fontobject.render("choose country", True, (240, 240, 240))
    screen.blit(labelsurface, labelsurface.get_rect(center=choosebuttonrectangle.center))

    if selectedcountry:
        selectedlabel = fontobject.render(f"selected: {selectedcountry}", True, (240, 240, 240))
        screen.blit(selectedlabel, (20, windowheight - 48))

    return choosebuttonrectangle, selectedcountry is not None


def gui_drawcountryinteractionmenu(screen, fontobject, smallfontobject, targetcountry, alreadyatwar):
    placehldr, windowheight = screen.get_size()
    menuwidth = 280
    menuheight = 154
    menux = 0
    menuy = (windowheight - menuheight) // 2
    menurectangle = pygame.Rect(menux, menuy, menuwidth, menuheight)

    pygame.draw.rect(screen, (26, 26, 35), menurectangle, border_radius=1)
    pygame.draw.rect(screen, (92, 92, 116), menurectangle, width=2, border_radius=1)

    titlelabel = fontobject.render("Country actions", True, (240, 240, 240))
    screen.blit(titlelabel, (menurectangle.x + 12, menurectangle.y + 10))

    countrylabel = fontobject.render(targetcountry, True, (220, 220, 220))
    screen.blit(countrylabel, (menurectangle.x + 12, menurectangle.y + 34))

    statustext = "status: at war" if alreadyatwar else "status: peace"
    statuslabel = smallfontobject.render(statustext, True, (205, 205, 215))
    screen.blit(statuslabel, (menurectangle.x + 12, menurectangle.y + 58))

    declarebuttonrectangle = pygame.Rect(menurectangle.x + 12, menurectangle.y + 82, menurectangle.width - 24, 38)
    pygame.draw.rect(screen, (56, 116, 198), declarebuttonrectangle, border_radius=1)
    pygame.draw.rect(screen, (35, 35, 35), declarebuttonrectangle, width=1, border_radius=1)
    buttontext = "already at war" if alreadyatwar else "declare war"
    buttonlabel = fontobject.render(buttontext, True, (240, 240, 240))
    screen.blit(buttonlabel, buttonlabel.get_rect(center=declarebuttonrectangle.center))

    hintlabel = smallfontobject.render("left click to confirm action", True, (178, 178, 188))
    screen.blit(hintlabel, (menurectangle.x + 12, menurectangle.y + 126))

    return menurectangle, declarebuttonrectangle


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
    topsurface = pygame.Surface((windowwidth, 74), pygame.SRCALPHA)
    topsurface.fill((0, 0, 0, 120))
    screen.blit(topsurface, (0, 0))

    headertext = f"{playercountry} | turn {currentturnnumber} | gold {currentgold} | population {currentpopulation}"
    screen.blit(fontobject.render(headertext, True, (242, 242, 242)), (10, 8))

    if selectedprovinceid:
        selectedprovince = provincemap[selectedprovinceid]
        detailtext = (
            f"province: {selectedprovinceid} | troops: {selectedprovince['troops']} | "
            f"terrain: {selectedprovince['terrain']}"
        )
        screen.blit(fontobject.render(detailtext, True, (236, 236, 236)), (10, 30))
    else:
        screen.blit(fontobject.render("select a province in your country", True, (205, 205, 205)), (10, 30))

    controltext = "left click: open state/select province | right click foreign province: country actions"
    screen.blit(smallfontobject.render(controltext, True, (215, 215, 215)), (10, 52))

    recruitbuttonrectangle = pygame.Rect(windowwidth - 390, windowheight - 56, 170, 38)
    endturnbuttonrectangle = pygame.Rect(windowwidth - 210, windowheight - 56, 190, 38)
    pygame.draw.rect(screen, (56, 116, 198), recruitbuttonrectangle, border_radius=1)
    pygame.draw.rect(screen, (35, 35, 35), recruitbuttonrectangle, width=1, border_radius=1)
    pygame.draw.rect(screen, (56, 116, 198), endturnbuttonrectangle, border_radius=1)
    pygame.draw.rect(screen, (35, 35, 35), endturnbuttonrectangle, width=1, border_radius=1)

    recruitlabel = fontobject.render(f"recruit +{recruitamount}", True, (240, 240, 240))
    endturnlabel = fontobject.render("end turn", True, (240, 240, 240))
    screen.blit(recruitlabel, recruitlabel.get_rect(center=recruitbuttonrectangle.center))
    screen.blit(endturnlabel, endturnlabel.get_rect(center=endturnbuttonrectangle.center))

    if not developmentmode:
        costtext = smallfontobject.render(
            f"cost: {recruitgoldcost}g, {recruitpopulationcost} pop",
            True,
            (210, 210, 210),
        )
        screen.blit(costtext, (windowwidth - 390, windowheight - 72))

    return recruitbuttonrectangle, endturnbuttonrectangle
