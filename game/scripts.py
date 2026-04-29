import pygame

from engine import EbeeEngine


class ScriptMenuController:
    def __init__(self, scriptfolder="scripts"):
        self.engine = EbeeEngine()
        self.manager = self.engine.initscripts(scriptfolder, autoload=False)
        self.backrect = pygame.Rect(0, 0, 1, 1)
        self.togglerects = {}
        self.scroll = 0

    def handle_event(self, event, mouseposition, screensize):
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return None

        if self.backrect.collidepoint(mouseposition):
            return "back"

        for scriptname, rect in self.togglerects.items():
            if rect.collidepoint(mouseposition):
                self.toggle_script(scriptname)
                return "handled"

        return None

    def draw(self, screen):
        width, height = screen.get_size()
        titlefont = pygame.font.SysFont("Arial", 34, bold=True)
        font = pygame.font.SysFont("Arial", 18)
        smallfont = pygame.font.SysFont("Arial", 14)

        overlay = pygame.Surface((width, height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 210))
        screen.blit(overlay, (0, 0))

        panel = pygame.Rect(width // 2 - 360, 70, 720, max(420, height - 140))
        pygame.draw.rect(screen, (18, 24, 34), panel, border_radius=5)
        pygame.draw.rect(screen, (120, 78, 36), panel, 2, border_radius=5)

        title = titlefont.render("SCRIPTS", True, (245, 245, 245))
        screen.blit(title, (panel.x + 24, panel.y + 22))

        self.backrect = pygame.Rect(panel.right - 118, panel.y + 22, 92, 36)
        self.draw_button(screen, self.backrect, "Back", font)

        scripts = self.manager.get_loaded_scripts()
        listtop = panel.y + 82
        rowheight = 52
        self.togglerects = {}

        if not scripts:
            empty = font.render("NO SCRIPTS!! found in /scripts.", True, (220, 220, 220))
            screen.blit(empty, (panel.x + 24, listtop + 24))
            return

        header = smallfont.render("LOADED from /scripts", True, (180, 188, 198))
        screen.blit(header, (panel.x + 24, listtop - 22))

        maxrows = max(1, (panel.bottom - listtop - 24) // rowheight)
        for index, script in enumerate(scripts[:maxrows]):
            y = listtop + index * rowheight
            rowrect = pygame.Rect(panel.x + 18, y, panel.width - 36, rowheight - 8)
            pygame.draw.rect(screen, (28, 35, 46), rowrect, border_radius=4)
            pygame.draw.rect(screen, (54, 65, 80), rowrect, 1, border_radius=4)

            enabled = bool(script.get("enabled"))
            name = str(script.get("name", "unknown"))
            status = "enabled" if enabled else "disabled"
            statuscolor = (120, 220, 140) if enabled else (230, 130, 120)

            namesurface = font.render(name, True, (240, 240, 240))
            statussurface = smallfont.render(status, True, statuscolor)
            screen.blit(namesurface, (rowrect.x + 14, rowrect.y + 8))
            screen.blit(statussurface, (rowrect.x + 14, rowrect.y + 30))

            buttonlabel = "Disable" if enabled else "Enable"
            togglerect = pygame.Rect(rowrect.right - 126, rowrect.y + 8, 104, 28)
            self.togglerects[name] = togglerect
            self.draw_button(screen, togglerect, buttonlabel, smallfont)

    def toggle_script(self, scriptname):
        if self.manager.is_enabled(scriptname):
            self.manager.disable_script(scriptname)
        else:
            self.manager.enable_script(scriptname)

    def draw_button(self, screen, rect, label, font):
        mouse = pygame.mouse.get_pos()
        hover = rect.collidepoint(mouse)
        fill = (64, 82, 104) if hover else (35, 47, 64)
        border = (220, 122, 48) if hover else (140, 78, 38)
        pygame.draw.rect(screen, fill, rect, border_radius=3)
        pygame.draw.rect(screen, border, rect, 1, border_radius=3)
        text = font.render(label, True, (245, 245, 245))
        screen.blit(text, text.get_rect(center=rect.center))
