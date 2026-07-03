from concurrent.futures import ThreadPoolExecutor
import textwrap

import pygame
from pydantic import ValidationError


STATUS_BAR_HEIGHT = 60
LEFTBAR_WIDTH = 230
RIGHTBAR_WIDTH = 260
BOTTOMBAR_HEIGHT = 70

_BG = (8, 14, 24)
_PANEL = (12, 20, 33)
_PANEL_HOVER = (25, 39, 60)
_BORDER = (58, 73, 93)
_GOLD = (212, 169, 77)
_GOLD_BRIGHT = (240, 198, 116)
_TEXT = (235, 239, 244)
_MUTED = (153, 164, 178)
_BLUE = (113, 174, 240)
_GREEN = (91, 201, 126)
_RED = (225, 100, 100)

_PRESET_DIALOGUE_CHOICES = (
    (
        "SEEK COMPROMISE",
        "We seek a fair peace that allows both nations to rebuild.",
    ),
    (
        "ASK FOR AN OFFER",
        "What do you propose as a counteroffer?",
    ),
    (
        "OFFER COOPERATION",
        "Cooperate with us and we will guarantee stability and reconstruction.",
    ),
    (
        "DEMAND COMPLIANCE",
        "You have no choice. Accept our terms.",
    ),
)


class PeaceTreatyScreen:
    """Blocking in-game peace-conference modal.

    It reuses the active display and returns a validated settlement dictionary;
    it never mutates campaign state itself.
    """

    def __init__(self, screen, negotiation, territory_options, volume=1.0):
        self.screen = screen
        self.negotiation = negotiation
        self.territory_options = list(territory_options or ())
        self.clock = pygame.time.Clock()
        self.title_font = pygame.font.SysFont("bahnschrift", 20, bold=True)
        self.small_font = pygame.font.SysFont("bahnschrift", 15)
        self.mini_font = pygame.font.SysFont("bahnschrift", 12)
        self.running = True
        self.result = None
        self.is_capitulation = bool(
            getattr(self.negotiation, "is_capitulation", True)
        )
        self.chat_open = False
        self.chat_input_text = ""
        self.chat_history = self.negotiation.chat_history
        if not self.chat_history:
            self.chat_history.append((
                self.negotiation.defeated,
                (
                    "Our armed resistance has ended. State the peace you intend to impose."
                    if self.is_capitulation
                    else "We are prepared to discuss terms for ending this war."
                ),
            ))
        self.selected_demands = {"CEASEFIRE"}
        self.selected_territories = set()
        self.proposal_history = []
        self.active_popup = None
        self.popup_message = ""
        self.pending_future = None
        self.pending_final = False
        self.pending_counter = None
        self.pending_counter_response = None
        self.pending_counter_message = ""
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="EbeePeace")
        self.backspace_held = False
        self.backspace_started = 0
        self.backspace_last = 0
        self.territory_scroll = 0
        self.demands = [
            "CEASEFIRE",
            "STATE TRANSFER",
            "PUPPET STATE",
            "MILITARY ACCESS",
            "REGIME CHANGE",
        ]
        self._layout()

    def _layout(self):
        width, height = self.screen.get_size()
        self.width = width
        self.height = height
        leftwidth = min(LEFTBAR_WIDTH, max(190, width // 6))
        rightwidth = min(RIGHTBAR_WIDTH, max(220, width // 5))
        self.leftbar = pygame.Rect(
            0, STATUS_BAR_HEIGHT, leftwidth, height - STATUS_BAR_HEIGHT - BOTTOMBAR_HEIGHT
        )
        self.rightbar = pygame.Rect(
            width - rightwidth,
            STATUS_BAR_HEIGHT,
            rightwidth,
            height - STATUS_BAR_HEIGHT - BOTTOMBAR_HEIGHT,
        )
        self.content = pygame.Rect(
            self.leftbar.right + 22,
            STATUS_BAR_HEIGHT + 22,
            self.rightbar.left - self.leftbar.right - 44,
            height - STATUS_BAR_HEIGHT - BOTTOMBAR_HEIGHT - 44,
        )
        self.exitbutton = pygame.Rect(18, height - 54, 180, 40)
        self.chatbutton = pygame.Rect(width // 2 - 210, height - 54, 200, 40)
        self.historybutton = pygame.Rect(width // 2 + 10, height - 54, 200, 40)
        self.submitbutton = pygame.Rect(width - 202, height - 54, 184, 40)
        self.chatpanel = self.content.inflate(-24, -24)
        self.chatinput = pygame.Rect(
            self.chatpanel.x + 16,
            self.chatpanel.bottom - 48,
            self.chatpanel.width - 32,
            36,
        )
        choicegap = 8
        choicewidth = max(100, (self.chatpanel.width - choicegap) // 2)
        choicestart = self.chatpanel.bottom - 78
        self.preset_dialogue_rects = [
            pygame.Rect(
                self.chatpanel.x + (index % 2) * (choicewidth + choicegap),
                choicestart + (index // 2) * 40,
                choicewidth,
                34,
            )
            for index in range(len(_PRESET_DIALOGUE_CHOICES))
        ]
        counterwidth = min(520, self.chatpanel.width - 24)
        self.counterpanel = pygame.Rect(0, 0, counterwidth, 190)
        self.counterpanel.center = self.chatpanel.center
        self.counteraccept = pygame.Rect(
            self.counterpanel.centerx - 126,
            self.counterpanel.bottom - 48,
            112,
            34,
        )
        self.counternegotiate = pygame.Rect(
            self.counterpanel.centerx + 14,
            self.counterpanel.bottom - 48,
            150,
            34,
        )
        popupwidth = min(520, width - 80)
        self.popup = pygame.Rect(0, 0, popupwidth, 230)
        self.popup.center = (width // 2, height // 2)
        self.popupconfirm = pygame.Rect(self.popup.centerx - 124, self.popup.bottom - 54, 108, 36)
        self.popupcancel = pygame.Rect(self.popup.centerx + 16, self.popup.bottom - 54, 108, 36)
        self.popupclose = pygame.Rect(self.popup.centerx - 60, self.popup.bottom - 54, 120, 36)
        self.countryrects = [
            pygame.Rect(self.leftbar.x + 14, self.leftbar.y + 58 + index * 64, self.leftbar.width - 28, 50)
            for index in range(2)
        ]
        self.demandrects = [
            pygame.Rect(self.rightbar.x + 14, self.rightbar.y + 58 + index * 58, self.rightbar.width - 28, 46)
            for index in range(len(self.demands))
        ]

    def _draw_panel(self, rect, selected=False, hovered=False, color=None):
        base = color or ((46, 42, 28) if selected else (_PANEL_HOVER if hovered else _PANEL))
        pygame.draw.rect(self.screen, base, rect, border_radius=6)
        pygame.draw.rect(
            self.screen,
            _GOLD if selected else (_MUTED if hovered else _BORDER),
            rect,
            2 if selected else 1,
            border_radius=6,
        )
        if selected:
            pygame.draw.rect(
                self.screen,
                _GOLD,
                pygame.Rect(rect.x, rect.y + 7, 3, rect.height - 14),
                border_radius=2,
            )

    def _draw_status(self):
        status = pygame.Rect(0, 0, self.width, STATUS_BAR_HEIGHT)
        pygame.draw.rect(self.screen, (7, 13, 22), status)
        pygame.draw.line(self.screen, _GOLD_BRIGHT, status.bottomleft, status.bottomright, 1)
        self.screen.blit(
            self.title_font.render("EBEE COMMAND", True, _GOLD_BRIGHT),
            (16, 19),
        )
        if self.is_capitulation:
            titletext = (
                f"PEACE CONFERENCE · {self.negotiation.defeated.upper()} CAPITULATED"
            )
        else:
            titletext = (
                f"PEACE NEGOTIATIONS · {self.negotiation.victor.upper()} / "
                f"{self.negotiation.defeated.upper()}"
            )
        title = self.title_font.render(titletext, True, _TEXT)
        self.screen.blit(title, title.get_rect(center=status.center))
        score = self.negotiation.posture_score(
            self.selected_demands, self.selected_territories
        )
        if self.negotiation.last_provider_error:
            posturetext = f"POSTURE {score:.0f}/100 · OFFLINE POLICY ACTIVE"
            posturecolor = _RED
        elif self._uses_preset_dialogue():
            posturetext = f"POSTURE {score:.0f}/100 · GRAPH POLICY ACTIVE"
            posturecolor = _GOLD_BRIGHT
        else:
            posturetext = f"AGREEMENT POSTURE {score:.0f}/100"
            posturecolor = _GOLD_BRIGHT
        posture = self.mini_font.render(posturetext, True, posturecolor)
        self.screen.blit(posture, posture.get_rect(midright=(self.width - 16, status.centery)))

    def _draw_sidebar(self):
        pygame.draw.rect(self.screen, (8, 15, 25), self.leftbar)
        pygame.draw.rect(self.screen, _BORDER, self.leftbar, 1)
        heading = self.small_font.render("PARTICIPANTS", True, _GOLD_BRIGHT)
        self.screen.blit(heading, heading.get_rect(centerx=self.leftbar.centerx, y=self.leftbar.y + 18))
        countries = [self.negotiation.victor, self.negotiation.defeated]
        roles = [
            (
                f"VICTOR · {self.negotiation.player_name.upper()}"[:28]
                if self.is_capitulation
                else f"PLAYER · {self.negotiation.player_name.upper()}"[:28]
            ),
            "CAPITULATED" if self.is_capitulation else "OPPOSING NATION",
        ]
        mouse = pygame.mouse.get_pos()
        for index, rect in enumerate(self.countryrects):
            self._draw_panel(rect, selected=index == 1, hovered=rect.collidepoint(mouse))
            country = self.small_font.render(countries[index].upper(), True, _TEXT)
            role = self.mini_font.render(roles[index], True, _GOLD if index == 1 else _MUTED)
            self.screen.blit(country, (rect.x + 14, rect.y + 8))
            self.screen.blit(role, (rect.x + 14, rect.y + 29))

        ratio = self.negotiation.victor_strength / self.negotiation.defeated_strength
        ratio_lines = [
            "BALANCE OF POWER",
            f"{self.negotiation.victor}: {ratio:.2f}×",
            f"{self.negotiation.defeated}: 1.00×",
            "",
            "NPC PERSONALITY",
            getattr(self.negotiation.personality, "name", "default").replace("_", " ").upper(),
        ]
        y = self.countryrects[-1].bottom + 30
        for line in ratio_lines:
            color = _GOLD_BRIGHT if line in {"BALANCE OF POWER", "NPC PERSONALITY"} else _MUTED
            surface = self.mini_font.render(line, True, color)
            self.screen.blit(surface, (self.leftbar.x + 16, y))
            y += 20

    def _draw_demands(self):
        pygame.draw.rect(self.screen, (8, 15, 25), self.rightbar)
        pygame.draw.rect(self.screen, _BORDER, self.rightbar, 1)
        heading = self.small_font.render("TREATY DEMANDS", True, _GOLD_BRIGHT)
        self.screen.blit(heading, heading.get_rect(centerx=self.rightbar.centerx, y=self.rightbar.y + 18))
        mouse = pygame.mouse.get_pos()
        for demand, rect in zip(self.demands, self.demandrects):
            selected = demand in self.selected_demands
            self._draw_panel(rect, selected=selected, hovered=rect.collidepoint(mouse))
            text = self.small_font.render(demand, True, _TEXT if selected else _MUTED)
            self.screen.blit(text, text.get_rect(center=rect.center))

        summaryy = self.demandrects[-1].bottom + 22
        territorycount = len(self.selected_territories)
        for line in (
            f"{len(self.selected_demands)} DEMANDS SELECTED",
            f"{territorycount} STATES CLAIMED",
            "Terms are not applied until",
            "the NPC accepts the proposal.",
        ):
            color = _GOLD_BRIGHT if "SELECTED" in line or "CLAIMED" in line else _MUTED
            surface = self.mini_font.render(line, True, color)
            self.screen.blit(surface, (self.rightbar.x + 16, summaryy))
            summaryy += 20

    def _state_rows(self):
        rowheight = 45
        top = self.content.y + 70
        visibleheight = self.content.bottom - top - 18
        visiblecount = max(1, visibleheight // rowheight)
        maxscroll = max(0, len(self.territory_options) - visiblecount)
        self.territory_scroll = max(0, min(maxscroll, self.territory_scroll))
        rows = []
        for displayindex in range(visiblecount):
            optionindex = self.territory_scroll + displayindex
            if optionindex >= len(self.territory_options):
                break
            rect = pygame.Rect(
                self.content.x + 18,
                top + displayindex * rowheight,
                self.content.width - 36,
                rowheight - 7,
            )
            rows.append((self.territory_options[optionindex], rect))
        return rows

    def _draw_territory(self):
        pygame.draw.rect(self.screen, (10, 18, 30), self.content, border_radius=8)
        pygame.draw.rect(self.screen, _BORDER, self.content, 1, border_radius=8)
        title = self.title_font.render("SELECT TERRITORY TO REQUEST", True, _GOLD_BRIGHT)
        self.screen.blit(title, (self.content.x + 18, self.content.y + 15))
        description = self.mini_font.render(
            "Each additional state lowers the chance of agreement. Only validated state IDs can be transferred.",
            True,
            _MUTED,
        )
        self.screen.blit(description, (self.content.x + 18, self.content.y + 43))
        mouse = pygame.mouse.get_pos()
        if not self.territory_options:
            empty = self.small_font.render("No territory is available for transfer.", True, _MUTED)
            self.screen.blit(empty, empty.get_rect(center=self.content.center))
            return
        for option, rect in self._state_rows():
            stateid = option["id"]
            selected = stateid in self.selected_territories
            self._draw_panel(rect, selected=selected, hovered=rect.collidepoint(mouse))
            checkbox = pygame.Rect(rect.x + 12, rect.centery - 8, 16, 16)
            pygame.draw.rect(self.screen, _GOLD if selected else _MUTED, checkbox, 2, border_radius=2)
            if selected:
                pygame.draw.circle(self.screen, _GOLD_BRIGHT, checkbox.center, 4)
            label = str(option.get("label") or stateid).replace("_", " ")
            text = self.small_font.render(label[:54], True, _TEXT)
            self.screen.blit(text, (rect.x + 40, rect.y + 10))

    def _wrapped_lines(self, message, width):
        charwidth = max(18, width // 8)
        return textwrap.wrap(str(message), width=charwidth) or [""]

    def _uses_preset_dialogue(self):
        providername = getattr(self.negotiation.ai_manager, "active_provider_name", None)
        return providername == "graph" or not self.negotiation.provider_available

    def _draw_chat(self):
        pygame.draw.rect(self.screen, (10, 18, 30), self.content, border_radius=8)
        pygame.draw.rect(self.screen, _GOLD, self.content, 1, border_radius=8)
        title = self.title_font.render(
            f"NEGOTIATE WITH {self.negotiation.defeated.upper()}",
            True,
            _GOLD_BRIGHT,
        )
        self.screen.blit(title, (self.chatpanel.x, self.chatpanel.y))
        y = self.chatpanel.y + 38
        messages = []
        for sender, message in self.chat_history[-7:]:
            lines = self._wrapped_lines(f"{sender}: {message}", self.chatpanel.width - 20)
            messages.append((sender, lines))
        inputtop = (
            self.preset_dialogue_rects[0].top - 28
            if self._uses_preset_dialogue()
            else self.chatinput.top
        )
        totalheight = sum(len(lines) * 19 + 7 for _sender, lines in messages)
        y = max(y, inputtop - 12 - totalheight)
        for sender, lines in messages:
            color = _BLUE if sender == "PLAYER" else (_GREEN if sender == "NOTICE" else _GOLD_BRIGHT)
            for line in lines:
                self.screen.blit(self.mini_font.render(line, True, color), (self.chatpanel.x, y))
                y += 19
            y += 7

        if self._uses_preset_dialogue():
            prompt = (
                "THE DELEGATION IS CONSIDERING YOUR CHOICE…"
                if self.pending_future is not None
                else "CHOOSE A DIALOGUE RESPONSE"
            )
            promptsurface = self.mini_font.render(prompt, True, _MUTED)
            self.screen.blit(
                promptsurface,
                (self.chatpanel.x, self.preset_dialogue_rects[0].y - 22),
            )
            mouse = pygame.mouse.get_pos()
            for (label, _message), rect in zip(
                _PRESET_DIALOGUE_CHOICES,
                self.preset_dialogue_rects,
            ):
                enabled = self.pending_future is None and self.pending_counter is None
                self._draw_panel(
                    rect,
                    hovered=enabled and rect.collidepoint(mouse),
                    color=None if enabled else (18, 26, 38),
                )
                color = _GOLD_BRIGHT if enabled else _MUTED
                labelsurface = self.mini_font.render(label, True, color)
                self.screen.blit(labelsurface, labelsurface.get_rect(center=rect.center))
        else:
            pygame.draw.rect(self.screen, (6, 12, 22), self.chatinput, border_radius=6)
            pygame.draw.rect(self.screen, _GOLD, self.chatinput, 1, border_radius=6)
            if self.pending_future is not None:
                inputtext = "The delegation is considering your words…"
                inputcolor = _MUTED
            else:
                cursor = "|" if pygame.time.get_ticks() % 900 < 450 else ""
                inputtext = (self.chat_input_text + cursor) or "Type a proposal and press Enter"
                inputcolor = _TEXT if self.chat_input_text else _MUTED
            surface = self.small_font.render(inputtext[-80:], True, inputcolor)
            self.screen.blit(
                surface,
                (self.chatinput.x + 10, self.chatinput.centery - surface.get_height() // 2),
            )

        self._draw_counteroffer()

    def _draw_counteroffer(self):
        if not self.pending_counter or not self.chat_open:
            return

        overlay = pygame.Surface(self.content.size, pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 125))
        self.screen.blit(overlay, self.content.topleft)
        pygame.draw.rect(self.screen, (14, 23, 37), self.counterpanel, border_radius=9)
        pygame.draw.rect(self.screen, _GOLD, self.counterpanel, 2, border_radius=9)
        title = self.small_font.render("COUNTEROFFER", True, _GOLD_BRIGHT)
        self.screen.blit(title, title.get_rect(centerx=self.counterpanel.centerx, y=self.counterpanel.y + 16))

        y = self.counterpanel.y + 50
        for line in self._wrapped_lines(
            self.pending_counter_message,
            self.counterpanel.width - 42,
        )[:4]:
            surface = self.mini_font.render(line, True, _TEXT)
            self.screen.blit(surface, surface.get_rect(centerx=self.counterpanel.centerx, y=y))
            y += 18

        mouse = pygame.mouse.get_pos()
        self._draw_panel(
            self.counteraccept,
            hovered=self.counteraccept.collidepoint(mouse),
            color=(24, 68, 40),
        )
        self._draw_panel(
            self.counternegotiate,
            hovered=self.counternegotiate.collidepoint(mouse),
            color=(48, 38, 28),
        )
        for rect, label in (
            (self.counteraccept, "AGREE"),
            (self.counternegotiate, "KEEP NEGOTIATING"),
        ):
            surface = self.mini_font.render(label, True, _TEXT)
            self.screen.blit(surface, surface.get_rect(center=rect.center))

    def _draw_bottom(self):
        bottom = pygame.Rect(0, self.height - BOTTOMBAR_HEIGHT, self.width, BOTTOMBAR_HEIGHT)
        pygame.draw.rect(self.screen, (5, 10, 17), bottom)
        pygame.draw.line(self.screen, _GOLD_BRIGHT, bottom.topleft, bottom.topright, 1)
        mouse = pygame.mouse.get_pos()
        fullyoccupied = self.negotiation.occupation_ratio >= 0.999
        exitlabel = "SUBMIT TERMS" if fullyoccupied else "LEAVE & CONTINUE WAR"
        exitcolor = _MUTED if fullyoccupied else _RED
        dialogue_label = (
            "DIALOGUE OPTIONS"
            if self._uses_preset_dialogue()
            else "CHAT WITH LEADER"
        )
        buttons = [
            (self.exitbutton, exitlabel, exitcolor),
            (self.chatbutton, "TERRITORY" if self.chat_open else dialogue_label, _GOLD),
            (self.historybutton, "PROPOSAL HISTORY", _GOLD),
            (self.submitbutton, "SUBMIT DEMANDS", _GREEN),
        ]
        for rect, label, color in buttons:
            selected = rect == self.chatbutton and self.chat_open
            self._draw_panel(
                rect,
                selected=selected,
                hovered=rect.collidepoint(mouse),
                color=(25, 48, 33) if color == _GREEN else None,
            )
            surface = self.small_font.render(label, True, color if not selected else _GOLD_BRIGHT)
            self.screen.blit(surface, surface.get_rect(center=rect.center))

    def _draw_popup(self):
        if not self.active_popup:
            return
        overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 175))
        self.screen.blit(overlay, (0, 0))
        pygame.draw.rect(self.screen, (14, 23, 37), self.popup, border_radius=10)
        pygame.draw.rect(self.screen, _GOLD, self.popup, 2, border_radius=10)
        titles = {
            "confirm": "CONFIRM FINAL PROPOSAL",
            "history": "PROPOSAL HISTORY",
            "result": "DELEGATION RESPONSE",
            "error": "INVALID PROPOSAL",
        }
        title = self.title_font.render(titles.get(self.active_popup, "PEACE CONFERENCE"), True, _GOLD_BRIGHT)
        self.screen.blit(title, title.get_rect(centerx=self.popup.centerx, y=self.popup.y + 24))
        y = self.popup.y + 70
        for line in self._wrapped_lines(self.popup_message, self.popup.width - 56)[:5]:
            surface = self.small_font.render(line, True, _TEXT)
            self.screen.blit(surface, surface.get_rect(centerx=self.popup.centerx, y=y))
            y += 22
        mouse = pygame.mouse.get_pos()
        if self.active_popup == "confirm":
            self._draw_panel(self.popupconfirm, hovered=self.popupconfirm.collidepoint(mouse), color=(24, 68, 40))
            self._draw_panel(self.popupcancel, hovered=self.popupcancel.collidepoint(mouse), color=(68, 28, 32))
            buttonlabels = ((self.popupconfirm, "SUBMIT"), (self.popupcancel, "CANCEL"))
            for rect, text in buttonlabels:
                surface = self.small_font.render(text, True, _TEXT)
                self.screen.blit(surface, surface.get_rect(center=rect.center))
        else:
            self._draw_panel(self.popupclose, hovered=self.popupclose.collidepoint(mouse))
            surface = self.small_font.render(
                "CONCLUDE" if self.result else "CLOSE",
                True,
                _GOLD_BRIGHT,
            )
            self.screen.blit(surface, surface.get_rect(center=self.popupclose.center))

    def draw(self):
        self.screen.fill(_BG)
        self._draw_status()
        self._draw_sidebar()
        self._draw_demands()
        if self.chat_open:
            self._draw_chat()
        else:
            self._draw_territory()
        self._draw_bottom()
        self._draw_popup()
        pygame.display.flip()

    def _start_ai_request(self, finalproposal=False):
        if self.pending_future is not None:
            return
        demands = set(self.selected_demands)
        territories = set(self.selected_territories)
        self.pending_final = bool(finalproposal)
        self.pending_future = self.executor.submit(
            self.negotiation.ask,
            demands,
            territories,
            finalproposal,
        )

    def _poll_ai(self):
        if self.pending_future is None or not self.pending_future.done():
            return
        future = self.pending_future
        finalproposal = self.pending_final
        self.pending_future = None
        self.pending_final = False
        try:
            response = future.result()
        except Exception as error:
            self.popup_message = f"Negotiation failed safely: {error}"
            self.active_popup = "error"
            return
        if response.decision.value == "COUNTER":
            self.proposal_history.append({
                "demands": sorted(self.selected_demands),
                "territories": sorted(self.selected_territories),
                "decision": response.decision.value,
                "message": response.message,
            })
            counterdemands = set(response.suggested_demands)
            counterterritories = set(response.suggested_territory_state_ids)
            statechanges = ", ".join(
                stateid.replace("_", " ") for stateid in sorted(counterterritories)
            ) or "none"
            demandchanges = ", ".join(sorted(counterdemands)) or "CEASEFIRE"
            notice = (
                "NPC SUGGESTED THE FOLLOWING: "
                f"Demands: {demandchanges}. State change: {statechanges}. AGREE?"
            )
            self.chat_history.append(("NOTICE", notice))
            self.pending_counter = {
                "demands": counterdemands,
                "territories": counterterritories,
            }
            self.pending_counter_response = response
            self.pending_counter_message = (
                f"Demands: {demandchanges}. State transfer: {statechanges}."
            )
            self.chat_open = True
            return
        if not finalproposal:
            return

        proposalrecord = {
            "demands": sorted(self.selected_demands),
            "territories": sorted(self.selected_territories),
            "decision": response.decision.value,
            "message": response.message,
        }
        self.proposal_history.append(proposalrecord)
        if response.decision.value == "ACCEPT":
            try:
                proposal = self.negotiation.validate_proposal(
                    self.selected_demands,
                    self.selected_territories,
                )
            except (ValidationError, ValueError) as error:
                self.popup_message = str(error)
                self.active_popup = "error"
                return
            self.result = {
                "accepted": True,
                "proposal": proposal.model_dump(mode="json"),
                "decision": response.model_dump(mode="json"),
            }
        self.popup_message = response.message
        self.active_popup = "result"

    def _accept_counteroffer(self):
        if not self.pending_counter or self.pending_counter_response is None:
            self.popup_message = "The counteroffer is no longer available."
            self.active_popup = "error"
            return
        try:
            proposal = self.negotiation.validate_proposal(
                self.pending_counter["demands"],
                self.pending_counter["territories"],
            )
        except (ValidationError, ValueError) as error:
            self.popup_message = str(error)
            self.active_popup = "error"
            return
        self.selected_demands = set(proposal.demands)
        self.selected_territories = set(proposal.territory_state_ids)
        self.result = {
            "accepted": True,
            "counteroffer": True,
            "proposal": proposal.model_dump(mode="json"),
            "decision": self.pending_counter_response.model_dump(mode="json"),
        }
        self.pending_counter = None
        self.pending_counter_response = None
        self.pending_counter_message = ""
        self.popup_message = "The NPC counteroffer was accepted. The treaty is ready to conclude."
        self.active_popup = "result"

    def _dismiss_counteroffer(self):
        if self.pending_counter:
            self.chat_history.append(("NOTICE", "COUNTEROFFER DECLINED. Negotiations continue."))
        self.pending_counter = None
        self.pending_counter_response = None
        self.pending_counter_message = ""

    def _submit_chat(self, preset_message=None):
        message = str(preset_message or self.chat_input_text).strip()
        if not message or self.pending_future is not None:
            return
        self.chat_input_text = ""
        self.negotiation.record_player_message(message)
        previousdemands = set(self.selected_demands)
        previousterritories = set(self.selected_territories)
        self.selected_demands, self.selected_territories = (
            self.negotiation.interpret_player_message(
                message,
                self.selected_demands,
                self.selected_territories,
            )
        )
        if (
            self.selected_demands != previousdemands
            or self.selected_territories != previousterritories
        ):
            territorylabels = [
                stateid.replace("_", " ")
                for stateid in sorted(self.selected_territories)
            ]
            visibleterritories = ", ".join(territorylabels[:6])
            if len(territorylabels) > 6:
                visibleterritories += f", +{len(territorylabels) - 6} more"
            notice = "FORMAL DEMANDS UPDATED: " + ", ".join(sorted(self.selected_demands))
            if visibleterritories:
                notice += f". Territory: {visibleterritories}"
            self.chat_history.append(("NOTICE", notice))
        self._start_ai_request(finalproposal=False)

    def _request_submit(self):
        try:
            self.negotiation.validate_proposal(
                self.selected_demands,
                self.selected_territories,
            )
        except (ValidationError, ValueError) as error:
            self.popup_message = str(error)
            self.active_popup = "error"
            return
        score = self.negotiation.posture_score(
            self.selected_demands,
            self.selected_territories,
        )
        self.popup_message = (
            f"Submit {len(self.selected_demands)} demand(s) and "
            f"{len(self.selected_territories)} territorial claim(s)? "
            f"Current agreement posture is {score:.0f}/100."
        )
        self.active_popup = "confirm"

    def _handle_click(self, position):
        if self.active_popup:
            if self.active_popup == "confirm":
                if self.popupconfirm.collidepoint(position):
                    self.active_popup = None
                    self._start_ai_request(finalproposal=True)
                elif self.popupcancel.collidepoint(position):
                    self.active_popup = None
            elif self.popupclose.collidepoint(position):
                if self.result:
                    self.running = False
                self.active_popup = None
            return
        if self.pending_counter and self.chat_open:
            if self.counteraccept.collidepoint(position):
                self._accept_counteroffer()
            elif self.counternegotiate.collidepoint(position):
                self._dismiss_counteroffer()
            return
        if self.exitbutton.collidepoint(position):
            if self.negotiation.occupation_ratio >= 0.999:
                self.popup_message = (
                    "Total occupation is complete. The NPC has no remaining leverage "
                    "and must accept a submitted proposal."
                )
                self.active_popup = "error"
                return
            self.result = {"accepted": False, "reason": "conference_deferred"}
            self.running = False
            return
        if self.chatbutton.collidepoint(position):
            self.chat_open = not self.chat_open
            return
        if self.historybutton.collidepoint(position):
            if self.proposal_history:
                latest = self.proposal_history[-1]
                self.popup_message = (
                    f"Latest: {latest['decision']} · "
                    f"{', '.join(latest['demands'])} · "
                    f"{len(latest['territories'])} states."
                )
            else:
                self.popup_message = "No proposals have been submitted."
            self.active_popup = "history"
            return
        if self.submitbutton.collidepoint(position):
            self._request_submit()
            return
        if self.chat_open and self._uses_preset_dialogue():
            for (_label, message), rect in zip(
                _PRESET_DIALOGUE_CHOICES,
                self.preset_dialogue_rects,
            ):
                if rect.collidepoint(position):
                    self._submit_chat(message)
                    return
        for demand, rect in zip(self.demands, self.demandrects):
            if not rect.collidepoint(position):
                continue
            if demand == "CEASEFIRE":
                return
            if demand in self.selected_demands:
                self.selected_demands.remove(demand)
                if demand == "STATE TRANSFER":
                    self.selected_territories.clear()
            else:
                self.selected_demands.add(demand)
            return
        if not self.chat_open and "STATE TRANSFER" in self.selected_demands:
            for option, rect in self._state_rows():
                if rect.collidepoint(position):
                    stateid = option["id"]
                    if stateid in self.selected_territories:
                        self.selected_territories.remove(stateid)
                    else:
                        self.selected_territories.add(stateid)
                    return

    def handle_event(self, event):
        if event.type == pygame.QUIT:
            self.result = {"accepted": False, "reason": "window_closed"}
            self.running = False
            return
        if event.type == pygame.VIDEORESIZE:
            self._layout()
            return
        if event.type == pygame.MOUSEWHEEL and not self.chat_open and not self.active_popup:
            self.territory_scroll -= event.y
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._handle_click(event.pos)
            return
        if event.type == pygame.KEYUP and event.key == pygame.K_BACKSPACE:
            self.backspace_held = False
            return
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_ESCAPE:
            if self.active_popup:
                self.active_popup = None
            elif self.pending_counter and self.chat_open:
                self._dismiss_counteroffer()
            elif self.chat_open:
                self.chat_open = False
            else:
                if self.negotiation.occupation_ratio >= 0.999:
                    self.popup_message = (
                        "Total occupation is complete. Submit your terms; the NPC must accept."
                    )
                    self.active_popup = "error"
                    return
                self.result = {"accepted": False, "reason": "conference_deferred"}
                self.running = False
            return
        if (
            not self.chat_open
            or self.active_popup
            or self.pending_future is not None
            or self._uses_preset_dialogue()
        ):
            return
        if event.key == pygame.K_RETURN:
            self._submit_chat()
        elif event.key == pygame.K_BACKSPACE:
            self.chat_input_text = self.chat_input_text[:-1]
            self.backspace_held = True
            self.backspace_started = pygame.time.get_ticks()
            self.backspace_last = self.backspace_started
        elif event.unicode and event.unicode.isprintable() and len(self.chat_input_text) < 500:
            self.chat_input_text += event.unicode

    def run(self):
        try:
            while self.running:
                for event in pygame.event.get():
                    self.handle_event(event)
                now = pygame.time.get_ticks()
                if (
                    self.backspace_held
                    and self.chat_open
                    and not self.active_popup
                    and not self._uses_preset_dialogue()
                    and now - self.backspace_started >= 380
                    and now - self.backspace_last >= 45
                ):
                    self.chat_input_text = self.chat_input_text[:-1]
                    self.backspace_last = now
                self._poll_ai()
                self.draw()
                self.clock.tick(60)
        finally:
            self.executor.shutdown(wait=False, cancel_futures=True)
        return self.result or {"accepted": False, "reason": "conference_closed"}
