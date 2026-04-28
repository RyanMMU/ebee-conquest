import os

import pygame


class FocusTreeView:
    def __init__(self):
        self.data = {"name": "Focus Tree", "focuses": []}
        self.isopen = False
        self.detailid = None
        self.noderects: dict[str, pygame.Rect] = {}
        self.closerect = pygame.Rect(0, 0, 1, 1)
        self.startrect = pygame.Rect(0, 0, 1, 1)
        self.detailrect = pygame.Rect(0, 0, 1, 1)
        self.iconcache = {}
        self.rootpath = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))

    def setdata(self, data):
        self.data = data or {"name": "Focus Tree", "focuses": []}
        if self.detailid and self.findfocus(self.detailid) is None:
            self.detailid = None

    def openview(self):
        self.isopen = True

    def closeview(self):
        self.isopen = False
        self.detailid = None

    def toggleview(self):
        if self.isopen:
            self.closeview()
        else:
            self.openview()

    def handleevent(self, event):
        if not self.isopen:
            return None

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.closeview()
            return None

        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return None

        position = event.pos
        if self.closerect.collidepoint(position):
            self.closeview()
            return None

        focus = self.findfocus(self.detailid)
        if focus and self.detailrect.collidepoint(position):
            if self.startrect.collidepoint(position) and focus.get("canstart"):
                return ("startfocus", self.detailid)
            return None

        for focusid, rect in self.noderects.items():
            if rect.collidepoint(position):
                self.detailid = focusid
                return None

        return None

    def pointerover(self, position):
        return self.isopen

    def draw(self, surface, titlefont, font, mouse):
        viewrect = surface.get_rect()
        pygame.draw.rect(surface, (13, 17, 23), viewrect)

        self.closerect = pygame.Rect(viewrect.right - 150, 18, 118, 34)
        title = str(self.data.get("name") or "Focus Tree")
        surface.blit(titlefont.render(title, True, (238, 220, 165)), (32, 22))
        self.drawbutton(surface, self.closerect, True, "Back", font)

        message = str(self.data.get("lastmessage") or "")
        if message:
            self.fittext(surface, message, font, (190, 205, 230), pygame.Rect(32, 55, viewrect.width - 220, 22))

        focuses = [focus for focus in self.data.get("focuses", ()) if isinstance(focus, dict)]
        if not focuses:
            note = font.render("No focus tree data for this country yet.", True, (205, 205, 205))
            surface.blit(note, note.get_rect(center=viewrect.center))
            self.noderects = {}
            return

        self.layoutnodes(viewrect, focuses)
        self.drawconnectors(surface, focuses)

        for focus in focuses:
            rect = self.noderects.get(focus.get("id"))
            if rect:
                self.drawnode(surface, focus, rect, font, mouse)

        focus = self.findfocus(self.detailid)
        if focus:
            self.drawdetails(surface, focus, titlefont, font)

    def layoutnodes(self, viewrect, focuses):
        nodew = 166
        nodeh = 92
        left = 70
        right = 70
        top = 122
        bottom = 70

        minx = min(int(focus.get("x", 0) or 0) for focus in focuses)
        maxx = max(int(focus.get("x", 0) or 0) for focus in focuses)
        miny = min(int(focus.get("y", 0) or 0) for focus in focuses)
        maxy = max(int(focus.get("y", 0) or 0) for focus in focuses)
        spanx = max(1, maxx - minx)
        spany = max(1, maxy - miny)
        stepx = max(120, (viewrect.width - left - right - nodew) // spanx)
        stepy = max(110, (viewrect.height - top - bottom - nodeh) // spany)

        self.noderects = {}
        for focus in focuses:
            focusid = focus.get("id")
            if not focusid:
                continue
            focusx = int(focus.get("x", 0) or 0)
            focusy = int(focus.get("y", 0) or 0)
            x = left + (focusx - minx) * stepx
            y = top + (focusy - miny) * stepy
            self.noderects[focusid] = pygame.Rect(x, y, nodew, nodeh)

    def drawconnectors(self, surface, focuses):
        for focus in focuses:
            target = self.noderects.get(focus.get("id"))
            if target is None:
                continue
            for prerequisite in focus.get("prerequisites", ()):
                source = self.noderects.get(prerequisite)
                if source is None:
                    continue
                start = source.midbottom
                end = target.midtop
                bend = (start[0], start[1] + (end[1] - start[1]) // 2)
                bendtwo = (end[0], bend[1])
                pygame.draw.lines(surface, (72, 80, 91), False, (start, bend, bendtwo, end), 3)
                pygame.draw.lines(surface, (112, 124, 140), False, (start, bend, bendtwo, end), 1)

    def drawnode(self, surface, focus, rect, font, mouse):
        status = str(focus.get("status", "locked"))
        fill, border = self.statuscolors(status)
        if rect.collidepoint(mouse):
            fill = tuple(min(255, value + 16) for value in fill)

        pygame.draw.rect(surface, fill, rect, border_radius=4)
        pygame.draw.rect(surface, border, rect, 2, border_radius=4)
        pygame.draw.rect(surface, border, pygame.Rect(rect.x, rect.y, rect.width, 6), border_radius=3)

        icon = self.loadicon(focus.get("icon"))
        iconrect = pygame.Rect(rect.centerx - 23, rect.y + 13, 46, 34)
        if icon:
            surface.blit(icon, icon.get_rect(center=iconrect.center))
        else:
            pygame.draw.rect(surface, (30, 34, 40), iconrect, border_radius=2)
            pygame.draw.rect(surface, (116, 126, 140), iconrect, 1, border_radius=2)

        titlerect = pygame.Rect(rect.x + 8, rect.y + 56, rect.width - 16, 28)
        self.fittext(surface, str(focus.get("title") or focus.get("id")), font, (244, 244, 244), titlerect)

    def drawdetails(self, surface, focus, titlefont, font):
        width = surface.get_width()
        height = surface.get_height()
        panelw = 410 if width >= 820 else max(320, width - 80)
        panelh = height - 130
        panelx = width - panelw - 34 if width >= 820 else 40
        self.detailrect = pygame.Rect(panelx, 82, panelw, panelh)

        pygame.draw.rect(surface, (20, 24, 31), self.detailrect, border_radius=4)
        pygame.draw.rect(surface, (96, 104, 116), self.detailrect, 2, border_radius=4)

        x = self.detailrect.x + 18
        y = self.detailrect.y + 16
        contentw = self.detailrect.width - 36
        titlelines = self.wraptext(str(focus.get("title") or focus.get("id")), titlefont, contentw)
        for line in titlelines[:2]:
            surface.blit(titlefont.render(line, True, (238, 220, 165)), (x, y))
            y += titlefont.get_height() + 2

        y += 8
        y = self.drawwrappedblock(surface, str(focus.get("description") or ""), font, (220, 220, 220), x, y, contentw, 5)
        y += 8

        status = str(focus.get("status", "locked"))
        progress = int(focus.get("progress", 0) or 0)
        turns = int(focus.get("turnsrequired", 1) or 1)
        y = self.drawfield(surface, "Status", status, font, x, y, contentw)
        y = self.drawfield(surface, "Turns", str(turns), font, x, y, contentw)
        y = self.drawfield(surface, "Progress", f"{progress}/{turns}", font, x, y, contentw)
        y = self.drawfield(surface, "Prerequisites", self.namelist(focus.get("prerequisites", ())), font, x, y, contentw)
        y = self.drawfield(surface, "Mutually exclusive", self.namelist(focus.get("mutuallyexclusive", ())), font, x, y, contentw)
        y = self.drawfield(surface, "Effects", self.effecttext(focus.get("effects", ())), font, x, y, contentw)

        reason = str(focus.get("blockingreason") or "")
        if reason:
            y += 4
            self.drawwrappedblock(surface, reason, font, (205, 150, 150), x, y, contentw, 3)

        self.startrect = pygame.Rect(x, self.detailrect.bottom - 52, contentw, 34)
        self.drawbutton(surface, self.startrect, bool(focus.get("canstart")), "Start Focus", font)

    def drawfield(self, surface, label, value, font, x, y, width):
        labeltext = font.render(f"{label}:", True, (185, 195, 210))
        surface.blit(labeltext, (x, y))
        y += labeltext.get_height() + 2
        y = self.drawwrappedblock(surface, value or "None", font, (235, 235, 235), x + 12, y, width - 12, 3)
        return y + 7

    def drawwrappedblock(self, surface, text, font, color, x, y, width, maxlines):
        for line in self.wraptext(str(text), font, width)[:maxlines]:
            surface.blit(font.render(line, True, color), (x, y))
            y += font.get_height() + 2
        return y

    def drawbutton(self, surface, rect, enabled, label, font):
        fill = (62, 126, 82) if enabled else (64, 64, 68)
        border = (154, 210, 165) if enabled else (118, 118, 122)
        textcolor = (245, 245, 245) if enabled else (170, 170, 174)
        pygame.draw.rect(surface, fill, rect, border_radius=3)
        pygame.draw.rect(surface, border, rect, 1, border_radius=3)
        text = font.render(label, True, textcolor)
        surface.blit(text, text.get_rect(center=rect.center))

    def fittext(self, surface, text, font, color, rect):
        original = str(text)
        fitted = original
        while fitted and font.size(fitted)[0] > rect.width:
            fitted = fitted[:-1]
        if not fitted:
            return
        if fitted != original:
            fitted = fitted[:-3] + "..." if len(fitted) > 3 else fitted
        rendered = font.render(fitted, True, color)
        surface.blit(rendered, rendered.get_rect(center=rect.center))

    def wraptext(self, text, font, width):
        words = str(text or "").split()
        if not words:
            return []

        lines = []
        line = ""
        for word in words:
            candidate = word if not line else f"{line} {word}"
            if font.size(candidate)[0] <= width:
                line = candidate
            else:
                if line:
                    lines.append(line)
                line = word
        if line:
            lines.append(line)
        return lines

    def loadicon(self, iconpath):
        iconpath = str(iconpath or "").strip()
        if not iconpath:
            return None

        filepath = iconpath
        if not os.path.isabs(filepath):
            filepath = os.path.join(self.rootpath, filepath)
        filepath = os.path.normpath(filepath)

        if filepath in self.iconcache:
            return self.iconcache[filepath]

        image = None
        try:
            loaded = pygame.image.load(filepath)
            try:
                loaded = loaded.convert_alpha()
            except pygame.error:
                pass
            image = pygame.transform.smoothscale(loaded, (46, 34))
        except (OSError, pygame.error):
            image = None

        self.iconcache[filepath] = image
        return image

    def findfocus(self, focusid):
        for focus in self.data.get("focuses", ()):
            if isinstance(focus, dict) and focus.get("id") == focusid:
                return focus
        return None

    def namelist(self, focusids):
        names = [self.focustitle(focusid) for focusid in focusids or ()]
        return ", ".join(names) if names else "None"

    def focustitle(self, focusid):
        focus = self.findfocus(focusid)
        if focus:
            return str(focus.get("title") or focusid)
        return str(focusid)

    def effecttext(self, effects):
        parts = []
        for effect in effects or ():
            if not isinstance(effect, dict):
                continue
            amount = int(effect.get("amount", 0) or 0)
            sign = "+" if amount >= 0 else ""
            effecttype = effect.get("type")
            if effecttype == "modify_gold":
                parts.append(f"Gold {sign}{amount}")
            elif effecttype == "modify_population_growth":
                parts.append(f"Population growth {sign}{amount}")
            else:
                parts.append(str(effecttype))
        return ", ".join(parts) if parts else "None"

    def statuscolors(self, status):
        colors = {
            "completed": ((42, 98, 67), (142, 222, 160)),
            "active": ((43, 82, 137), (140, 190, 255)),
            "available": ((101, 81, 39), (232, 190, 86)),
            "blocked": ((90, 46, 46), (220, 125, 125)),
            "locked": ((52, 54, 59), (122, 126, 136)),
            "waiting": ((50, 54, 62), (122, 132, 145)),
        }
        return colors.get(status, colors["locked"])
