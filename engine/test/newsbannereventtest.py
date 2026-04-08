import pygame
from dataclasses import dataclass
from collections import deque
from engine import EngineEventType


@dataclass
class NewsItem:
    title: str
    description: str
    imagekey: str = "placeholder"
    priority: int = 0


class NewsSystem:
    def __init__(self, eventbus):
        self.bus = eventbus
        self.queue = deque()
        self.current = None
        self.subs = []

    def start(self):
        self._sub(EngineEventType.WARDECLARED, self.onwardeclared)
        self._sub(EngineEventType.PROVINCECONTROLCHANGED, self.onprovincecontrolchanged)
        self._sub("countrycollapsed", self.oncountrycollapsed)  # custom event string
        self._pullnext()

    def stop(self):
        for eventname, cb in self.subs:
            self.bus.unsubscribe(eventname, cb)
        self.subs.clear()

    def _sub(self, eventname, cb):
        self.bus.subscribe(eventname, cb)
        self.subs.append((eventname, cb))

    def _push(self, item):
        self.queue.append(item)
        if self.current is None:
            self._pullnext()

    def _pullnext(self):
        self.current = self.queue.popleft() if self.queue else None

    def closecurrent(self):
        self._pullnext()

    def onwardeclared(self, p):
        self._push(
            NewsItem(
                title=f"{p['attacker'].upper()} DECLARED WAR!",
                description=f"{p['attacker']} has declared war on {p['defender']} (turn {p['turn']}).",
                imagekey="war",
                priority=5,
            )
        )

    def onprovincecontrolchanged(self, p):
        self._push(
            NewsItem(
                title="PROVINCE CAPTURED",
                description=f"{p['provinceId']} changed control from {p['previousController']} to {p['newController']}.",
                imagekey="capture",
                priority=2,
            )
        )

    def oncountrycollapsed(self, p):
        self._push(
            NewsItem(
                title=f"{p['country'].upper()} COLLAPSED!",
                description=p.get("description", "Government authority has collapsed."),
                imagekey="collapse",
                priority=10,
            )
        )


class NewsPopup:
    def __init__(self):
        self.closerect = pygame.Rect(0, 0, 0, 0)

    def draw(self, screen, fonts, item):
        if item is None:
            return
        titlefont, bodyfont = fonts
        w, h = screen.get_size()

        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        screen.blit(overlay, (0, 0))

        panel = pygame.Rect(w // 2 - 260, h // 2 - 180, 520, 360)
        pygame.draw.rect(screen, (24, 24, 30), panel, border_radius=10)
        pygame.draw.rect(screen, (90, 90, 110), panel, width=2, border_radius=10)

        title = titlefont.render(item.title, True, (240, 240, 240))
        screen.blit(title, (panel.x + 16, panel.y + 14))

        imgrect = pygame.Rect(panel.x + 16, panel.y + 58, panel.width - 32, 140)
        pygame.draw.rect(screen, (50, 50, 62), imgrect, border_radius=6)
        pygame.draw.rect(screen, (100, 100, 120), imgrect, width=1, border_radius=6)
        label = bodyfont.render("placeholder image", True, (180, 180, 190))
        screen.blit(label, label.get_rect(center=imgrect.center))

        y = imgrect.bottom + 12
        for line in wraptext(item.description, bodyfont, panel.width - 32):
            surf = bodyfont.render(line, True, (220, 220, 220))
            screen.blit(surf, (panel.x + 16, y))
            y += 20

        self.closerect = pygame.Rect(panel.right - 116, panel.bottom - 46, 100, 30)
        pygame.draw.rect(screen, (56, 116, 198), self.closerect, border_radius=6)
        pygame.draw.rect(screen, (30, 30, 30), self.closerect, width=1, border_radius=6)
        txt = bodyfont.render("close", True, (240, 240, 240))
        screen.blit(txt, txt.get_rect(center=self.closerect.center))

    def handleclick(self, pos):
        return self.closerect.collidepoint(pos)


def wraptext(text, font, maxwidth):
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
