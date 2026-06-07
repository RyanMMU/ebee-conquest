import ctypes
import math
import os
from datetime import date, timedelta

import pygame

from engine.gui import gui_drawtroopcountbadge, gui_mergetroopbadgeentries
from game.animation.motion import (
    AmbientParticleField,
    PulseLayer,
    draw_animated_icon,
    draw_light_sweep,
    draw_scanlines,
    draw_soft_glow,
    ease_out_cubic,
    exp_lerp,
    mix_color,
    pulse,
    scale_rect,
)
from .focusui import FocusTreeView
from .researchui import ResearchTreeView

ctypes.windll.user32.SetProcessDPIAware()

_C_BG0 = (11, 18, 32)
_C_BG1 = (17, 24, 39)
_C_PANEL = (23, 32, 51)
_C_PANEL_DARK = (12, 18, 29)
_C_PANEL_HOVER = (28, 39, 59)
_C_GOLD = (212, 169, 77)
_C_GOLD_BRIGHT = (240, 198, 116)
_C_STEEL = (132, 145, 160)
_C_TEXT = (229, 231, 235)
_C_TEXT_MUTED = (156, 163, 175)
_C_SUCCESS = (67, 181, 129)
_C_DANGER = (224, 93, 93)
_C_INFO = (74, 143, 231)
_C_POLICY_BROWN = (44, 27, 18)
_C_POLICY_BROWN_DARK = (25, 15, 10)
_C_POLICY_BROWN_LIGHT = (72, 43, 24)


class Panel:
    def __init__(self, rect: pygame.Rect, color=(40, 40, 40)):
        self.rect = rect
        self.color = color

    def draw(self, surface: pygame.Surface):
        pygame.draw.rect(surface, self.color, self.rect)
        pygame.draw.rect(surface, (45, 56, 70), self.rect, 1)


class LeftBar:
    def __init__(self, rect: pygame.Rect):
        self.rect = rect
        self.items: list[str] = []
        self.item_rects: dict[str, pygame.Rect] = {}
        self._hover_glow = {}
        # rolling FPS history for status graph (42 samples)
        self._fps_history: list[float] = [0.0] * 42

    def set_items(self, items: list[str]):
        self.items = list(items)
        self._hover_glow = {}

    @staticmethod
    def _fit_text(font, text, max_width):
        text = str(text)
        if font.size(text)[0] <= max_width:
            return text
        suffix = "..."
        available_width = max(0, max_width - font.size(suffix)[0])
        fitted = ""
        for character in text:
            candidate = fitted + character
            if font.size(candidate)[0] > available_width:
                break
            fitted = candidate
        return fitted.rstrip() + suffix if fitted else suffix

    def draw(
        self,
        surface: pygame.Surface,
        font: pygame.font.Font,
        mouse_pos,
        font_bold=None,
        icons=None,
        selected=None,
        disabled_items=None,
        statusdata=None,
        notification_count=0,
    ):
        motion_time = pygame.time.get_ticks() / 1000.0
        icons = icons or {}
        disabled_items = {str(item).upper() for item in (disabled_items or set())}
        statusdata = statusdata or {}
        notification_count = max(0, int(notification_count or 0))
        pygame.draw.rect(surface, _C_PANEL_DARK, self.rect)
        pygame.draw.rect(surface, (28, 38, 52), self.rect, 1)
        pygame.draw.line(surface, (76, 64, 38), self.rect.topright, self.rect.bottomright, 1)
        draw_scanlines(surface, self.rect, motion_time, color=(74, 143, 231), alpha=8, spacing=34)

        self.item_rects = {}
        radius = 6
        item_index = 0
        item_step = 58
        item_height = 48
        for item in self.items:
            item_text = str(item).strip()
            if not item_text:
                divider_y = self.rect.y + 22 + item_index * item_step
                pygame.draw.line(
                    surface,
                    (76, 64, 38),
                    (self.rect.x + 14, divider_y),
                    (self.rect.right - 14, divider_y),
                    1,
                )
                continue

            x = self.rect.x + 14
            y = self.rect.y + 16 + item_index * item_step
            w = self.rect.width - 28
            h = item_height
            rect = pygame.Rect(x, y, w, h)
            item_key = item_text.upper()
            self.item_rects[item_key] = rect
            item_index += 1

            hovered = rect.collidepoint(mouse_pos)
            disabled = item_key in disabled_items
            if disabled:
                hovered = False
            glow = self._hover_glow.get(item_key, 0.0)
            if hovered:
                glow = min(1.0, glow + 0.16)
            else:
                glow = max(0.0, glow - 0.10)
            self._hover_glow[item_key] = glow

            is_selected = item_key == selected and not disabled
            if disabled:
                color = (29, 34, 42)
            elif "CLEAR ALL" in item_text:
                color = (35, 45, 47) if hovered else (20, 30, 36)
            elif is_selected:
                color = (37, 35, 28) if not hovered else (50, 44, 30)
            else:
                color = _C_PANEL_HOVER if hovered else (14, 22, 33)

            shadow = pygame.Surface((w + 8, h + 8), pygame.SRCALPHA)
            pygame.draw.rect(shadow, (0, 0, 0, 75), shadow.get_rect(), border_radius=radius + 2)
            surface.blit(shadow, (x - 3, y - 1))
            pygame.draw.rect(surface, color, rect, border_radius=radius)
            if disabled:
                bordercolor = (55, 60, 68)
            elif "CLEAR ALL" in item_text:
                bordercolor = (89, 110, 105) if hovered else (45, 61, 66)
            elif is_selected:
                bordercolor = _C_GOLD
            elif hovered:
                bordercolor = (88, 101, 118)
            else:
                bordercolor = (42, 55, 72)
            pygame.draw.rect(surface, bordercolor, rect, 1, border_radius=radius)

            if glow > 0.01:
                glowcolor = _C_GOLD if (is_selected or "CLEAR ALL" in item_text) else (92, 116, 144)
                glow_surf = pygame.Surface((w + 20, h + 20), pygame.SRCALPHA)
                for ring in range(4):
                    alpha = int(glow * (36 - ring * 7))
                    if alpha <= 0:
                        continue
                    offset = ring * 2 + 2
                    pygame.draw.rect(
                        glow_surf,
                        (*glowcolor, alpha),
                        (10 - offset, 10 - offset, w + offset * 2, h + offset * 2),
                        border_radius=radius + offset,
                        width=2,
                    )
                surface.blit(glow_surf, (x - 10, y - 10))
                draw_light_sweep(surface, rect, motion_time + item_index * 0.21, glowcolor, alpha=int(10 + glow * 26))

            if is_selected:
                pygame.draw.rect(surface, _C_GOLD, pygame.Rect(rect.x, rect.y + 8, 3, rect.height - 16), border_radius=2)

            icon = icons.get(item_key)
            icon_x = x + 18
            text_x = x + 54 + int(glow * 4)
            if icon is not None:
                draw_animated_icon(
                    surface,
                    icon,
                    (icon_x + icon.get_width() // 2, y + h // 2),
                    motion_time,
                    hover=0.65 if (hovered or is_selected) else 0.0,
                    accent=(92, 98, 108) if disabled else (_C_GOLD if is_selected else (92, 116, 144)),
                    phase=item_index * 0.7,
                )
            else:
                text_x = x + 18

            badge_text = None
            badge_rect = None
            badge_reserved_width = 0
            if item_key == "NOTIFICATIONS" and notification_count > 0:
                badge_label = "99+" if notification_count > 99 else str(notification_count)
                badge_text = font_bold.render(badge_label, True, (11, 18, 32)) if font_bold else font.render(badge_label, True, (11, 18, 32))
                badge_rect = pygame.Rect(0, 0, max(20, badge_text.get_width() + 8), 20)
                badge_rect.center = (rect.right - 20, rect.centery)
                badge_reserved_width = badge_rect.width + 12

            text_color = (224, 228, 231) if hovered else (202, 207, 211)
            if disabled:
                text_color = (112, 119, 130)
            if "CLEAR ALL" in item_text:
                text_color = (224, 228, 216)
            if is_selected:
                text_color = (239, 224, 185)
            active_font = font_bold if (is_selected and font_bold) else font
            fitted_text = self._fit_text(active_font, item_text, rect.right - text_x - 12 - badge_reserved_width)
            text = active_font.render(fitted_text, True, text_color)
            surface.blit(text, (text_x, y + (h - text.get_height()) // 2))

            if badge_text is not None and badge_rect is not None:
                badge_scale = 1.0 + 0.06 * pulse(motion_time, 4.6)
                badge_draw_rect = scale_rect(badge_rect, badge_scale)
                draw_soft_glow(surface, badge_draw_rect, _C_GOLD_BRIGHT, 0.55 + 0.25 * pulse(motion_time, 5.2), radius=5, rings=3)
                pygame.draw.rect(surface, _C_GOLD_BRIGHT, badge_draw_rect, border_radius=4)
                surface.blit(badge_text, badge_text.get_rect(center=badge_draw_rect.center))

        status_rect = pygame.Rect(self.rect.x + 14, self.rect.bottom - 202, self.rect.width - 28, 184)
        if status_rect.height > 0 and status_rect.top > self.rect.y + 430:
            shadow = pygame.Surface((status_rect.width + 8, status_rect.height + 8), pygame.SRCALPHA)
            pygame.draw.rect(shadow, (0, 0, 0, 90), shadow.get_rect(), border_radius=6)
            surface.blit(shadow, (status_rect.x - 3, status_rect.y - 2))
            pygame.draw.rect(surface, (9, 15, 24), status_rect, border_radius=6)
            pygame.draw.rect(surface, (42, 55, 72), status_rect, 1, border_radius=6)
            title = font.render("SYSTEM STATUS", True, _C_TEXT_MUTED)
            surface.blit(title, (status_rect.x + 14, status_rect.y + 14))
            graph_rect = pygame.Rect(status_rect.x + 14, status_rect.y + 46, status_rect.width - 28, 76)
            pygame.draw.rect(surface, (7, 12, 20), graph_rect, border_radius=4)
            for offset in range(1, 4):
                gy = graph_rect.y + offset * graph_rect.height // 4
                pygame.draw.line(surface, (26, 37, 51), (graph_rect.x, gy), (graph_rect.right, gy), 1)
            # update fps history from statusdata then draw graph from samples
            try:
                fps_sample = float(statusdata.get("fps", 0.0) or 0.0)
            except Exception:
                fps_sample = 0.0
            self._fps_history.append(fps_sample)
            if len(self._fps_history) > 42:
                self._fps_history = self._fps_history[-42:]

            samples = list(self._fps_history or [])
            if not samples:
                samples = [0.0] * 42
            # autoscale: at least 60 FPS range so small variations are visible
            max_scale = max(60.0, max(samples) if samples else 60.0)
            points = []
            sample_count = max(2, len(samples))
            for idx, sample in enumerate(samples):
                px = graph_rect.x + int(idx * graph_rect.width / (sample_count - 1))
                normalized = min(1.0, max(0.0, float(sample) / max_scale))
                # map normalized (0..1) so 0 is bottom, 1 is top of graph rect
                py = graph_rect.bottom - int(normalized * graph_rect.height)
                points.append((px, py))
            if len(points) >= 2:
                pygame.draw.lines(surface, _C_SUCCESS, False, points, 2)
            fps_value = float(statusdata.get("fps", 0.0) or 0.0)
            latency_value = float(statusdata.get("latency_ms", 0.0) or 0.0)
            fps_text = font.render(f"FPS {fps_value:4.1f}", True, _C_TEXT)
            latency_text = font.render(f"Frame {latency_value:4.1f} ms", True, _C_TEXT_MUTED)
            surface.blit(fps_text, (status_rect.x + 14, status_rect.bottom - 48))
            surface.blit(latency_text, (status_rect.x + 14, status_rect.bottom - 25))


class BottomButtons:
    def __init__(self, rect: pygame.Rect):
        self.rect = rect
        self.items: list[str] = []
        self.item_rects: dict[str, pygame.Rect] = {}
        self.selected: str | None = None
        self._hover_glow = {}

    def set_items(self, items: list[str]):
        self.items = list(items)
        if self.selected not in self.items:
            self.selected = (self.items[-1] if self.items else None)
        self._hover_glow = {}

    def set_selected(self, item: str | None):
        if item is None or item in self.items:
            self.selected = item

    def draw(self, surface: pygame.Surface, font: pygame.font.Font, mouse_pos, font_bold=None, icons=None):
        motion_time = pygame.time.get_ticks() / 1000.0
        icons = icons or {}
        w = 142
        h = 64
        spacing = 8
        radius = 6
        total_width = len(self.items) * w + (len(self.items) - 1) * spacing if self.items else 0
        available_width = max(0, self.rect.width)
        start_x = self.rect.x + max(0, (available_width - total_width) // 2)
        dock_rect = pygame.Rect(start_x - 14, self.rect.y + 9, total_width + 28, h + 18)

        dock_shadow = pygame.Surface((dock_rect.width + 14, dock_rect.height + 14), pygame.SRCALPHA)
        pygame.draw.rect(dock_shadow, (0, 0, 0, 88), dock_shadow.get_rect(), border_radius=10)
        surface.blit(dock_shadow, (dock_rect.x - 7, dock_rect.y - 3))
        dock_surface = pygame.Surface(dock_rect.size, pygame.SRCALPHA)
        pygame.draw.rect(dock_surface, (10, 15, 23, 176), dock_surface.get_rect(), border_radius=8)
        pygame.draw.rect(dock_surface, (44, 58, 76, 150), dock_surface.get_rect(), 1, border_radius=8)
        surface.blit(dock_surface, dock_rect.topleft)
        draw_light_sweep(surface, dock_rect, motion_time, _C_GOLD_BRIGHT, alpha=16)

        self.item_rects = {}
        for i, item in enumerate(self.items):
            x = start_x + (i * (w + spacing))
            y = self.rect.y + 18
            rect = pygame.Rect(x, y, w, h)
            self.item_rects[item] = rect

            hovered = rect.collidepoint(mouse_pos)
            glow = self._hover_glow.get(item, 0.0)
            if hovered:
                glow = min(1.0, glow + 0.12)
            else:
                glow = max(0.0, glow - 0.08)
            self._hover_glow[item] = glow

            if item == self.selected:
                color = (36, 34, 27) if not hovered else (48, 42, 30)
            else:
                color = (26, 36, 52) if hovered else (15, 23, 35)

            card_shadow = pygame.Surface((w + 8, h + 8), pygame.SRCALPHA)
            pygame.draw.rect(card_shadow, (0, 0, 0, 80), card_shadow.get_rect(), border_radius=radius + 2)
            surface.blit(card_shadow, (x - 3, y - 1))
            pygame.draw.rect(surface, color, rect, border_radius=radius)
            bordercolor = (177, 145, 70) if item == self.selected else ((82, 91, 101) if hovered else (58, 63, 70))
            pygame.draw.rect(surface, bordercolor, rect, 1, border_radius=radius)
            if item == self.selected:
                pygame.draw.line(surface, _C_GOLD_BRIGHT, (rect.x + 16, rect.y + 2), (rect.right - 16, rect.y + 2), 2)

            if glow > 0.01:
                glow_surf = pygame.Surface((w + 22, h + 22), pygame.SRCALPHA)
                for ring in range(5):
                    ring_alpha = int(glow * (28 - ring * 5))
                    if ring_alpha <= 0:
                        continue
                    offset = ring * 2 + 2
                    gw = w + offset * 2
                    gh = h + offset * 2
                    pygame.draw.rect(glow_surf, (*_C_GOLD, ring_alpha),
                        (11 - offset, 11 - offset, gw, gh),
                        border_radius=radius + offset, width=2)
                surface.blit(glow_surf, (x - 11, y - 11))
                draw_light_sweep(surface, rect, motion_time + i * 0.18, _C_GOLD_BRIGHT, alpha=int(10 + glow * 22))

            text_color = (226, 230, 234) if hovered else (200, 205, 210)
            if item == self.selected and not hovered:
                text_color = (239, 224, 185)
            active_font = font_bold if (hovered and font_bold) else font
            icon = icons.get(item)
            if icon is not None:
                draw_animated_icon(
                    surface,
                    icon,
                    (rect.centerx, rect.y + 22),
                    motion_time,
                    hover=0.7 if (hovered or item == self.selected) else 0.0,
                    accent=_C_GOLD_BRIGHT,
                    phase=i * 0.55,
                )
            text = active_font.render(item, True, text_color)
            text_rect = text.get_rect(center=(rect.centerx, rect.y + 48 + int(glow * 2)))
            surface.blit(text, text_rect)


class InGameUI:
    actionchoosecountry = "choosecountry"
    actionrecruit = "recruit"
    actionendturn = "endturn"
    actiondeclarewar = "declarewar"
    actionsplit = "split"
    actionmerge = "merge"
    actionfrontline = "frontline"
    actionautoadvance = "autoadvance"
    actiondetachregiment = "detachregiment"
    actiontogglefocuspanel = "togglefocuspanel"
    actionstartfocus = "startfocus"
    actiondomesticaffairs = "domesticaffairs"
    actiontooglemco = "tooglemco"
    actionpausemenu = "pausemenu"
    actionquitgame = "quitgame"
    actionweapon1 = "weapon_1"
    actionweapon2 = "weapon_2"
    actionweapon3 = "weapon_3"
    actionweapon4 = "weapon_4"

    def __init__(self, window_size):
        self.window_size = window_size
        self.title_font = pygame.font.SysFont("bahnschrift", 22, bold=True)
        self.font = pygame.font.SysFont("segoeui", 14)
        self.font_bold = pygame.font.SysFont("segoeui", 14, bold=True)
        self.small_font = pygame.font.SysFont("segoeui", 11)
        self.small_font_bold = pygame.font.SysFont("segoeui", 11, bold=True)
        self.number_font = pygame.font.SysFont("bahnschrift", 17, bold=True)
        
        self.ui_click_sound = pygame.mixer.Sound("game/sounds/click.wav")
        self.ui_click_sound.set_volume(0.4)

        self.leftbar_width = 256
        self.topbar_height = 80
        # widened so troop/country panels fit "seamlessly" in the right tab
        self.rightbar_width = 380
        self.bottombar_height = 104

        self.gamephase = "choosecountry"
        self.pendingcountry = None
        self.playercountry = None
        self.currentturnnumber = 1
        self.playergold = 0
        self.playerpopulation = 0
        self.playerstability = 50.0
        self.playerpp = 0
        self.playerap = 0
        self._active_manpower = 0
        self._combat_summary = {}
        self._manpower_cache_key = None
        self._gradient_surface_cache = {}
        self._glass_shadow_cache = {}
        self._glass_glow_cache = {}
        self._map_edge_shadow_cache = {}
        self._bar_overlay_cache = {}
        self._layout_cache_key = None
        self._merged_troop_badge_cache_key = None
        self._merged_troop_badge_cache = []
        self._motion_time = 0.0
        self._ambient_particles = AmbientParticleField(72, seed=203)
        self._ui_pulses = PulseLayer()
        self._drawer_progress = 0.0
        self._choose_progress = 0.0
        self._tooltip_progress = 0.0
        self._last_turn_seen = None
        self._last_resource_values = {}
        self._metric_flash = {}

        self.recruitamount = 0
        self.recruitenabled = False
        self._countrymenutarget = None
        self._selectedmapcountry = None
        self._selected_country_stats = {}
        self._bigflags = {}
        self._countriesatwarset = set()
        self._selectedtroopentries = []
        self._frontlineplacementmode = False
        self._troopbadgelist = []
        self._hovertext = None
        self._hovermousepos = (0, 0)
        self.focusview = FocusTreeView()
        self.researchview = ResearchTreeView()
        self.pausemenuopen = False
        self.active_left_tab = None
        self.warprogressopen = False
        self._warprogressdata = {}
        self.actionwarprogress = "warprogress"
        self.domesticaffairsopen = False
        self._domesticaffairsdata = {}
        self._domestic_active_tab = "Executive"
        self._domestic_selected_party_id = None
        self._domestic_segment_hitboxes = []
        self._systemstatus = {"fps": 0.0, "latency_ms": 0.0}
        self.notifications = []
        self._expanded_notification = None
        self._notification_scroll = 0
        self._notification_max_scroll = 0
        self._notification_card_rects = {}
        self._notification_popup_rect = pygame.Rect(0, 0, 10, 10)
        self._combat_popup_rect = pygame.Rect(0, 0, 10, 10)
        self._policy_popup_rect = pygame.Rect(0, 0, 10, 10)
        self._policy_focus_slot_rect = pygame.Rect(0, 0, 10, 10)
        self._policy_dropdown_progress = 0.0
        self._notificationcount = 0
        self._startdate = date(2020, 1, 1)
        self._daysperturn = 5
        

        # rolling FPS history for status graph (42 samples)
        self._fps_history: list[float] = [0.0] * 42

        self._flags = self._load_flags()
        self._badge_flags = {
            key: pygame.transform.scale(img, (20, 14))
            for key, img in self._flags.items()
        }
        self._leaderportraits = self._load_leader_portraits()
        self._topbar_icons = self._load_topbar_icons()

        self._choose_rect = pygame.Rect(0, 0, 160, 34)
        self._endturn_rect = pygame.Rect(0, 0, 10, 10)  # placed near map bottom-right
        self._endturn_glow = 0.0
        self._button_glows: dict[str, float] = {}
        self._topbar_metric_rects = {}
        self._topbar_metric_data = {}
        self._topbar_metric_glows = {}
        self._active_topbar_metric = None
        self._topbar_metric_popup_rect = pygame.Rect(0, 0, 10, 10)
        self._topbar_metric_snapshot = {}
        self._topbar_metric_rates = {}
        self._topbar_metric_rate_turn = None

        # right panel interactive rects (computed in applylayout)
        self._recruit_action_rect = pygame.Rect(0, 0, 10, 10)
        self._declarewar_rect = pygame.Rect(0, 0, 10, 10)
        self._split_rect = pygame.Rect(0, 0, 10, 10)
        self._merge_rect = pygame.Rect(0, 0, 10, 10)
        self._frontline_rect = pygame.Rect(0, 0, 10, 10)
        self._auto_advance_rect = pygame.Rect(0, 0, 10, 10)
        self._detach_regiment_rects = {}
        self._research_btn_rects = [pygame.Rect(0, 0, 10, 10) for _ in range(4)]
        self._research_back_rect = pygame.Rect(0, 0, 10, 10)
        self._warprogress_popup_rect = pygame.Rect(0, 0, 10, 10)
        self._warprogress_close_rect = pygame.Rect(0, 0, 10, 10)
        self._warprogress_header_rect = pygame.Rect(0, 0, 10, 10)
        self._warprogress_tab_rects = []
        self._warprogress_popup_pos = None
        self._warprogress_dragging = False
        self._warprogress_drag_offset = (0, 0)
        self._warprogress_active_index = 0
        self._domestic_popup_rect = pygame.Rect(0, 0, 10, 10)
        self._domestic_close_rect = pygame.Rect(0, 0, 10, 10)
        self._domestic_header_rect = pygame.Rect(0, 0, 10, 10)
        self._domestic_tab_rects = {}
        self._domestic_popup_pos = None
        self._domestic_dragging = False
        self._domestic_drag_offset = (0, 0)
        self.production_popup_open = False
        self._production_popup_back_rect = pygame.Rect(0, 0, 10, 10)
        self._production_popup_rect = pygame.Rect(0, 0, 10, 10)
        self._production_item_rects = {}
        self._production_scroll = 0
        self._production_max_scroll = 0
        self._production_item_count = 44
        self.production_selected = None
        self._researched_weapon_nodes: list[dict] = []
        self._recruit_action_rect = pygame.Rect(0, 0, 10, 10)
        self._declarewar_rect = pygame.Rect(0, 0, 10, 10)
        self._split_rect = pygame.Rect(0, 0, 10, 10)
        self._merge_rect = pygame.Rect(0, 0, 10, 10)
        self._frontline_rect = pygame.Rect(0, 0, 10, 10)
        self._production_blank_rect = pygame.Rect(0, 0, 10, 10)
        self._research_btn_rects = [pygame.Rect(0, 0, 10, 10) for _ in range(4)]

        self.leftbar = LeftBar(pygame.Rect(0, 0, 10, 10))
        self.bottom_buttons = BottomButtons(pygame.Rect(0, 0, 10, 10))

        self.leftbar.set_items(
            [
                "CLEAR ALL",
                "",
                "NOTIFICATIONS",
                "LOGISTICS",
                "COMBAT",
                "INTEL",
                "NATIONAL POLICY",
                "DOMESTIC AFFAIRS"
            ]
        )
        self.bottom_buttons.set_items(
            [
                "RESEARCH",
                "DIPLOMACY",
                "TRADE",
                "PRODUCTION",
                "CONSTRUCTION",
                "TROOPS",
            ]
        )
        self.bottom_buttons.set_selected(None)

        self.topbar = Panel(pygame.Rect(0, 0, 10, 10), _C_PANEL_DARK)
        self.rightbar = Panel(pygame.Rect(0, 0, 10, 10), _C_PANEL_DARK)
        self.bottombar = Panel(pygame.Rect(0, 0, 10, 10), (5, 10, 17))
        self.pause_menu = pygame.Rect(0,0,10,10)
        self.quit_menu = pygame.Rect(0,0,10,10)
        self.map_rect = pygame.Rect(0, 0, 10, 10)
        self.applylayout()


    

    def _load_flags(self):
        flags = {}
        flag_path = os.path.normpath(
            os.path.join(os.path.dirname(__file__), "..", "flags")
        )

        if not os.path.isdir(flag_path):
            return flags

        for filename in os.listdir(flag_path):
            if not filename.lower().endswith(".png"):
                continue

            filepath = os.path.join(flag_path, filename)

            country_key = (
                os.path.splitext(filename)[0]
                .strip()
                .lower()
                .replace(" ", "_")
                .replace("-", "_")
            )

            try:
                img = pygame.image.load(filepath).convert_alpha()

                # Store ORIGINAL high-resolution image
                flags[country_key] = img

            except pygame.error:
                continue

        return flags

    def _load_leader_portraits(self):
        portraits = {}
        portrait_path = os.path.normpath(
            os.path.join(os.path.dirname(__file__), "..", "assets", "leaders")
        )
        if not os.path.isdir(portrait_path):
            return portraits
        for filename in os.listdir(portrait_path):
            lower = filename.lower()
            if not (lower.endswith(".png") or lower.endswith(".jpg") or lower.endswith(".jpeg")):
                continue
            key = os.path.splitext(filename)[0].strip().lower()
            filepath = os.path.join(portrait_path, filename)
            try:
                portraits[key] = pygame.image.load(filepath).convert_alpha()
            except pygame.error:
                continue
        return portraits

    @staticmethod
    def _portrait_key(name):
        text = str(name or "").strip().lower()
        chars = []
        previous_sep = False
        for character in text:
            if character.isalnum():
                chars.append(character)
                previous_sep = False
            elif not previous_sep:
                chars.append("_")
                previous_sep = True
        return "".join(chars).strip("_")

    def _load_topbar_icons(self):
        icons = {}
        icon_path = os.path.normpath(
            os.path.join(os.path.dirname(__file__), "..", "images", "ui_icons")
        )
        icon_files = {
            "turn": "turn.svg",
            "date": "date.svg",
            "gold": "gold.svg",
            "population": "population.svg",
            "manpower": "manpower.svg",
            "stability": "stability.svg",
            "political_power": "political_power.svg",
            "action_points": "action_points.svg",
            "CLEAR ALL": "clear_all.svg",
            "NOTIFICATIONS": "notifications.svg",
            "LOGISTICS": "logistics.svg",
            "COMBAT": "combat.svg",
            "INTEL": "intel.svg",
            "NATIONAL POLICY": "national_policy.svg",
            "DOMESTIC AFFAIRS": "domestic_affairs.svg",
            "notifications": "notifications.svg",
            "logistics": "logistics.svg",
            "combat": "combat.svg",
            "intel": "intel.svg",
            "national_policy": "national_policy.svg",
            "domestic_affairs": "domestic_affairs.svg",
            "RESEARCH": "research.svg",
            "DIPLOMACY": "diplomacy.svg",
            "TRADE": "trade.svg",
            "PRODUCTION": "production.svg",
            "CONSTRUCTION": "construction.svg",
            "TROOPS": "recruit.svg",
            "research": "research.svg",
            "diplomacy": "diplomacy.svg",
            "trade": "trade.svg",
            "production": "production.svg",
            "construction": "construction.svg",
            "recruit": "recruit.svg",
            "war_progress": "war_progress.svg",
            "occupation": "occupation.svg",
            "close": "close.svg",
        }

        for key, filename in icon_files.items():
            filepath = os.path.join(icon_path, filename)
            if not os.path.isfile(filepath):
                continue
            try:
                image = pygame.image.load(filepath).convert_alpha()
                icons[key] = pygame.transform.smoothscale(image, (20, 20))
            except pygame.error:
                continue

        return icons

    @staticmethod
    def _format_number(value):
        try:
            return f"{int(value):,}"
        except (TypeError, ValueError):
            return "0"

    @staticmethod
    def _format_decimal(value):
        try:
            number = float(value)
        except (TypeError, ValueError):
            number = 0.0
        if abs(number - int(number)) < 0.05:
            return f"{int(number):,}"
        return f"{number:,.1f}"

    @staticmethod
    def _format_compact_number(value):
        try:
            number = float(value)
        except (TypeError, ValueError):
            number = 0.0

        sign = "-" if number < 0 else ""
        number = abs(number)
        for suffix, divisor in (("B", 1_000_000_000), ("M", 1_000_000), ("K", 1_000)):
            if number >= divisor:
                compact = number / divisor
                text = f"{compact:.1f}".rstrip("0").rstrip(".")
                return f"{sign}{text}{suffix}"
        return f"{sign}{int(number):,}"

    @staticmethod
    def _format_signed_compact_number(value):
        try:
            number = float(value)
        except (TypeError, ValueError):
            number = 0.0
        if abs(number) < 0.05:
            return "0"
        prefix = "+" if number > 0 else ""
        return f"{prefix}{InGameUI._format_compact_number(number)}"

    def _format_ingame_date(self):
        try:
            turnnumber = max(1, int(self.currentturnnumber))
        except (TypeError, ValueError):
            turnnumber = 1
        currentdate = self._startdate + timedelta(days=(turnnumber - 1) * self._daysperturn)
        return currentdate.strftime("%d/%m/%Y")

    @staticmethod
    def _fit_text(font, text, max_width):
        # trim long labels before they enter fixed-width war columns.
        text = str(text)
        if font.size(text)[0] <= max_width:
            return text

        suffix = "..."
        available_width = max(0, max_width - font.size(suffix)[0])
        fitted = ""
        for char in text:
            candidate = fitted + char
            if font.size(candidate)[0] > available_width:
                break
            fitted = candidate
        return fitted.rstrip() + suffix if fitted else suffix

    def _draw_text_fit(self, surface, text, color, x, y, max_width, font=None):
        font = font or self.font
        fitted = self._fit_text(font, text, max_width)
        surface.blit(font.render(fitted, True, color), (x, y))

    def _draw_vertical_gradient_rect(self, surface, rect, top_color, bottom_color, radius=0):
        if rect.width <= 0 or rect.height <= 0:
            return
        top_color = tuple(top_color[:3])
        bottom_color = tuple(bottom_color[:3])
        radius = int(radius or 0)
        cachekey = (rect.width, rect.height, top_color, bottom_color, radius)
        gradient = self._gradient_surface_cache.get(cachekey)
        if gradient is None:
            gradient = pygame.Surface(rect.size, pygame.SRCALPHA)
            for y in range(rect.height):
                t = y / max(1, rect.height - 1)
                color = tuple(int(top_color[i] + (bottom_color[i] - top_color[i]) * t) for i in range(3))
                pygame.draw.line(gradient, (*color, 255), (0, y), (rect.width, y))
            if radius:
                mask = pygame.Surface(rect.size, pygame.SRCALPHA)
                pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=radius)
                gradient.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            if len(self._gradient_surface_cache) > 256:
                self._gradient_surface_cache.clear()
            self._gradient_surface_cache[cachekey] = gradient
        surface.blit(gradient, rect.topleft)

    def _draw_glass_panel(self, surface, rect, radius=6, border=(58, 71, 89), glow=False):
        radius = int(radius or 0)
        if glow:
            glowkey = (rect.width, rect.height, radius)
            glow_surface = self._glass_glow_cache.get(glowkey)
            if glow_surface is None:
                glow_surface = pygame.Surface((rect.width + 24, rect.height + 24), pygame.SRCALPHA)
                pygame.draw.rect(glow_surface, (212, 169, 77, 35), glow_surface.get_rect(), border_radius=radius + 8)
                if len(self._glass_glow_cache) > 128:
                    self._glass_glow_cache.clear()
                self._glass_glow_cache[glowkey] = glow_surface
            surface.blit(glow_surface, (rect.x - 12, rect.y - 12))
        shadowkey = (rect.width, rect.height, radius)
        shadow = self._glass_shadow_cache.get(shadowkey)
        if shadow is None:
            shadow = pygame.Surface((rect.width + 10, rect.height + 10), pygame.SRCALPHA)
            pygame.draw.rect(shadow, (0, 0, 0, 105), shadow.get_rect(), border_radius=radius + 2)
            if len(self._glass_shadow_cache) > 128:
                self._glass_shadow_cache.clear()
            self._glass_shadow_cache[shadowkey] = shadow
        surface.blit(shadow, (rect.x - 4, rect.y - 2))
        self._draw_vertical_gradient_rect(surface, rect, (22, 31, 48), (9, 15, 24), radius=radius)
        pygame.draw.rect(surface, border, rect, 1, border_radius=radius)
        pygame.draw.line(surface, (41, 49, 60), (rect.x + 8, rect.y + 1), (rect.right - 8, rect.y + 1), 1)
        if rect.width >= 64 and rect.height >= 32:
            draw_light_sweep(surface, rect, self._motion_time, border, alpha=14 if not glow else 24)
            if rect.height >= 90:
                draw_scanlines(surface, rect, self._motion_time, color=(74, 143, 231), alpha=6, spacing=30)

    def _draw_command_atmosphere(self, surface):
        if self.map_rect.width <= 0 or self.map_rect.height <= 0:
            return
        map_rect = self.map_rect.clip(surface.get_rect())
        if map_rect.width <= 0 or map_rect.height <= 0:
            return
        self._ambient_particles.draw(
            surface,
            map_rect,
            self._motion_time,
            color=(94, 160, 220),
            parallax=(
                (self._hovermousepos[0] - surface.get_width() * 0.5) * 0.012,
                (self._hovermousepos[1] - surface.get_height() * 0.5) * 0.010,
            ),
        )

    def _flash_metric(self, key, amount=1.0):
        self._metric_flash[key] = max(float(amount), self._metric_flash.get(key, 0.0))

    def _draw_bottombar_background(self, surface):
        rect = self.bottombar.rect
        if rect.width <= 0 or rect.height <= 0:
            return
        cachekey = ("bottom", rect.width, rect.height)
        overlay = self._bar_overlay_cache.get(cachekey)
        if overlay is None:
            overlay = pygame.Surface(rect.size, pygame.SRCALPHA)
            pygame.draw.rect(overlay, (4, 9, 16, 158), overlay.get_rect())
            pygame.draw.line(overlay, (212, 169, 77, 80), (0, 0), (rect.width, 0), 1)
            pygame.draw.line(overlay, (74, 143, 231, 35), (0, 1), (rect.width, 1), 1)
            if len(self._bar_overlay_cache) > 12:
                self._bar_overlay_cache.clear()
            self._bar_overlay_cache[cachekey] = overlay
        surface.blit(overlay, rect.topleft)

    def _draw_topbar_background(self, surface):
        rect = self.topbar.rect
        if rect.width <= 0 or rect.height <= 0:
            return

        self._draw_vertical_gradient_rect(surface, rect, (13, 22, 36), (6, 10, 18))
        pygame.draw.line(surface, (25, 34, 47), rect.topleft, rect.topright, 1)
        pygame.draw.line(surface, (76, 64, 38), (rect.x, rect.bottom - 2), (rect.right, rect.bottom - 2), 1)
        pygame.draw.line(surface, _C_GOLD, (rect.x, rect.bottom - 1), (rect.right, rect.bottom - 1), 1)
        draw_light_sweep(surface, rect, self._motion_time * 0.72, _C_GOLD_BRIGHT, alpha=16)
        draw_scanlines(surface, rect, self._motion_time, color=(74, 143, 231), alpha=6, spacing=30)

    def _draw_map_edge_shadows(self, surface):
        rect = self.map_rect.clip(surface.get_rect())
        if rect.width <= 0 or rect.height <= 0:
            return

        edge_w = max(96, int(rect.width * 0.11))
        edge_w = max(1, min(rect.width // 2, edge_w))
        cachekey = (rect.width, rect.height, edge_w)
        cacheentry = self._map_edge_shadow_cache.get(cachekey)
        if cacheentry is None:
            shadow = pygame.Surface((edge_w, rect.height), pygame.SRCALPHA)
            for step in range(edge_w):
                t = step / max(1, edge_w - 1)
                alpha = int(92 * (1.0 - t) ** 2.4)
                pygame.draw.line(shadow, (0, 0, 0, alpha), (step, 0), (step, rect.height))
            right_shadow = pygame.transform.flip(shadow, True, False)
            contact = pygame.Surface((rect.width, 18), pygame.SRCALPHA)
            for step in range(contact.get_height()):
                alpha = int(40 * (1.0 - step / max(1, contact.get_height() - 1)) ** 2)
                pygame.draw.line(contact, (0, 0, 0, alpha), (0, step), (rect.width, step))
            if len(self._map_edge_shadow_cache) > 12:
                self._map_edge_shadow_cache.clear()
            cacheentry = (shadow, right_shadow, contact)
            self._map_edge_shadow_cache[cachekey] = cacheentry
        shadow, right_shadow, contact = cacheentry

        surface.blit(shadow, rect.topleft)
        surface.blit(right_shadow, (rect.right - edge_w, rect.y))

        # A narrow contact shadow under fixed panels gives depth without a boxed vignette.
        surface.blit(contact, rect.topleft)

    def _draw_resource_chip(
        self,
        surface,
        x,
        y,
        icon_key,
        label,
        value,
        max_right,
        accent=(200, 170, 80),
        metric_key=None,
        mouse=None,
    ):
        icon = self._topbar_icons.get(icon_key)
        metric_key = metric_key or icon_key
        mouse = mouse or pygame.mouse.get_pos()
        value = str(value)
        label = str(label)
        value_surface = self.number_font.render(value, True, _C_TEXT)
        label_surface = self.small_font.render(label, True, _C_TEXT_MUTED)
        chip_width = max(112, value_surface.get_width() + 68, label_surface.get_width() + 56)
        if icon_key == "date":
            chip_width = max(148, value_surface.get_width() + 68, label_surface.get_width() + 56)
        chip_height = 56

        if x + chip_width > max_right:
            return x, False

        rect = pygame.Rect(x, y, chip_width, chip_height)
        hovered = rect.collidepoint(mouse)
        active = metric_key == self._active_topbar_metric
        flash = self._metric_flash.get(metric_key, 0.0)
        glow = self._topbar_metric_glows.get(metric_key, 0.0)
        if hovered or active or flash > 0.01:
            glow = min(1.0, glow + 0.14)
        else:
            glow = max(0.0, glow - 0.08)
        self._topbar_metric_glows[metric_key] = glow
        visual_glow = max(glow, flash)
        draw_rect = scale_rect(
            rect,
            1.0 + glow * 0.025 + flash * 0.055,
            (0, -flash * 2),
        )

        if visual_glow > 0.01:
            glow_surface = pygame.Surface((draw_rect.width + 24, draw_rect.height + 24), pygame.SRCALPHA)
            for ring in range(4):
                ring_alpha = int(visual_glow * (38 - ring * 7))
                if ring_alpha <= 0:
                    continue
                offset = ring * 2 + 2
                pygame.draw.rect(
                    glow_surface,
                    (*accent, ring_alpha),
                    (12 - offset, 12 - offset, draw_rect.width + offset * 2, draw_rect.height + offset * 2),
                    width=2,
                    border_radius=8 + offset,
                )
            surface.blit(glow_surface, (draw_rect.x - 12, draw_rect.y - 12))

        border = accent if active else ((72, 88, 111) if hovered else (48, 62, 80))
        if flash > 0.01:
            border = mix_color(border, _C_GOLD_BRIGHT, flash)
        self._draw_glass_panel(surface, draw_rect, radius=6, border=border)
        pygame.draw.line(surface, accent, (draw_rect.x + 8, draw_rect.y + 9), (draw_rect.x + 8, draw_rect.bottom - 9), 2)

        draw_x = draw_rect.x + 20
        if icon is not None:
            draw_animated_icon(
                surface,
                icon,
                (draw_x + icon.get_width() // 2, draw_rect.y + draw_rect.height // 2),
                self._motion_time,
                hover=max(glow, flash) * 0.8 if (hovered or active) else 0.0,
                accent=accent,
                phase=len(metric_key) * 0.41,
            )
            draw_x += icon.get_width() + 12
        surface.blit(value_surface, (draw_x, draw_rect.y + 9))
        surface.blit(label_surface, (draw_x, draw_rect.y + 32))
        if metric_key:
            self._topbar_metric_rects[metric_key] = rect
            self._topbar_metric_data[metric_key] = {
                "label": label,
                "value": value,
                "icon_key": icon_key,
                "accent": accent,
            }
        return rect.right + 10, True

    def _draw_country_chip(self, surface, x, y, country_text, flag_img, max_right):
        text_surface = self.title_font.render(str(country_text), True, _C_TEXT)
        label_surface = self.small_font.render("PLAYER COUNTRY", True, _C_TEXT_MUTED)
        flag_width = 32 if flag_img is not None else 0
        flag_gap = 10 if flag_img is not None else 0
        chip_width = max(200, 18 + flag_width + flag_gap + text_surface.get_width() + 36)
        chip_height = 56

        if x + chip_width > max_right:
            return x, False

        rect = pygame.Rect(x, y, chip_width, chip_height)
        self._draw_glass_panel(surface, rect, radius=6, border=(73, 67, 49), glow=True)

        draw_x = rect.x + 16
        if flag_img is not None:
            scaled_flag = pygame.transform.smoothscale(flag_img, (32, 22))
            flag_rect = scaled_flag.get_rect()
            flag_rect.topleft = (
                draw_x,
                rect.y + (chip_height - flag_rect.height) // 2 + int(math.sin(self._motion_time * 2.4) * 1.5),
            )
            draw_soft_glow(surface, flag_rect.inflate(8, 6), _C_GOLD, 0.28 + 0.12 * pulse(self._motion_time, 2.0), radius=5, rings=3)
            surface.blit(scaled_flag, flag_rect)
            draw_x += scaled_flag.get_width() + flag_gap

        surface.blit(text_surface, (draw_x, rect.y + 9))
        surface.blit(label_surface, (draw_x, rect.y + 34))
        return rect.right + 12, True

    def _topbar_metric_values(self):
        return {
            "gold": float(self.playergold or 0),
            "population": float(self.playerpopulation or 0),
            "manpower": float(self._active_manpower or 0),
            "stability": float(self.playerstability or 0),
            "political_power": float(self.playerpp or 0),
            "action_points": float(self.playerap or 0),
            "turn": float(self.currentturnnumber or 0),
        }

    def _update_topbar_metric_rates(self):
        values = self._topbar_metric_values()
        try:
            turnnumber = int(self.currentturnnumber or 0)
        except (TypeError, ValueError):
            turnnumber = 0

        if self._topbar_metric_rate_turn is None:
            self._topbar_metric_rates = {key: 0.0 for key in values}
        elif turnnumber != self._topbar_metric_rate_turn:
            previousvalues = self._topbar_metric_snapshot or {}
            self._topbar_metric_rates = {
                key: values.get(key, 0.0) - float(previousvalues.get(key, values.get(key, 0.0)) or 0.0)
                for key in values
            }

        self._topbar_metric_snapshot = values
        self._topbar_metric_rate_turn = turnnumber

    def _get_topbar_metric_info(self, metric_key):
        affected = {
            "gold": "tax income, controlled land, focus rewards, recruitment and spending",
            "population": "controlled population, recruitment, conquest, scripted events",
            "manpower": "troops in controlled provinces and active movement orders",
            "stability": "focus effects, events, war pressure and national policy",
            "political_power": "turn income, focuses, diplomacy and decision costs",
            "action_points": "turn refreshes, movement orders and command actions",
            "turn": "end-turn actions, research progress, focus progress and movement",
            "date": "turn length and campaign start date",
        }
        full_names = {
            "gold": "Treasury Gold",
            "population": "National Population",
            "manpower": "Active Manpower",
            "stability": "National Stability",
            "political_power": "Political Power",
            "action_points": "Action Points",
            "turn": "Campaign Turn",
            "date": "Campaign Date",
        }
        rate = float(self._topbar_metric_rates.get(metric_key, 0.0) or 0.0)
        if metric_key == "date":
            rate_text = f"+{int(self._daysperturn)} days / turn"
        elif metric_key == "turn":
            rate_text = "+1 / turn"
        elif metric_key == "stability":
            rate_text = "No change last turn" if abs(rate) < 0.05 else f"{rate:+.1f}% / turn"
        else:
            rate_text = (
                "No change last turn"
                if abs(rate) < 0.05
                else f"{self._format_signed_compact_number(rate)} / turn"
            )

        data = self._topbar_metric_data.get(metric_key, {})
        return {
            "full_name": full_names.get(metric_key, str(data.get("label", metric_key)).title()),
            "current": str(data.get("value", "")),
            "rate": rate_text,
            "affected": affected.get(metric_key, "current campaign state and scripted effects"),
            "icon_key": data.get("icon_key", metric_key),
            "accent": data.get("accent", _C_GOLD),
        }

    def _draw_notification_popup(self, surface, mouse):
        if self.active_left_tab != "NOTIFICATIONS":
            self._notification_popup_rect = pygame.Rect(0, 0, 10, 10)
            self._notification_card_rects = {}
            return

        anchor_rect = self.leftbar.item_rects.get("NOTIFICATIONS")
        if anchor_rect is None:
            self._notification_popup_rect = pygame.Rect(0, 0, 10, 10)
            self._notification_card_rects = {}
            return

        popup_w = min(380, max(300, surface.get_width() - anchor_rect.right - 24))
        popup_h = 424 if self.notifications else 104
        popup_h = min(popup_h, max(104, surface.get_height() - self.topbar_height - 24))
        popup_x = anchor_rect.right + 8
        popup_y = anchor_rect.y
        popup_x = max(12, min(surface.get_width() - popup_w - 12, popup_x))
        popup_y = max(self.topbar_height + 8, min(surface.get_height() - popup_h - 12, popup_y))
        popup_rect = pygame.Rect(popup_x, popup_y, popup_w, popup_h)
        self._notification_popup_rect = popup_rect

        self._draw_glass_panel(surface, popup_rect, radius=8, border=_C_GOLD, glow=True)
        content_rect = popup_rect.inflate(-24, -22)
        self._draw_notifications_panel(surface, content_rect, mouse)

    def _wrap_notification_text(self, text, font, max_width):
        words = str(text or "").split(" ")
        lines = []
        current_line = ""
        for word in words:
            test_line = f"{current_line} {word}".strip()
            if current_line and font.size(test_line)[0] > max_width:
                lines.append(current_line)
                current_line = word
            else:
                current_line = test_line
        if current_line:
            lines.append(current_line)
        return lines

    def _draw_notifications_panel(self, surface, content_rect, mouse):
        self._notification_card_rects = {}
        header = self.font_bold.render("NOTIFICATIONS", True, _C_GOLD_BRIGHT)
        surface.blit(header, (content_rect.x, content_rect.y))

        if not self.notifications:
            empty_text = self.font.render("No notifications.", True, _C_TEXT_MUTED)
            surface.blit(empty_text, (content_rect.x, content_rect.y + 30))
            self._notification_scroll = 0
            self._notification_max_scroll = 0
            return

        card_x = content_rect.x
        card_w = content_rect.width
        card_y_start = content_rect.y + 30
        card_h = 48
        min_expanded_h = 120
        gap = 6
        bottom_padding = 18
        max_visible = max(1, content_rect.bottom - card_y_start)

        total_h = 0
        expanded_height_lookup = {}
        for idx in range(len(self.notifications)):
            h = card_h
            if self._expanded_notification == idx:
                desc = str(self.notifications[idx].get("description", ""))
                lines = self._wrap_notification_text(desc, self.font, card_w - 20)
                h = max(min_expanded_h, 46 + len(lines) * 18 + 14)
                expanded_height_lookup[idx] = h
            total_h += h + gap
        total_h += bottom_padding
        max_scroll = max(0, total_h - max_visible)
        self._notification_max_scroll = max_scroll
        self._notification_scroll = max(0, min(self._notification_scroll, max_scroll))
        y = card_y_start - self._notification_scroll

        for reverse_idx, notif in enumerate(reversed(self.notifications)):
            idx = len(self.notifications) - 1 - reverse_idx
            is_expanded = (self._expanded_notification == idx)
            notif_h = expanded_height_lookup.get(idx, card_h) if is_expanded else card_h
            card_rect = pygame.Rect(card_x, y, card_w, notif_h)

            if y + notif_h > content_rect.y and y < content_rect.bottom:
                accent = _C_GOLD if not notif.get("read") else _C_STEEL
                self._draw_glass_panel(surface, card_rect, radius=6, border=accent)
                inner = card_rect.inflate(-10, -6)
                turn_label = self.small_font.render(f"T{notif.get('turn', '?')}", True, _C_TEXT_MUTED)
                surface.blit(turn_label, (inner.x, inner.y + 2))
                title_surf = self.font_bold.render(str(notif.get("title", "")), True, _C_TEXT)
                title_x = inner.x + turn_label.get_width() + 10
                title_max = inner.width - turn_label.get_width() - 10
                self._draw_text_fit(surface, notif.get("title", ""), _C_TEXT, title_x, inner.y + 2, title_max, self.font_bold)

                if is_expanded:
                    desc = str(notif.get("description", ""))
                    desc_lines = self._wrap_notification_text(desc, self.font, inner.width - 10)
                    line_y = inner.y + 28
                    for line in desc_lines:
                        line_surf = self.font.render(line, True, _C_TEXT_MUTED)
                        surface.blit(line_surf, (inner.x + 2, line_y))
                        line_y += 18
                        if line_y > card_rect.bottom - 6:
                            break

            self._notification_card_rects[idx] = card_rect
            y += notif_h + gap

        if max_scroll > 0:
            track_rect = pygame.Rect(content_rect.right - 5, card_y_start, 4, max_visible)
            pygame.draw.rect(surface, (39, 51, 68), track_rect, border_radius=2)
            thumb_h = max(28, int(max_visible * (max_visible / max(total_h, 1))))
            thumb_y = track_rect.y + int((track_rect.height - thumb_h) * (self._notification_scroll / max_scroll))
            pygame.draw.rect(surface, _C_GOLD, pygame.Rect(track_rect.x, thumb_y, track_rect.width, thumb_h), border_radius=2)

    def _draw_combat_popup(self, surface, mouse):
        if self.active_left_tab != "COMBAT":
            self._combat_popup_rect = pygame.Rect(0, 0, 10, 10)
            return

        anchor_rect = self.leftbar.item_rects.get("COMBAT")
        if anchor_rect is None:
            self._combat_popup_rect = pygame.Rect(0, 0, 10, 10)
            return

        popup_w = min(380, max(300, surface.get_width() - anchor_rect.right - 24))
        popup_h = 302
        popup_x = anchor_rect.right + 8
        popup_y = anchor_rect.y
        popup_x = max(12, min(surface.get_width() - popup_w - 12, popup_x))
        popup_y = max(self.topbar_height + 8, min(surface.get_height() - popup_h - 12, popup_y))
        popup_rect = pygame.Rect(popup_x, popup_y, popup_w, popup_h)
        self._combat_popup_rect = popup_rect

        self._draw_glass_panel(surface, popup_rect, radius=8, border=_C_GOLD, glow=True)
        content_rect = popup_rect.inflate(-24, -22)
        surface.blit(self.font_bold.render("COMBAT", True, _C_GOLD_BRIGHT), (content_rect.x, content_rect.y))

        data = self._warprogressdata or {}
        wars = [war for war in data.get("wars", []) if isinstance(war, dict)]
        if not wars and data.get("aggressor") and data.get("defender"):
            wars = [data]
        wins = 0
        losses = 0
        for war in wars:
            progress = float(war.get("progress", 0.0) or 0.0)
            defender_progress = float(war.get("defender_progress", 0.0) or 0.0)
            if self.playercountry == war.get("aggressor"):
                own_pressure = progress
                enemy_pressure = defender_progress
            elif self.playercountry == war.get("defender"):
                own_pressure = defender_progress
                enemy_pressure = progress
            else:
                own_pressure = progress
                enemy_pressure = defender_progress
            if own_pressure > enemy_pressure + 5.0:
                wins += 1
            elif enemy_pressure > own_pressure + 5.0:
                losses += 1

        active_wars = len(wars) if wars else len(self._countriesatwarset or ())
        summary = self._combat_summary or {}
        preparedness = max(0.0, min(100.0, float(summary.get("preparedness", 0.0) or 0.0)))
        avg_strength = float(summary.get("avg_strength", 0.0) or 0.0)
        if active_wars <= 0:
            status = "N/A"
            status_detail = "No active wars"
            status_color = _C_STEEL
        else:
            status = "Advantage" if wins > losses else ("Under Pressure" if losses > wins else "Contested")
            status_detail = f"War pressure W/L {wins}-{losses}"
            status_color = _C_SUCCESS if wins > losses else (_C_DANGER if losses > wins else _C_GOLD_BRIGHT)

        chip_gap = 8
        chip_w = (content_rect.width - chip_gap) // 2
        chip_y = content_rect.y + 30
        self._draw_metric_chip(
            surface,
            pygame.Rect(content_rect.x, chip_y, chip_w, 48),
            "Manpower",
            self._format_compact_number(self._active_manpower),
            icon_key="manpower",
            accent=_C_INFO,
        )
        self._draw_metric_chip(
            surface,
            pygame.Rect(content_rect.x + chip_w + chip_gap, chip_y, chip_w, 48),
            "Avg Strength",
            self._format_compact_number(avg_strength),
            icon_key="combat",
            accent=_C_DANGER,
        )

        chip_y += 58
        self._draw_metric_chip(
            surface,
            pygame.Rect(content_rect.x, chip_y, chip_w, 48),
            "Prepared",
            f"{preparedness:.0f}%",
            icon_key="logistics",
            accent=_C_SUCCESS,
        )
        self._draw_metric_chip(
            surface,
            pygame.Rect(content_rect.x + chip_w + chip_gap, chip_y, chip_w, 48),
            "Wars",
            str(active_wars),
            icon_key="intel",
            accent=_C_GOLD,
        )

        status_rect = pygame.Rect(content_rect.x, chip_y + 58, content_rect.width, 48)
        self._draw_vertical_gradient_rect(surface, status_rect, (31, 42, 62), (9, 15, 24), radius=8)
        pygame.draw.rect(surface, status_color, status_rect, 1, border_radius=8)
        pygame.draw.rect(surface, (*status_color, 42), status_rect.inflate(-2, -2), 1, border_radius=7)
        status_icon = self._topbar_icons.get("combat")
        icon_box = pygame.Rect(status_rect.x + 10, status_rect.y + 10, 28, 28)
        self._draw_vertical_gradient_rect(surface, icon_box, (37, 49, 72), (14, 21, 35), radius=6)
        pygame.draw.rect(surface, status_color, icon_box, 1, border_radius=6)
        if status_icon is not None:
            small_icon = pygame.transform.smoothscale(status_icon, (18, 18))
            surface.blit(small_icon, small_icon.get_rect(center=icon_box.center))

        status_pill_text = self.small_font_bold.render(status.upper(), True, status_color)
        status_pill_w = min(148, status_pill_text.get_width() + 24)
        status_pill = pygame.Rect(status_rect.right - status_pill_w - 10, status_rect.y + 11, status_pill_w, 26)
        self._draw_vertical_gradient_rect(surface, status_pill, (22, 31, 47), (8, 13, 22), radius=13)
        pygame.draw.rect(surface, status_color, status_pill, 1, border_radius=13)
        surface.blit(status_pill_text, status_pill_text.get_rect(center=status_pill.center))

        status_x = icon_box.right + 10
        surface.blit(self.small_font_bold.render("FRONT STATUS", True, _C_TEXT_MUTED), (status_x, status_rect.y + 8))
        self._draw_text_fit(
            surface,
            status_detail,
            _C_TEXT,
            status_x,
            status_rect.y + 25,
            status_pill.x - status_x - 12,
            self.font_bold,
        )

        self._war_progress_rect = pygame.Rect(content_rect.x, content_rect.bottom - 42, content_rect.width, 34)
        self._draw_glow_btn(
            surface,
            "warprogress",
            self._war_progress_rect,
            True,
            "WAR PROGRESS",
            mouse=mouse,
        )

    def _draw_policy_popup(self, surface, mouse):
        if self.focusview.isopen:
            self._policy_popup_rect = pygame.Rect(0, 0, 10, 10)
            self._policy_focus_slot_rect = pygame.Rect(0, 0, 10, 10)
            return

        opening = self.active_left_tab == "NATIONAL POLICY"
        progress = max(0.0, min(1.0, float(self._policy_dropdown_progress or 0.0)))
        if not opening and progress <= 0.01:
            self._policy_popup_rect = pygame.Rect(0, 0, 10, 10)
            self._policy_focus_slot_rect = pygame.Rect(0, 0, 10, 10)
            return

        anchor_rect = self.leftbar.item_rects.get("NATIONAL POLICY")
        if anchor_rect is None:
            self._policy_popup_rect = pygame.Rect(0, 0, 10, 10)
            self._policy_focus_slot_rect = pygame.Rect(0, 0, 10, 10)
            return

        full_h = 104
        panel_gap = 6
        panel_rect = pygame.Rect(anchor_rect.x, anchor_rect.bottom + panel_gap, anchor_rect.width, full_h)
        max_bottom = min(surface.get_height() - 12, self.leftbar.rect.bottom - 12)
        available_h = max_bottom - panel_rect.y
        if available_h <= 8:
            self._policy_popup_rect = pygame.Rect(0, 0, 10, 10)
            self._policy_focus_slot_rect = pygame.Rect(0, 0, 10, 10)
            return
        if panel_rect.bottom > max_bottom:
            panel_rect.height = min(panel_rect.height, available_h)
        if panel_rect.height <= 8:
            self._policy_popup_rect = pygame.Rect(0, 0, 10, 10)
            self._policy_focus_slot_rect = pygame.Rect(0, 0, 10, 10)
            return

        eased = 1.0 - pow(1.0 - progress, 3)
        visible_h = max(1, min(panel_rect.height, int(panel_rect.height * eased)))
        visible_rect = pygame.Rect(panel_rect.x, panel_rect.y, panel_rect.width, visible_h)
        self._policy_popup_rect = visible_rect
        self._policy_focus_slot_rect = visible_rect if opening else pygame.Rect(0, 0, 10, 10)

        shadow = pygame.Surface((visible_rect.width + 12, visible_rect.height + 12), pygame.SRCALPHA)
        pygame.draw.rect(shadow, (0, 0, 0, 105), shadow.get_rect(), border_radius=10)
        surface.blit(shadow, (visible_rect.x - 6, visible_rect.y - 2))

        focusdata = self.focusview.data or {}
        active_title = str(focusdata.get("activefocustitle") or "").strip()
        active_id = focusdata.get("activefocusid")
        active_focus = None
        if active_id:
            for focus in focusdata.get("focuses", ()):
                if isinstance(focus, dict) and focus.get("id") == active_id:
                    active_focus = focus
                    break

        panel_surface = pygame.Surface(panel_rect.size, pygame.SRCALPHA)
        panel_bounds = panel_surface.get_rect()
        hovered = visible_rect.collidepoint(mouse)
        top = _C_POLICY_BROWN_LIGHT if hovered else _C_POLICY_BROWN
        pygame.draw.rect(panel_surface, _C_POLICY_BROWN_DARK, panel_bounds, border_radius=8)
        self._draw_vertical_gradient_rect(panel_surface, panel_bounds, top, _C_POLICY_BROWN_DARK, radius=8)
        pygame.draw.rect(panel_surface, (_C_GOLD if hovered else (112, 78, 44)), panel_bounds, 1, border_radius=8)
        pygame.draw.line(panel_surface, _C_GOLD_BRIGHT, (14, 1), (panel_bounds.width - 14, 1), 1)

        content_rect = panel_bounds.inflate(-18, -16)
        if active_title:
            icon_rect = pygame.Rect(content_rect.x, content_rect.y + 14, 46, 46)
            pygame.draw.rect(panel_surface, (32, 20, 14), icon_rect, border_radius=6)
            pygame.draw.rect(panel_surface, (122, 84, 49), icon_rect, 1, border_radius=6)
            icon = None
            if isinstance(active_focus, dict):
                icon = self.focusview.loadimage(active_focus.get("icon"))
            if icon is not None:
                scaled_icon = pygame.transform.smoothscale(icon, (34, 34))
                panel_surface.blit(scaled_icon, scaled_icon.get_rect(center=icon_rect.center))
            else:
                focus_mark = self.title_font.render("+", True, _C_GOLD_BRIGHT)
                panel_surface.blit(focus_mark, focus_mark.get_rect(center=icon_rect.center))

            text_x = icon_rect.right + 10
            self._draw_text_fit(
                panel_surface,
                "RUNNING FOCUS",
                _C_GOLD_BRIGHT,
                text_x,
                content_rect.y + 10,
                content_rect.right - text_x,
                self.small_font_bold,
            )
            self._draw_text_fit(
                panel_surface,
                active_title,
                _C_TEXT,
                text_x,
                content_rect.y + 30,
                content_rect.right - text_x,
                self.font_bold,
            )
            remaining = active_focus.get("remainingturns") if isinstance(active_focus, dict) else None
            progress = active_focus.get("progress") if isinstance(active_focus, dict) else None
            total = active_focus.get("turnsrequired") if isinstance(active_focus, dict) else None
            detail = "In progress"
            if remaining is not None and total:
                detail = f"{remaining} turns remaining  |  {progress}/{total}"
            self._draw_text_fit(
                panel_surface,
                detail,
                _C_TEXT_MUTED,
                text_x,
                content_rect.y + 50,
                content_rect.right - text_x,
                self.small_font,
            )

            if total:
                try:
                    fill_ratio = max(0.0, min(1.0, float(progress or 0) / float(total)))
                except (TypeError, ValueError, ZeroDivisionError):
                    fill_ratio = 0.0
                bar_rect = pygame.Rect(text_x, content_rect.y + 71, content_rect.right - text_x, 7)
                pygame.draw.rect(panel_surface, (30, 19, 13), bar_rect, border_radius=3)
                fill_rect = bar_rect.copy()
                fill_rect.width = int(bar_rect.width * fill_ratio)
                if fill_rect.width > 0:
                    pygame.draw.rect(panel_surface, _C_GOLD_BRIGHT, fill_rect, border_radius=3)
        else:
            select_text = self.font_bold.render("(select a national focus)", True, _C_GOLD_BRIGHT)
            select_rect = select_text.get_rect(center=panel_bounds.center)
            panel_surface.blit(select_text, select_rect)

        surface.blit(panel_surface.subsurface(pygame.Rect(0, 0, panel_rect.width, visible_h)), panel_rect.topleft)

    def _draw_topbar_metric_popup(self, surface, mouse):
        metric_key = self._active_topbar_metric
        anchor_rect = self._topbar_metric_rects.get(metric_key)
        if not metric_key or anchor_rect is None:
            self._topbar_metric_popup_rect = pygame.Rect(0, 0, 10, 10)
            return

        info = self._get_topbar_metric_info(metric_key)
        popup_w = min(332, max(284, surface.get_width() - 24))
        popup_h = 156
        popup_x = anchor_rect.centerx - popup_w // 2
        popup_y = anchor_rect.bottom + 8
        popup_x = max(12, min(surface.get_width() - popup_w - 12, popup_x))
        popup_y = max(self.topbar_height + 8, min(surface.get_height() - popup_h - 12, popup_y))
        popup_rect = pygame.Rect(popup_x, popup_y, popup_w, popup_h)
        self._topbar_metric_popup_rect = popup_rect

        self._draw_glass_panel(surface, popup_rect, radius=8, border=info["accent"], glow=True)
        icon = self._topbar_icons.get(info["icon_key"])
        title_x = popup_rect.x + 18
        if icon is not None:
            surface.blit(icon, (title_x, popup_rect.y + 16))
            title_x += icon.get_width() + 10
        surface.blit(self.font_bold.render(info["full_name"], True, _C_TEXT), (title_x, popup_rect.y + 12))
        current_text = self.small_font.render(f"Current: {info['current']}", True, _C_TEXT_MUTED)
        surface.blit(current_text, (title_x, popup_rect.y + 34))

        row_defs = (
            ("turn", "Rate", info["rate"]),
            ("logistics", "Affected by", info["affected"]),
            ("intel", "Shown as", self._topbar_metric_data.get(metric_key, {}).get("label", info["full_name"])),
        )
        row_y = popup_rect.y + 64
        for row_icon_key, label, value in row_defs:
            row_rect = pygame.Rect(popup_rect.x + 14, row_y, popup_rect.width - 28, 26)
            hovered = row_rect.collidepoint(mouse)
            row_top = (28, 39, 59) if hovered else (16, 24, 38)
            self._draw_vertical_gradient_rect(surface, row_rect, row_top, (9, 15, 24), radius=5)
            pygame.draw.rect(surface, (48, 62, 80), row_rect, 1, border_radius=5)
            row_icon = self._topbar_icons.get(row_icon_key)
            row_x = row_rect.x + 8
            if row_icon is not None:
                small_icon = pygame.transform.smoothscale(row_icon, (16, 16))
                surface.blit(small_icon, (row_x, row_rect.y + 5))
                row_x += 22
            label_surface = self.small_font_bold.render(str(label).upper(), True, _C_GOLD_BRIGHT)
            surface.blit(label_surface, (row_x, row_rect.y + 6))
            value_x = row_x + 82
            max_value_w = max(40, row_rect.right - value_x - 8)
            self._draw_text_fit(surface, value, _C_TEXT, value_x, row_rect.y + 5, max_value_w, self.small_font)
            row_y += 30

    def applylayout(self):
        window_width, window_height = self.window_size

        self.topbar.rect = pygame.Rect(0, 0, window_width, self.topbar_height)

        
        if self.gamephase == "choosecountry":
            show_left = False
            show_bottom = False
            show_right = False
        else:
            show_left = True
            show_bottom = True
            show_right = bool(
                self._countrymenutarget
                or self.bottom_buttons.selected == "PRODUCTION"
                or self.bottom_buttons.selected == "TROOPS"
                or self._selectedmapcountry
            )

        left_w = self.leftbar_width if show_left else 0
        bottom_h = self.bottombar_height if show_bottom else 0
        right_w = self.rightbar_width if show_right else 0

        self.leftbar.rect = pygame.Rect(0, self.topbar_height, left_w, max(0, window_height - self.topbar_height))

        right_x = max(0, window_width - right_w)
        self.rightbar.rect = pygame.Rect(
            right_x,
            self.topbar_height,
            right_w,
            max(0, window_height - self.topbar_height - bottom_h),
        )

        bottom_y = max(0, window_height - bottom_h)
        self.bottombar.rect = pygame.Rect(left_w, bottom_y, max(1, window_width - left_w), bottom_h)
        self.bottom_buttons.rect = self.bottombar.rect

        center_x = left_w
        center_y = self.topbar_height
        center_w = max(1, window_width - left_w - right_w)
        center_h = max(1, window_height - self.topbar_height)
        self.map_rect = pygame.Rect(center_x, center_y, center_w, center_h)

        # End turn sits above the command dock while the map renders beneath it.
        end_w = 196
        end_h = 74
        end_x = self.map_rect.right - end_w - 18
        end_limit_y = self.bottombar.rect.y if show_bottom else self.map_rect.bottom
        end_y = max(self.map_rect.y + 12, end_limit_y - end_h - 16)
        self._endturn_rect = pygame.Rect(end_x, end_y, end_w, end_h)

        # choose button near bottom-right of map in choosecountry (draw will override)

        # right panel content layout (play phase; safe even if right panel hidden)
        content_x = self.rightbar.rect.x + 12
        content_y = self.rightbar.rect.y + 12
        content_w = max(1, self.rightbar.rect.width - 24)
        self._recruit_action_rect = pygame.Rect(content_x, content_y + 40, content_w, 34)
        self._declarewar_rect = pygame.Rect(content_x, content_y + 82, content_w, 34)
        self._production_blank_rect = pygame.Rect(content_x, content_y + 40, content_w, 90)

        # troop decision buttons at the bottom of right panel
        btn_w = max(1, (content_w - 30) // 4)
        btn_h = 50
        btn_y = (self.rightbar.rect.bottom - 12 - btn_h) if self.rightbar.rect.width else (self.map_rect.bottom - 12 - btn_h)
        self._split_rect = pygame.Rect(content_x, btn_y, btn_w, btn_h)
        self._merge_rect = pygame.Rect(content_x + btn_w + 10, btn_y, btn_w, btn_h)
        self._frontline_rect = pygame.Rect(content_x + (btn_w + 10) * 2, btn_y, btn_w, btn_h)
        self._auto_advance_rect = pygame.Rect(content_x + (btn_w + 10) * 3, btn_y, btn_w, btn_h)
        btn_w = 400
        btn_h = 60
        btn_gap = 20
        total_h = 4 * btn_h + 3 * btn_gap
        start_x = (window_width - btn_w) // 2
        start_y = (window_height - total_h) // 2
        for i in range(4):
            self._research_btn_rects[i] = pygame.Rect(
                start_x,
                start_y + i * (btn_h + btn_gap),
                btn_w,
                btn_h
            )

        last_weapon_rect = self._research_btn_rects[3]

        back_w = 120
        back_h = 40
        back_x = start_x + (btn_w - back_w) // 2 
        back_y = last_weapon_rect.bottom + 20

        self._research_back_rect = pygame.Rect(back_x, back_y, back_w, back_h)
        menu_w = min(320, max(220, window_width - 80))
        menu_h = 170
        menu_x = max(0, (window_width - menu_w) // 2)
        menu_y = max(0, (window_height - menu_h) // 2)
        self._pausemenu_rect = pygame.Rect(menu_x, menu_y, menu_w, menu_h)
        self._pausequit_rect = pygame.Rect(menu_x + (menu_w - 150) // 2, menu_y + menu_h - 52, 150, 40)
        self._war_progress_rect = pygame.Rect(content_x, content_y + 40, content_w, 34)

    def _current_layout_key(self):
        return (
            self.window_size,
            self.gamephase,
            self.bottom_buttons.selected,
            self.active_left_tab,
            bool(self._countrymenutarget),
            bool(self._selectedmapcountry),
            self.focusview.isopen,
            self.researchview.isopen,
            self.pausemenuopen,
            self.warprogressopen,
        )

    def applylayoutifneeded(self):
        layoutkey = self._current_layout_key()
        if layoutkey == self._layout_cache_key:
            return
        self._layout_cache_key = layoutkey
        self.applylayout()

    def _get_visible_troop_badges(self):
        badgekey = tuple(
            (
                int(entry.get("center", (0, 0))[0]) if isinstance(entry, dict) and entry.get("center") else 0,
                int(entry.get("center", (0, 0))[1]) if isinstance(entry, dict) and entry.get("center") else 0,
                int(entry.get("troops", 0)) if isinstance(entry, dict) else 0,
                entry.get("country") if isinstance(entry, dict) else None,
                tuple(entry.get("backgroundcolor", (0, 0, 0))) if isinstance(entry, dict) else (0, 0, 0),
                tuple(entry.get("bordercolor", (165, 165, 165))) if isinstance(entry, dict) else (165, 165, 165),
                bool(entry.get("entrenched", False)) if isinstance(entry, dict) else False,
            )
            for entry in self._troopbadgelist
        )
        if badgekey != self._merged_troop_badge_cache_key:
            self._merged_troop_badge_cache_key = badgekey
            self._merged_troop_badge_cache = gui_mergetroopbadgeentries(
                self._troopbadgelist,
                self.font,
                self._badge_flags,
            )
        return self._merged_troop_badge_cache



        

    def select_map_country(self, country_name: str | None):
        self._selectedmapcountry = country_name
        if country_name:
            self._countrymenutarget = None
            self._selectedtroopentries = []
        self.applylayoutifneeded()

    def _get_big_flag(self, country_name, size=(240, 144)):
        if not country_name:
            return None
        key = str(country_name).strip().lower().replace(" ", "_").replace("-", "_")
        cache_key = (key, size)
        if cache_key in self._bigflags:
            return self._bigflags[cache_key]
        small_flag = self._flags.get(key)
        if not small_flag:
            return None
        big_flag = pygame.transform.smoothscale(small_flag, size)
        self._bigflags[cache_key] = big_flag
        return big_flag

    def setwindowsize(self, window_size):
        self.window_size = window_size
        self.applylayout()

    def sync(
        self,
        gamephase,
        pendingcountry,
        playercountry,
        currentturnnumber,
        playergold,
        playerpopulation,
        playerstability,
        playerpp,
        playerap,
        selectedprovinceid,
        provincemap,
        recruitamount,
        recruitenabled,
        developmentmode,
        recruitgoldcost,
        recruitpopulationcost,
        countrymenutarget,
        countriesatwarset,
        selectedtroopentries,
        frontlineplacementmode,
        hovertext,
        mouseposition,
        troopbadgelist,
        focusview=None,
        researchdata=None,
        warprogressdata=None,
        domesticaffairsdata=None,
        selected_country_stats=None,
        systemstatus=None,
        notifications=None,
    ):
        previous_notification_count = self._notificationcount
        previous_turn = self._last_turn_seen
        self.gamephase = gamephase
        self.pendingcountry = pendingcountry
        self.playercountry = playercountry
        self.currentturnnumber = currentturnnumber
        self.playergold = playergold
        self.playerpopulation = playerpopulation
        self.playerstability = playerstability
        self.playerpp = playerpp
        self.playerap = playerap
        self.recruitamount = recruitamount
        self.recruitenabled = bool(recruitenabled)
        self._countrymenutarget = countrymenutarget
        self._countriesatwarset = set(countriesatwarset or ())
        self._selectedtroopentries = list(selectedtroopentries or [])
        self._frontlineplacementmode = bool(frontlineplacementmode)
        self._troopbadgelist = list(troopbadgelist or [])
        self._hovertext = hovertext
        self._hovermousepos = tuple(mouseposition or (0, 0))
        if focusview is not None:
            self.focusview.setdata(focusview)
        if researchdata is not None:
            self.researchview.setdata(
                researchdata.get("researched", frozenset()),
                researchdata.get("researching_id"),
                researchdata.get("researching_turns_remaining", 0),
            )
            self._researched_weapon_nodes = self.researchview.get_researched_nodes()
        
        if warprogressdata is not None:
            self._warprogressdata = warprogressdata
        if domesticaffairsdata is not None:
            self._domesticaffairsdata = domesticaffairsdata
        if selected_country_stats is not None:
            self._selected_country_stats = selected_country_stats
        if systemstatus is not None:
            self._systemstatus = dict(systemstatus)
            try:
                fps_val = float(self._systemstatus.get("fps", 0.0) or 0.0)
            except Exception:
                fps_val = 0.0
            self._fps_history.append(fps_val)
            if len(self._fps_history) > 42:
                self._fps_history = self._fps_history[-42:]
        if notifications is not None:
            self.notifications = list(notifications)
        self._notificationcount = len([n for n in self.notifications if not n.get("read")])
        if self._notificationcount > previous_notification_count:
            self._ui_pulses.emit(self.leftbar.rect.center, _C_GOLD_BRIGHT, radius=120, duration=0.8, width=3)

        try:
            turn_value = int(currentturnnumber or 0)
        except (TypeError, ValueError):
            turn_value = 0
        if previous_turn is not None and turn_value != previous_turn:
            self._ui_pulses.emit(self.map_rect.center, _C_SUCCESS, radius=220, duration=0.95, width=3)
        self._last_turn_seen = turn_value

        self.applylayout()

        # cache active manpower (sum troops controlled by player) only when inputs change
        cache_key = (id(provincemap), self.playercountry, int(currentturnnumber or 0))
        if cache_key != self._manpower_cache_key:
            self._manpower_cache_key = cache_key
            manpower = 0
            controlled_count = 0
            troop_province_count = 0
            entrenchment_total = 0.0
            if self.playercountry and isinstance(provincemap, dict):
                for province in provincemap.values():
                    if not isinstance(province, dict):
                        continue
                    controller = province.get("controllercountry", province.get("country"))
                    if controller == self.playercountry:
                        controlled_count += 1
                        troops = int(province.get("troops", 0) or 0)
                        manpower += troops
                        if troops > 0:
                            troop_province_count += 1
                            last_activity = int(province.get("lasttroopactivityturn", 0) or 0)
                            entrenchment_total += max(0.0, min(1.0, (int(currentturnnumber or 0) - last_activity) / 3.0))
            self._active_manpower = manpower
            avg_strength = 0 if troop_province_count <= 0 else manpower / troop_province_count
            preparedness = 0.0 if troop_province_count <= 0 else (entrenchment_total / troop_province_count) * 100.0
            self._combat_summary = {
                "controlled_provinces": controlled_count,
                "troop_provinces": troop_province_count,
                "avg_strength": avg_strength,
                "preparedness": preparedness,
            }
        self._update_topbar_metric_rates()
        current_values = self._topbar_metric_values()
        if self._last_resource_values:
            for key, value in current_values.items():
                old_value = self._last_resource_values.get(key, value)
                if abs(float(value) - float(old_value)) > 0.001:
                    self._flash_metric(key, 1.0)
        self._last_resource_values = current_values

    def update(self, elapsedseconds: float):
        try:
            dt = max(0.0, min(0.1, float(elapsedseconds or 0.0)))
        except (TypeError, ValueError):
            dt = 0.0
        self._motion_time += dt
        self._ui_pulses.update(dt)
        self._drawer_progress = exp_lerp(self._drawer_progress, 1.0 if self.rightbar.rect.width else 0.0, 6.8, dt)
        self._choose_progress = exp_lerp(self._choose_progress, 1.0 if self.gamephase == "choosecountry" else 0.0, 6.0, dt)
        self._tooltip_progress = exp_lerp(self._tooltip_progress, 1.0 if self._hovertext else 0.0, 11.0, dt)
        for key in list(self._metric_flash.keys()):
            self._metric_flash[key] = max(0.0, self._metric_flash[key] - dt * 1.65)
            if self._metric_flash[key] <= 0.01:
                del self._metric_flash[key]

        target = 1.0 if self.active_left_tab == "NATIONAL POLICY" and not self.focusview.isopen else 0.0
        speed = 8.5
        if self._policy_dropdown_progress < target:
            self._policy_dropdown_progress = min(target, self._policy_dropdown_progress + dt * speed)
        elif self._policy_dropdown_progress > target:
            self._policy_dropdown_progress = max(target, self._policy_dropdown_progress - dt * speed)

    def _get_selected_division_entry(self):
        for entry in self._selectedtroopentries or ():
            if isinstance(entry, dict) and entry.get("divisionid"):
                return entry
        return None



    def process_event(self, event):

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            if self.domesticaffairsopen:
                self.domesticaffairsopen = False
                if self.active_left_tab == "DOMESTIC AFFAIRS":
                    self.active_left_tab = None
                self._domestic_dragging = False
                return None
            if self.warprogressopen:
                self.warprogressopen = False
                return None
            self.pausemenuopen = not self.pausemenuopen
            return self.actionpausemenu

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._ui_pulses.emit(event.pos, _C_GOLD_BRIGHT, radius=82, duration=0.42, width=2)

        if event.type == pygame.MOUSEWHEEL and self.active_left_tab == "NOTIFICATIONS":
            mouse_pos = pygame.mouse.get_pos()
            if self._notification_popup_rect.collidepoint(mouse_pos):
                self._notification_scroll = max(
                    0,
                    min(self._notification_max_scroll, self._notification_scroll - int(event.y) * 42),
                )
                return "notification_scroll"

        if self.domesticaffairsopen:
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self._domestic_dragging = False
                if self._domestic_popup_rect.collidepoint(event.pos):
                    return None
            if event.type == pygame.MOUSEMOTION and self._domestic_dragging:
                target_x = int(event.pos[0] - self._domestic_drag_offset[0])
                target_y = int(event.pos[1] - self._domestic_drag_offset[1])
                popup = self._domestic_popup_rect.copy()
                popup.topleft = (target_x, target_y)
                bounds = pygame.Rect(12, self.topbar_height + 8, self.window_size[0] - 24, self.window_size[1] - self.topbar_height - 20)
                popup.clamp_ip(bounds)
                self._domestic_popup_pos = popup.topleft
                return None
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self._domestic_close_rect.collidepoint(event.pos):
                    self.domesticaffairsopen = False
                    self._domestic_dragging = False
                    if self.active_left_tab == "DOMESTIC AFFAIRS":
                        self.active_left_tab = None
                    return None
                for tab_name, tab_rect in (self._domestic_tab_rects or {}).items():
                    if tab_rect.collidepoint(event.pos):
                        self._domestic_active_tab = tab_name
                        return None
                segment = self._get_domestic_segment_at_pos(event.pos)
                if segment is not None:
                    self._domestic_selected_party_id = segment.get("party_id")
                    return None
                if self._domestic_header_rect.collidepoint(event.pos):
                    self._domestic_dragging = True
                    self._domestic_drag_offset = (
                        event.pos[0] - self._domestic_popup_rect.x,
                        event.pos[1] - self._domestic_popup_rect.y,
                    )
                    return None
                if self._domestic_popup_rect.collidepoint(event.pos):
                    return None
        
        if self.production_popup_open:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.production_popup_open = False
                return None
            if event.type == pygame.MOUSEWHEEL:
                if self._production_popup_rect.collidepoint(pygame.mouse.get_pos()):
                    self._production_scroll = max(0, min(self._production_max_scroll, 
                        self._production_scroll - int(event.y) * 40))
                    return "production_scroll"
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self._production_popup_back_rect.collidepoint(event.pos):
                    self.production_popup_open = False
                    return None
                for idx, rect in self._production_item_rects.items():
                    if rect.collidepoint(event.pos):
                        self.production_selected = idx + 1
                        self.ui_click_sound.play()
                        # DO NOT close – keep popup open
                        return f"production_select_{idx+1}"
                # click outside = close
                if not self._production_popup_rect.collidepoint(event.pos):
                    self.production_popup_open = False
                    return None
                if self.warprogressopen:
                    if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                        self._warprogress_dragging = False
                        if self._warprogress_popup_rect.collidepoint(event.pos):
                            return None
                    if event.type == pygame.MOUSEMOTION and self._warprogress_dragging:
                        target_x = int(event.pos[0] - self._warprogress_drag_offset[0])
                        target_y = int(event.pos[1] - self._warprogress_drag_offset[1])
                        popup = self._warprogress_popup_rect.copy()
                        popup.topleft = (target_x, target_y)
                        bounds = pygame.Rect(12, self.topbar_height + 8, self.window_size[0] - 24, self.window_size[1] - self.topbar_height - 20)
                        popup.clamp_ip(bounds)
                        self._warprogress_popup_pos = popup.topleft
                        return None
                    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        if self._warprogress_close_rect.collidepoint(event.pos):
                            self.warprogressopen = False
                            self._warprogress_dragging = False
                            return None
                        for tab_index, tab_rect in enumerate(self._warprogress_tab_rects):
                            if tab_rect.collidepoint(event.pos):
                                self._warprogress_active_index = tab_index
                                return None
                        if self._warprogress_header_rect.collidepoint(event.pos):
                            self._warprogress_dragging = True
                            self._warprogress_drag_offset = (
                                event.pos[0] - self._warprogress_popup_rect.x,
                                event.pos[1] - self._warprogress_popup_rect.y,
                            )
                            return None
                        if self._warprogress_popup_rect.collidepoint(event.pos):
                            return None

        if self.pausemenuopen:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self._pausequit_rect.collidepoint(event.pos):
                    self.ui_click_sound.play()
                    return self.actionquitgame
            return None

        if self.gamephase == "play" and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            clicked_metric = None
            for metric_key, metric_rect in (self._topbar_metric_rects or {}).items():
                if metric_rect.collidepoint(pos):
                    clicked_metric = metric_key
                    break
            if clicked_metric:
                self._active_topbar_metric = (
                    None if self._active_topbar_metric == clicked_metric else clicked_metric
                )
                return None
            if self._active_topbar_metric:
                if self._topbar_metric_popup_rect.collidepoint(pos):
                    return None
                self._active_topbar_metric = None

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            selected_bottom_tab = self.bottom_buttons.selected
            if selected_bottom_tab:
                selected_rect = (self.bottom_buttons.item_rects or {}).get(selected_bottom_tab)
                if selected_rect is not None and selected_rect.collidepoint(pos):
                    self.bottom_buttons.set_selected(None)
                    if selected_bottom_tab == "RESEARCH":
                        self.researchview.isopen = False
                    self.applylayout()
                    return None

            selected_left_tab = self.active_left_tab
            if selected_left_tab:
                selected_rect = (self.leftbar.item_rects or {}).get(selected_left_tab)
                if selected_rect is not None and selected_rect.collidepoint(pos):
                    self.active_left_tab = None
                    if selected_left_tab == "NATIONAL POLICY":
                        self.focusview.isopen = False
                    if selected_left_tab == "DOMESTIC AFFAIRS":
                        self.domesticaffairsopen = False
                    self.applylayout()
                    return None
        
        if self.focusview.isopen:
            self.domesticaffairsopen = False
            result = self.focusview.handleevent(event)
            if not self.focusview.isopen:
                self.active_left_tab = None
                self.applylayout()
            return result

        if self.researchview.isopen:
            self.domesticaffairsopen = False
            result = self.researchview.handleevent(event)
            if not self.researchview.isopen:
                self.bottom_buttons.set_selected(None)
                self.applylayout()
            return result

        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return None

        pos = event.pos
        if self.gamephase == "choosecountry":
            if self.pendingcountry and self._choose_rect.collidepoint(pos):
                return self.actionchoosecountry
            return None

        for item, rect in (self.leftbar.item_rects or {}).items():
            if rect.collidepoint(pos):

                self.ui_click_sound.play()
                if item == "CLEAR ALL":
                    self.notifications.clear()
                    self._expanded_notification = None
                    self._notification_scroll = 0
                    return None
                if item == "NOTIFICATIONS":
                    self.domesticaffairsopen = False
                    self.active_left_tab = None if self.active_left_tab == "NOTIFICATIONS" else "NOTIFICATIONS"
                    self.applylayout()
                    return None
                if item == "COMBAT":
                    self.domesticaffairsopen = False
                    self.active_left_tab = None if self.active_left_tab == "COMBAT" else "COMBAT"
                    self._countrymenutarget = None
                    self._selectedmapcountry = None
                    self.applylayout()
                    return None
                if item == "NATIONAL POLICY":
                    self.domesticaffairsopen = False
                    self.active_left_tab = None if self.active_left_tab == "NATIONAL POLICY" else "NATIONAL POLICY"
                    self._countrymenutarget = None
                    self._selectedmapcountry = None
                    self.applylayout()
                    return None
                if item == "DOMESTIC AFFAIRS":
                    if not self.playercountry:
                        return None
                    self.domesticaffairsopen = not self.domesticaffairsopen
                    self.active_left_tab = "DOMESTIC AFFAIRS" if self.domesticaffairsopen else None
                    if self.domesticaffairsopen:
                        self._domestic_active_tab = self._domestic_active_tab or "Executive"
                    self.applylayout()
                    return self.actiondomesticaffairs
                self.domesticaffairsopen = False
                self.active_left_tab = item
                self.applylayout()
                if item == "NOTIFICATIONS":
                    return None
                return None

        for item, rect in (self.bottom_buttons.item_rects or {}).items():
            if rect.collidepoint(pos):
                self.ui_click_sound.play()
                self.domesticaffairsopen = False
                if self.active_left_tab == "DOMESTIC AFFAIRS":
                    self.active_left_tab = None
                self.bottom_buttons.set_selected(item)
                self.applylayout()
                if item == "RESEARCH":
                    self.researchview.toggleview()
                return None
            
        if (
            self.domesticaffairsopen
            and self._domestic_active_tab == "Health"
            and hasattr(self, "_mco_button_rect")
            and self._mco_button_rect.collidepoint(pos)
        ):
            self.ui_click_sound.play()
            return self.actiontogglemco

      
        if self._endturn_rect.collidepoint(pos):
            self.ui_click_sound.play()
            return self.actionendturn

        selected_tab = self.bottom_buttons.selected

        if selected_tab == "PRODUCTION" and not self._countrymenutarget:
            if self._production_blank_rect.collidepoint(pos):
                self.production_popup_open = True
                return None

        if selected_tab == "RESEARCH" and not self._countrymenutarget:

            if self._research_back_rect.collidepoint(pos):
                self.bottom_buttons.set_selected(None)
                self.applylayout()
                return "back_from_research"

            for i in range(4):
                if self._research_btn_rects[i].collidepoint(pos):
                    return getattr(self, f"actionweapon{i+1}")

            return None


        if self.active_left_tab == "NOTIFICATIONS":
            for idx, card_rect in (self._notification_card_rects or {}).items():
                if card_rect.collidepoint(pos):
                    self.ui_click_sound.play()
                    if self._expanded_notification == idx:
                        self._expanded_notification = None
                    else:
                        self._expanded_notification = idx
                        if idx < len(self.notifications):
                            self.notifications[idx]["read"] = True
                        if card_rect.centery > self._notification_popup_rect.centery:
                            self._notification_scroll = 999999
                    return None

        if self.active_left_tab == "COMBAT" and not self._countrymenutarget:
            if self._war_progress_rect.collidepoint(pos):
                self.ui_click_sound.play()
                self.warprogressopen = not self.warprogressopen
                return self.actionwarprogress
        if self.active_left_tab == "NATIONAL POLICY":
            if self._policy_focus_slot_rect.collidepoint(pos):
                self.ui_click_sound.play()
                self.active_left_tab = None
                self._policy_dropdown_progress = 0.0
                self.focusview.openview()
                self.applylayout()
                return self.actiontogglefocuspanel
        if self._selectedmapcountry and not self._countrymenutarget:
            if self._declarewar_rect.collidepoint(pos):
                if (
                    self.playercountry
                    and self._selectedmapcountry != self.playercountry
                    and self._selectedmapcountry not in self._countriesatwarset
                ):
                    return self.actiondeclarewar
                return None
        if selected_tab == "TROOPS":
            if self._recruit_action_rect.collidepoint(pos):
                self.ui_click_sound.play()
                if self.recruitenabled:
                    return self.actionrecruit
                return None
            for provinceid, detachrect in (self._detach_regiment_rects or {}).items():
                if detachrect.collidepoint(pos):
                    return (self.actiondetachregiment, provinceid)

      
        if selected_tab == "TROOPS" and self._selectedtroopentries:
            selected = [e for e in self._selectedtroopentries if isinstance(e, dict)]
            totaltroops = sum(max(0, int(e.get("troops", 0))) for e in selected)
            if totaltroops > 0:
                if self._split_rect.collidepoint(pos) and totaltroops > 1:
                    self.ui_click_sound.play()
                    return self.actionsplit
                if self._merge_rect.collidepoint(pos) and len(selected) > 1:
                    self.ui_click_sound.play()
                    return self.actionmerge
                if self._frontline_rect.collidepoint(pos):
                    self.ui_click_sound.play()
                    return self.actionfrontline
                divisionentry = self._get_selected_division_entry()
                if self._auto_advance_rect.collidepoint(pos) and divisionentry:
                    return (self.actionautoadvance, divisionentry.get("divisionid"))

            return None
       
    def ispointeroverui(self, mouseposition):
        if self.domesticaffairsopen and self._domestic_popup_rect.collidepoint(mouseposition):
            return True

        if self.warprogressopen and self._warprogress_popup_rect.collidepoint(mouseposition):
            return True
        
        if self.production_popup_open and self._production_popup_rect.collidepoint(mouseposition):
            return True
       
        if self.focusview.pointerover(mouseposition):
            return True
        if self.researchview.pointerover(mouseposition):
            return True
        if self._endturn_rect.collidepoint(mouseposition):
            return True
        if self.leftbar.rect.collidepoint(mouseposition):
            return True
        if self.topbar.rect.collidepoint(mouseposition):
            return True
        if self.rightbar.rect.collidepoint(mouseposition):
            return True
        if self.active_left_tab == "NOTIFICATIONS" and self._notification_popup_rect.collidepoint(mouseposition):
            return True
        if self.active_left_tab == "COMBAT" and self._combat_popup_rect.collidepoint(mouseposition):
            return True
        if self._policy_dropdown_progress > 0.01 and self._policy_popup_rect.collidepoint(mouseposition):
            return True
        if self.bottombar.rect.collidepoint(mouseposition):
            return True
        return False

    def draw(self, surface: pygame.Surface):
        mouse = pygame.mouse.get_pos()



    

        if self.gamephase == "choosecountry":
            self._draw_command_atmosphere(surface)
            # minimal UI only during choosecountry
            self._draw_topbar_background(surface)
            title = self.title_font.render("EBEE COMMAND", True, _C_GOLD_BRIGHT)
            subtitle = self.small_font.render("SELECT THEATER COMMAND", True, _C_TEXT_MUTED)
            surface.blit(title, (20, 16))
            surface.blit(subtitle, (20, 45))

            # clear non-map areas so the screen doesn't keep old UI pixels
            bg = (10, 10, 10)
            if self.map_rect.x > 0:
                pygame.draw.rect(surface, bg, pygame.Rect(0, self.topbar_height, self.map_rect.x, surface.get_height() - self.topbar_height))
            if self.map_rect.right < surface.get_width():
                pygame.draw.rect(surface, bg, pygame.Rect(self.map_rect.right, self.topbar_height, surface.get_width() - self.map_rect.right, surface.get_height() - self.topbar_height))
            if self.map_rect.bottom < surface.get_height():
                pygame.draw.rect(surface, bg, pygame.Rect(0, self.map_rect.bottom, surface.get_width(), surface.get_height() - self.map_rect.bottom))

            # place choose button near bottom-right of the map viewport
            bw = 220
            bh = 34
            bx = self.map_rect.right - bw - 12
            by = self.map_rect.bottom - bh - 12
            self._choose_rect = pygame.Rect(bx, by, bw, bh)

            enabled = bool(self.pendingcountry)
            self._draw_glass_panel(
                surface,
                self._choose_rect,
                radius=6,
                border=(_C_SUCCESS if enabled else (69, 75, 84)),
                glow=enabled,
            )
            label = self.font_bold.render("CHOOSE COUNTRY", True, (_C_TEXT if enabled else _C_TEXT_MUTED))
            surface.blit(label, label.get_rect(center=self._choose_rect.center))
            if self.pendingcountry:
                selected = self.font.render(f"Selected: {self.pendingcountry}", True, _C_TEXT)
                surface.blit(selected, (self._choose_rect.x, self._choose_rect.y - 22))
            self._ui_pulses.draw(surface)

            return

                

        # full UI chrome (play)
        self._draw_map_edge_shadows(surface)
        self._draw_command_atmosphere(surface)
        if self.leftbar.rect.width:
            self.leftbar.draw(
                surface,
                self.font,
                mouse,
                font_bold=self.font_bold,
                icons=self._topbar_icons,
                selected=self.active_left_tab,
                disabled_items=set() if self.playercountry else {"DOMESTIC AFFAIRS"},
                statusdata=self._systemstatus,
                notification_count=self._notificationcount,
            )
        self._draw_bottombar_background(surface)
        self.bottom_buttons.draw(surface, self.font, mouse, font_bold=self.font_bold, icons=self._topbar_icons)
        self._draw_topbar_background(surface)

        # end turn button (bottom-right of map)
        hovered = self._endturn_rect.collidepoint(mouse)
        if hovered:
            self._endturn_glow = min(1.0, self._endturn_glow + 0.12)
        else:
            self._endturn_glow = max(0.0, self._endturn_glow - 0.08)
        glow = self._endturn_glow
        radius = 8
        if glow > 0.01:
            ew, eh = self._endturn_rect.size
            ex, ey = self._endturn_rect.topleft
            glow_surf = pygame.Surface((ew + 28, eh + 28), pygame.SRCALPHA)
            for ring in range(5):
                ring_alpha = int(glow * (42 - ring * 7))
                if ring_alpha <= 0:
                    continue
                offset = ring * 2 + 2
                pygame.draw.rect(glow_surf, (*_C_SUCCESS, ring_alpha),
                    (14 - offset, 14 - offset, ew + offset * 2, eh + offset * 2),
                    border_radius=radius + offset, width=2)
            surface.blit(glow_surf, (ex - 14, ey - 14))
        self._draw_vertical_gradient_rect(
            surface,
            self._endturn_rect,
            (20, 92, 56) if hovered else (17, 73, 46),
            (7, 32, 25),
            radius=radius,
        )
        pygame.draw.rect(surface, (58, 178, 116) if hovered else (45, 136, 91), self._endturn_rect, 1, border_radius=radius)
        pygame.draw.line(surface, (136, 232, 181), (self._endturn_rect.x + 14, self._endturn_rect.y + 2), (self._endturn_rect.right - 14, self._endturn_rect.y + 2), 1)
        end_font = self.font_bold
        end_label = end_font.render("END TURN", True, _C_TEXT)
        sub_label = self.small_font.render(f"Turn {int(self.currentturnnumber)}", True, (196, 226, 209))
        surface.blit(end_label, end_label.get_rect(center=(self._endturn_rect.centerx - 10, self._endturn_rect.y + 28)))
        surface.blit(sub_label, sub_label.get_rect(center=(self._endturn_rect.centerx - 10, self._endturn_rect.y + 55)))
        arrow = self.title_font.render(">", True, (200, 244, 221))
        surface.blit(arrow, arrow.get_rect(center=(self._endturn_rect.right - 26, self._endturn_rect.centery)))

        # top title + stats line (with mini flag)
        base_title = "EBEE COMMAND"
        info_x = 18
        info_y = 12
        emblem_center = (info_x + 26, info_y + 27)
        pygame.draw.circle(surface, _C_GOLD, emblem_center, 24, 1)
        pygame.draw.circle(surface, (88, 70, 34), emblem_center, 17, 1)
        pygame.draw.line(surface, _C_GOLD, (emblem_center[0], emblem_center[1] - 22), (emblem_center[0], emblem_center[1] + 22), 1)
        pygame.draw.line(surface, _C_GOLD, (emblem_center[0] - 22, emblem_center[1]), (emblem_center[0] + 22, emblem_center[1]), 1)
        title_x = info_x + 64
        title_surface = self.title_font.render(base_title, True, _C_GOLD_BRIGHT)
        subtitle_surface = self.small_font.render("STRATEGIC COMMAND & CONTROL", True, _C_TEXT_MUTED)
        surface.blit(title_surface, (title_x, info_y + 5))
        surface.blit(subtitle_surface, (title_x, info_y + 34))

        flag_img = None
        if self.playercountry:
            key = str(self.playercountry).strip().lower().replace(" ", "_").replace("-", "_")
            flag_img = self._flags.get(key) if self._flags.get(key) else None
        stats_x = max(396, title_x + title_surface.get_width() + 38)
        stats_y = 12

        country_text = str(self.playercountry or "None")
        date_text = self._format_ingame_date()
        max_right = self.topbar.rect.right - 12
        stats_x, _ = self._draw_country_chip(surface, stats_x, stats_y, country_text, flag_img, max_right)

        self._topbar_metric_rects = {}
        self._topbar_metric_data = {}
        chip_data = (
            ("gold", "Gold", self._format_number(self.playergold), (177, 145, 70)),
            ("turn", "Turn", str(int(self.currentturnnumber)), (130, 138, 146)),
            ("date", "Date", date_text, (177, 145, 70)),
            ("population", "Population", self._format_compact_number(self.playerpopulation), (130, 138, 146)),
            ("manpower", "Active MP", self._format_compact_number(self._active_manpower), (177, 145, 70)),
            ("stability", "Stability", f"{self.playerstability:.0f}%", (177, 145, 70)),
            ("political_power", "PP", str(int(self.playerpp)), (130, 138, 146)),
            ("action_points", "AP", str(int(self.playerap)), (177, 145, 70)),
        )
        for icon_key, label_text, value_text, accent in chip_data:
            stats_x, did_draw = self._draw_resource_chip(
                surface,
                stats_x,
                stats_y,
                icon_key,
                label_text,
                value_text,
                max_right,
                accent=accent,
                metric_key=icon_key,
                mouse=mouse,
            )
            if not did_draw:
                break

        # troop badges on top of the map (map-local centers need viewport offset)
        visiblebadgelist = self._get_visible_troop_badges()
        for entry in visiblebadgelist:
            if not isinstance(entry, dict):
                continue
            center = entry.get("center")
            if not center:
                continue
            cx = int(center[0] + self.map_rect.x)
            cy = int(center[1] + self.map_rect.y)
            border_color = entry.get("bordercolor", (165, 165, 165))
            badge_pulse = 0.25 + 0.35 * pulse(self._motion_time, 3.0, cx * 0.015 + cy * 0.011)
            if border_color == _C_DANGER:
                badge_pulse = 0.65 + 0.35 * pulse(self._motion_time, 5.2)
            elif border_color == _C_GOLD:
                badge_pulse = 0.45 + 0.35 * pulse(self._motion_time, 4.0)
            draw_soft_glow(
                surface,
                pygame.Rect(cx - 26, cy - 16, 52, 32),
                border_color,
                badge_pulse,
                radius=8,
                rings=3,
            )
            gui_drawtroopcountbadge(
                surface,
                (cx, cy + int(math.sin(self._motion_time * 2.3 + cx * 0.01) * 1.5)),
                entry.get("troops", 0),
                self.font,
                self._badge_flags,
                entry.get("country"),
                backgroundcolor=entry.get("backgroundcolor", (0, 0, 0)),
                bordercolor=entry.get("bordercolor", (165, 165, 165)),
                rows=entry.get("rows"),
            )

        # hover tooltip (full-window coords) must be on top of badges
        if self._hovertext:
            tooltip_lines = []
            if isinstance(self._hovertext, dict):
                name = self._hovertext.get("name", "unknown")
                provinceid = self._hovertext.get("provinceid", "unknown")
                population = self._hovertext.get("population", "unknown")
                country = self._hovertext.get("country", "unknown")
                terrain = self._hovertext.get("terrain", "unknown")
                province_count = self._hovertext.get("province_count", "unknown")
                vp = self._hovertext.get("victory_points", 0)
                
                tooltip_lines = [
                    f"State: {name}",
                    f"Province: {provinceid}",
                    f"Population: {population}",
                    f"Country: {country}",
                    f"Terrain Type: {terrain}",
                    f"Number of states: {province_count}",
                ]
                
                if vp > 0:
                    tooltip_lines.append(f"Victory Points: {vp}")
                
            else:
                tooltip_lines = [str(self._hovertext)]

            padding = 10
            text_surfs = []
            for index, line in enumerate(tooltip_lines):
                color = _C_GOLD_BRIGHT if index == 0 else (_C_TEXT if index <= 2 else _C_TEXT_MUTED)
                font = self.font_bold if index == 0 else self.font
                text_surfs.append(font.render(line, True, color))
            box_w = max(ts.get_width() for ts in text_surfs) + padding * 2
            box_h = sum(ts.get_height() for ts in text_surfs) + padding * 2

            mx, my = self._hovermousepos
            x = int(mx + 16)
            y = int(my + 16)
            x = max(0, min(surface.get_width() - box_w, x))
            y = max(0, min(surface.get_height() - box_h, y))
            rect = pygame.Rect(x, y, box_w, box_h)
            tooltip_ease = ease_out_cubic(self._tooltip_progress)
            rect = rect.move(int((1.0 - tooltip_ease) * 10), int((1.0 - tooltip_ease) * 8))

            draw_soft_glow(surface, rect, _C_GOLD, 0.22 + tooltip_ease * 0.32, radius=7, rings=4)
            self._draw_glass_panel(surface, rect, radius=5, border=(126, 102, 58))
            ty = rect.y + padding
            for ts in text_surfs:
                surface.blit(ts, (rect.x + padding, ty))
                ty += ts.get_height()



        if self.production_popup_open:
            overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 140))
            surface.blit(overlay, (0, 0))
            popup_rect = pygame.Rect(0, 0, 640, 520)
            popup_rect.center = surface.get_rect().center
            self._production_popup_rect = popup_rect
            self._draw_glass_panel(surface, popup_rect, radius=8, border=(72, 86, 108), glow=True)

            title = self.title_font.render("PRODUCTION", True, _C_GOLD_BRIGHT)
            surface.blit(title, title.get_rect(center=(popup_rect.centerx, popup_rect.y + 32)))
            subtitle = self.small_font.render("Select production item", True, _C_TEXT_MUTED)
            surface.blit(subtitle, subtitle.get_rect(center=(popup_rect.centerx, popup_rect.y + 58)))

            list_top = popup_rect.y + 80
            list_bottom = popup_rect.bottom - 70
            list_rect = pygame.Rect(popup_rect.x + 24, list_top, popup_rect.width - 48, list_bottom - list_top)
            pygame.draw.rect(surface, (7, 12, 20), list_rect, border_radius=6)
            pygame.draw.rect(surface, (43, 56, 73), list_rect, 1, border_radius=6)

            row_h = 44
            gap = 6
            total_h = self._production_item_count * (row_h + gap)
            visible_h = list_rect.height
            self._production_max_scroll = max(0, total_h - visible_h + gap)
            self._production_scroll = max(0, min(self._production_scroll, self._production_max_scroll))

            self._production_item_rects = {}
            y = list_rect.y + 6 - self._production_scroll
            for i in range(self._production_item_count):
                row_rect = pygame.Rect(list_rect.x + 8, y, list_rect.width - 16, row_h)
                if row_rect.bottom >= list_rect.y and row_rect.top <= list_rect.bottom:
                    self._production_item_rects[i] = row_rect
                    selected = self.production_selected == (i + 1)

                    
                    researched = self._researched_weapon_nodes
                    if i < len(researched):
                        node = researched[i]
                        label = node["label"]
                        is_unlocked = True
                 
                        cat_tag = node.get("category", "")
                        display_label = f"{label}  [{cat_tag}]" if cat_tag else label
                    else:
                        display_label = f"Production Item {i + 1}"
                        is_unlocked = False

                    self._draw_glow_btn(
                        surface, f"prod_item_{i}", row_rect, True, display_label,
                        primary=selected or is_unlocked, selected=selected, mouse=mouse,
                        align='left'
                    )

                    
                    if is_unlocked and row_rect.width >= 120:
                        badge_text = self.small_font_bold.render("✓ RESEARCHED", True, (67, 181, 129))
                        badge_x = row_rect.right - badge_text.get_width() - 12
                        badge_y = row_rect.centery - badge_text.get_height() // 2
                        if badge_x > row_rect.x + row_rect.width // 2:
                            surface.blit(badge_text, (badge_x, badge_y))

                y += row_h + gap

            if self._production_max_scroll > 0:
                track_rect = pygame.Rect(list_rect.right - 6, list_rect.y + 2, 4, list_rect.height - 4)
                pygame.draw.rect(surface, (39, 51, 68), track_rect, border_radius=2)
                thumb_h = max(28, int(list_rect.height * (visible_h / max(total_h, 1))))
                thumb_y = track_rect.y + int((track_rect.height - thumb_h) * (self._production_scroll / self._production_max_scroll))
                pygame.draw.rect(surface, _C_GOLD, pygame.Rect(track_rect.x, thumb_y, track_rect.width, thumb_h), border_radius=2)

            back_w, back_h = 140, 40
            self._production_popup_back_rect = pygame.Rect(0, 0, back_w, back_h)
            self._production_popup_back_rect.centerx = popup_rect.centerx
            self._production_popup_back_rect.y = popup_rect.bottom - back_h - 18
            self._draw_glow_btn(surface, "prod_back", self._production_popup_back_rect, True, "BACK", mouse=mouse)

        if self.focusview.isopen:
            self.focusview.draw(surface, self.title_font, self.font, mouse)
            self._draw_topbar_metric_popup(surface, mouse)
            self._draw_notification_popup(surface, mouse)
            self._draw_combat_popup(surface, mouse)
            self._draw_policy_popup(surface, mouse)
            if self.warprogressopen:
                self._draw_war_progress_popup(surface, mouse)
            if self.domesticaffairsopen:
                self._draw_domestic_affairs_popup(surface, mouse)
            if self.pausemenuopen:
                self._draw_pausemenu(surface)
            self._ui_pulses.draw(surface)
            return

        if self.researchview.isopen:
            self.researchview.draw(surface, self.title_font, self.font, mouse)
            self._draw_topbar_metric_popup(surface, mouse)
            self._draw_notification_popup(surface, mouse)
            self._draw_combat_popup(surface, mouse)
            self._draw_policy_popup(surface, mouse)
            if self.warprogressopen:
                self._draw_war_progress_popup(surface, mouse)
            if self.domesticaffairsopen:
                self._draw_domestic_affairs_popup(surface, mouse)
            if self.pausemenuopen:
                self._draw_pausemenu(surface)
            self._ui_pulses.draw(surface)
            return

        selected_tab = self.bottom_buttons.selected
        if not self.rightbar.rect.width:
            self._draw_topbar_metric_popup(surface, mouse)
            self._draw_notification_popup(surface, mouse)
            self._draw_combat_popup(surface, mouse)
            self._draw_policy_popup(surface, mouse)
            if self.warprogressopen:
                self._draw_war_progress_popup(surface, mouse)
            if self.domesticaffairsopen:
                self._draw_domestic_affairs_popup(surface, mouse)
            if self.pausemenuopen:
                self._draw_pausemenu(surface)
            self._ui_pulses.draw(surface)
            return
                
       

        content_rect = self.rightbar.rect.inflate(-24, -24)
        content_rect.topleft = (self.rightbar.rect.x + 12, self.rightbar.rect.y + 12)

        
        self._draw_glass_panel(surface, self.rightbar.rect, radius=0, border=(44, 58, 76))
        pygame.draw.rect(surface, (10, 16, 25), content_rect, border_radius=6)

        panel_title = "COUNTRY" if (self._countrymenutarget or self._selectedmapcountry) else str(selected_tab or "")
        header = self.font_bold.render(panel_title, True, _C_GOLD_BRIGHT)
        surface.blit(header, (content_rect.x, content_rect.y))

        y_cursor = content_rect.y + 24

       
        if self._countrymenutarget:
            alreadyatwar = self._countrymenutarget in self._countriesatwarset
            surface.blit(self.font.render("Country actions", True, (240, 240, 240)), (content_rect.x, y_cursor + 6))
            country_key = str(self._countrymenutarget or "").strip().lower().replace(" ", "_").replace("-", "_")
            flag_img = self._flags.get(country_key) if country_key else None
            draw_x = content_rect.x
            draw_y = y_cursor + 30
            if flag_img:
                surface.blit(flag_img, (draw_x, draw_y + 2))
                draw_x += flag_img.get_width() + 6
            surface.blit(self.font.render(str(self._countrymenutarget), True, (220, 220, 220)), (draw_x, draw_y))
            status = "Status: at war" if alreadyatwar else "Status: peace"
            surface.blit(self.font.render(status, True, (205, 205, 215)), (content_rect.x, y_cursor + 52))
            self._declarewar_rect.topleft = (content_rect.x, y_cursor + 82)
            self._draw_glow_btn(
                surface, "declarewar", self._declarewar_rect,
                not alreadyatwar,
                "Declare War" if not alreadyatwar else "Already at war!",
                mouse=mouse,
            )
            y_cursor += 130

        elif self._selectedmapcountry and not self._countrymenutarget:
            big_flag = self._get_big_flag(self._selectedmapcountry, size=(240, 144))
            y_cursor = content_rect.y + 45
            if big_flag:
                flag_x = content_rect.x + (content_rect.width - big_flag.get_width()) // 2
                surface.blit(big_flag, (flag_x, y_cursor))
                y_cursor += big_flag.get_height() + 16

            name_surf = self.title_font.render(str(self._selectedmapcountry), True, (240, 240, 240))
            surface.blit(name_surf, (content_rect.x, y_cursor))
            y_cursor += name_surf.get_height() + 8

            stats = self._selected_country_stats or {}
            lines = [
                f"Armies: {self._format_number(stats.get('population', 0))}",
                f"Manpower:   {self._format_number(stats.get('manpower', 0))}",
                f"Stability:  {self._format_decimal(stats.get('stability', 0))}%",
                f"Leader:     {stats.get('leader', 'Unknown')}",
            ]
            for line in lines:
                surface.blit(self.font.render(line, True, (212, 212, 212)), (content_rect.x, y_cursor))
                y_cursor += 20

            alreadyatwar = self._selectedmapcountry in self._countriesatwarset
            can_declare = (
                bool(self.playercountry)
                and self._selectedmapcountry != self.playercountry
                and not alreadyatwar
            )
            status = "At war" if alreadyatwar else ("Player country" if self._selectedmapcountry == self.playercountry else "Peace")
            status_surf = self.small_font.render(f"STATUS: {status.upper()}", True, _C_TEXT_MUTED)
            surface.blit(status_surf, (content_rect.x, y_cursor + 8))

            self._declarewar_rect.topleft = (content_rect.x, content_rect.bottom - self._declarewar_rect.height)
            declare_label = "DECLARE WAR" if can_declare else ("ALREADY AT WAR" if alreadyatwar else "DECLARE WAR")
            self._draw_glow_btn(
                surface,
                "declarewar_selected_country",
                self._declarewar_rect,
                can_declare,
                declare_label,
                mouse=mouse,
            )

        
        elif selected_tab == "TROOPS":
           
            self._recruit_action_rect.topleft = (content_rect.x, self._split_rect.y - 44)
            recruit_label = f"RECRUIT +{int(self.recruitamount)}"
            self._draw_glow_btn(
                surface, "recruit", self._recruit_action_rect,
                self.recruitenabled, recruit_label, primary=True, mouse=mouse,
            )
            y_cursor = max(y_cursor, content_rect.y + 24)

        elif selected_tab == "PRODUCTION" and not self._countrymenutarget:
            self._production_blank_rect.topleft = (content_rect.x, content_rect.y + 40)
            self._draw_glow_btn(
                surface, "production_blank", self._production_blank_rect,
                True, "     +      ", mouse=mouse,
            )
            y_cursor += 100

        # Troop info + decision buttons only show in TROOPS tab, and only when troops > 0
        if selected_tab == "TROOPS" and not self._countrymenutarget and self.active_left_tab != "COMBAT" and not self._selectedmapcountry:
            self._detach_regiment_rects = {}
            selected = [e for e in (self._selectedtroopentries or []) if isinstance(e, dict)]
            totaltroops = sum(max(0, int(e.get("troops", 0))) for e in selected)
            if totaltroops > 0:
                header_y = content_rect.y + 60
                divisionentry = self._get_selected_division_entry()
                divisionname = divisionentry.get("divisionname") if divisionentry else None
                divisionautoadvance = bool(divisionentry.get("divisionautoadvance", False)) if divisionentry else False

                icon = self._topbar_icons.get("manpower")
                if icon is not None:
                    surface.blit(icon, (content_rect.x, header_y - 2))
                    title_x = content_rect.x + icon.get_width() + 8
                else:
                    title_x = content_rect.x
                surface.blit(self.font_bold.render("Selected Regiments", True, _C_TEXT), (title_x, header_y))

                chip_gap = 8
                chip_w = (content_rect.width - chip_gap) // 2
                chip_y = header_y + 28
                self._draw_metric_chip(
                    surface,
                    pygame.Rect(content_rect.x, chip_y, chip_w, 48),
                    "Regiments",
                    str(len(selected)),
                    icon_key="combat",
                    accent=_C_INFO,
                )
                self._draw_metric_chip(
                    surface,
                    pygame.Rect(content_rect.x + chip_w + chip_gap, chip_y, chip_w, 48),
                    "Troops",
                    self._format_number(totaltroops),
                    icon_key="manpower",
                    accent=_C_SUCCESS,
                )

                division_y = chip_y + 58
                if divisionname:
                    division_rect = pygame.Rect(content_rect.x, division_y, content_rect.width, 44)
                    self._draw_vertical_gradient_rect(surface, division_rect, (26, 35, 52), (13, 20, 33), radius=6)
                    pygame.draw.rect(surface, (61, 75, 96), division_rect, 1, border_radius=6)
                    div_icon = self._topbar_icons.get("logistics")
                    div_x = division_rect.x + 10
                    if div_icon is not None:
                        surface.blit(div_icon, (div_x, division_rect.centery - div_icon.get_height() // 2))
                        div_x += div_icon.get_width() + 8
                    surface.blit(self.small_font.render("DIVISION", True, _C_TEXT_MUTED), (div_x, division_rect.y + 7))
                    surface.blit(self.font_bold.render(str(divisionname), True, _C_TEXT), (div_x, division_rect.y + 22))
                    status_text = "ADVANCE" if divisionautoadvance else "HOLD"
                    status_color = _C_SUCCESS if divisionautoadvance else _C_GOLD_BRIGHT
                    status_surface = self.small_font_bold.render(status_text, True, status_color)
                    surface.blit(
                        status_surface,
                        (
                            division_rect.right - status_surface.get_width() - 10,
                            division_rect.centery - status_surface.get_height() // 2,
                        ),
                    )
                    list_top = division_rect.bottom + 10
                else:
                    list_top = chip_y + 60

                list_bottom = min(self._recruit_action_rect.y, self._split_rect.y) - 10
                maxrows = max(0, (list_bottom - list_top) // 48)
                maxrows = min(7, maxrows)

                col_x = content_rect.x
                row_h = 44
                for i in range(maxrows):
                    if i >= len(selected):
                        break
                    row_rect = pygame.Rect(col_x, list_top + i * (row_h + 4), content_rect.width, row_h)
                    row_top = (23, 33, 50) if i % 2 == 0 else (18, 27, 42)
                    self._draw_vertical_gradient_rect(surface, row_rect, row_top, (10, 16, 27), radius=6)
                    pygame.draw.rect(surface, (43, 56, 73), row_rect, 1, border_radius=6)
                    pygame.draw.line(surface, _C_INFO, (row_rect.x + 5, row_rect.y + 8), (row_rect.x + 5, row_rect.bottom - 8), 2)

                    prov = selected[i].get("provinceid", "unknown")
                    troops = int(selected[i].get("troops", 0))
                    regiment_label = selected[i].get("regimentname") or f"Regiment {i + 1}"
                    label_x = row_rect.x + 16
                    label_y = row_rect.y + 6
                    regiment_surface = self.font_bold.render(str(regiment_label), True, _C_TEXT)
                    surface.blit(regiment_surface, (label_x, label_y))

                    rowdivisionid = selected[i].get("divisionid")
                    if rowdivisionid:
                        detachrect = pygame.Rect(label_x + regiment_surface.get_width() + 8, label_y - 1, 18, 18)
                        self._detach_regiment_rects[str(prov)] = detachrect
                        pygame.draw.rect(surface, _C_DANGER, detachrect, border_radius=4)
                        pygame.draw.line(surface, (255, 235, 235), (detachrect.x + 5, detachrect.y + 5), (detachrect.right - 5, detachrect.bottom - 5), 2)
                        pygame.draw.line(surface, (255, 235, 235), (detachrect.right - 5, detachrect.y + 5), (detachrect.x + 5, detachrect.bottom - 5), 2)

                    prov_str = self.small_font.render(str(prov), True, _C_TEXT_MUTED)
                    surface.blit(prov_str, (label_x, row_rect.y + 25))

                    troop_str = self.font_bold.render(f"{troops:,}", True, (200, 232, 204))
                    surface.blit(troop_str,
                        (content_rect.right - troop_str.get_width() - 8, row_rect.y + 8))
                    troop_label = self.small_font.render("troops", True, _C_TEXT_MUTED)
                    surface.blit(troop_label, (content_rect.right - troop_label.get_width() - 8, row_rect.y + 26))

                if len(selected) > maxrows and maxrows > 0:
                    overflow = len(selected) - maxrows
                    surface.blit(self.font.render(f"... +{overflow} more", True, (170, 170, 170)),
                        (col_x, list_top + (maxrows - 1) * (row_h + 4) + row_h + 2))

                split_enabled = totaltroops > 1
                merge_enabled = len(selected) > 1
                hasdivision = divisionentry is not None
                frontline_label = "Cancel" if self._frontlineplacementmode else "Line"
                advance_label = "Auto"
                self._draw_glow_btn(surface, "split", self._split_rect, split_enabled, "Split", mouse=mouse, icon_key="manpower")
                self._draw_glow_btn(surface, "merge", self._merge_rect, merge_enabled, "Merge", mouse=mouse, icon_key="logistics")
                self._draw_glow_btn(
                    surface,
                    "frontline",
                    self._frontline_rect,
                    True,
                    frontline_label,
                    selected=self._frontlineplacementmode,
                    mouse=mouse,
                    icon_key="combat",
                )
                self._draw_glow_btn(
                    surface,
                    "autoadvance",
                    self._auto_advance_rect,
                    hasdivision,
                    advance_label,
                    primary=divisionautoadvance,
                    selected=divisionautoadvance,
                    mouse=mouse,
                    icon_key="turn",
                )
        else:
            self._detach_regiment_rects = {}

        self._draw_topbar_metric_popup(surface, mouse)
        self._draw_notification_popup(surface, mouse)
        self._draw_combat_popup(surface, mouse)
        self._draw_policy_popup(surface, mouse)

        if self.warprogressopen:
            self._draw_war_progress_popup(surface, mouse)
        if self.domesticaffairsopen:
            self._draw_domestic_affairs_popup(surface, mouse)

        if self.pausemenuopen:
            self._draw_pausemenu(surface)
        self._ui_pulses.draw(surface)


    def _draw_metric_chip(self, surface, rect, label, value, icon_key=None, accent=_C_GOLD):
        self._draw_vertical_gradient_rect(surface, rect, (18, 27, 42), (9, 15, 24), radius=6)
        pygame.draw.rect(surface, (49, 63, 82), rect, 1, border_radius=6)
        pygame.draw.line(surface, accent, (rect.x + 8, rect.y + 9), (rect.x + 8, rect.bottom - 9), 2)
        draw_x = rect.x + 18
        icon = self._topbar_icons.get(icon_key) if icon_key else None
        if icon is not None:
            surface.blit(icon, (draw_x, rect.centery - icon.get_height() // 2))
            draw_x += icon.get_width() + 10
        value_surface = self.font_bold.render(str(value), True, _C_TEXT)
        label_surface = self.small_font.render(str(label), True, _C_TEXT_MUTED)
        text_gap = 2
        text_block_h = value_surface.get_height() + text_gap + label_surface.get_height()
        text_y = rect.y + max(7, (rect.height - text_block_h) // 2)
        surface.blit(value_surface, (draw_x, text_y))
        surface.blit(label_surface, (draw_x, text_y + value_surface.get_height() + text_gap))

    def _draw_occupation_bar(self, surface, rect, label, percent, count_text, fill_color):
        percent = max(0.0, min(100.0, float(percent or 0.0)))
        label_surface = self.font_bold.render(str(label), True, _C_TEXT)
        value_surface = self.font_bold.render(f"{percent:.1f}%", True, _C_TEXT)
        surface.blit(label_surface, (rect.x, rect.y))
        surface.blit(value_surface, (rect.right - value_surface.get_width(), rect.y))

        bar_rect = pygame.Rect(rect.x, rect.y + 28, rect.width, 24)
        pygame.draw.rect(surface, (7, 12, 20), bar_rect, border_radius=5)
        pygame.draw.rect(surface, (43, 56, 73), bar_rect, 1, border_radius=5)

        fill_width = int(bar_rect.width * (percent / 100.0))
        if fill_width > 0:
            fill_rect = pygame.Rect(bar_rect.x, bar_rect.y, fill_width, bar_rect.height)
            self._draw_vertical_gradient_rect(surface, fill_rect, fill_color, (max(0, fill_color[0] - 32), max(0, fill_color[1] - 32), max(0, fill_color[2] - 32)), radius=5)

        risk_x = bar_rect.x + int(bar_rect.width * 0.8)
        pygame.draw.line(surface, _C_DANGER, (risk_x, bar_rect.y - 4), (risk_x, bar_rect.bottom + 4), 2)
        risk_label = self.small_font.render("80% capitulation risk", True, _C_DANGER)
        surface.blit(risk_label, (bar_rect.right - risk_label.get_width(), bar_rect.bottom + 6))

        count_surface = self.small_font.render(str(count_text), True, _C_TEXT_MUTED)
        surface.blit(count_surface, (rect.x, bar_rect.bottom + 6))

    @staticmethod
    def _parse_ui_color(value, fallback=(132, 145, 160)):
        if isinstance(value, (tuple, list)) and len(value) >= 3:
            try:
                return tuple(max(0, min(255, int(component))) for component in value[:3])
            except (TypeError, ValueError):
                return fallback
        text = str(value or "").strip()
        if text.startswith("#") and len(text) == 7:
            try:
                return tuple(int(text[index:index + 2], 16) for index in (1, 3, 5))
            except ValueError:
                return fallback
        return fallback

    def _draw_value_bar(self, surface, rect, label, value, accent=_C_GOLD, suffix="%"):
        try:
            numeric = max(0.0, min(100.0, float(value or 0.0)))
        except (TypeError, ValueError):
            numeric = 0.0
        self._draw_text_fit(surface, label, _C_TEXT_MUTED, rect.x, rect.y, rect.width - 64, self.small_font_bold)
        value_text = f"{numeric:.0f}{suffix}"
        value_surface = self.small_font_bold.render(value_text, True, _C_TEXT)
        surface.blit(value_surface, (rect.right - value_surface.get_width(), rect.y))
        bar_rect = pygame.Rect(rect.x, rect.y + 18, rect.width, 9)
        pygame.draw.rect(surface, (7, 12, 20), bar_rect, border_radius=4)
        pygame.draw.rect(surface, (43, 56, 73), bar_rect, 1, border_radius=4)
        fill_rect = bar_rect.copy()
        fill_rect.width = int(bar_rect.width * numeric / 100.0)
        if fill_rect.width > 0:
            self._draw_vertical_gradient_rect(surface, fill_rect, accent, tuple(max(0, channel - 42) for channel in accent), radius=4)

    def _draw_domestic_info_row(self, surface, x, y, label, value, width):
        label_w = min(156, max(96, int(width * 0.38)))
        self._draw_text_fit(surface, str(label).upper(), _C_TEXT_MUTED, x, y, label_w, self.small_font_bold)
        self._draw_text_fit(surface, value, _C_TEXT, x + label_w + 10, y - 1, max(20, width - label_w - 10), self.font_bold)

    def _get_domestic_segment_at_pos(self, pos):
        mx, my = pos
        for segment in self._domestic_segment_hitboxes or ():
            cx, cy = segment.get("center", (0, 0))
            dx = mx - cx
            dy = my - cy
            distance = math.hypot(dx, dy)
            if distance < segment.get("inner_radius", 0) or distance > segment.get("outer_radius", 0):
                continue
            angle = math.atan2(dy, dx)
            if angle < 0:
                angle += math.tau
            if angle < math.pi:
                angle += math.tau
            if segment.get("start_angle", 0) <= angle <= segment.get("end_angle", 0):
                return segment.get("party")
        return None

    def _draw_domestic_affairs_popup(self, surface, mouse):
        popup_w = min(980, max(700, self.map_rect.width - 48))
        max_popup_h = max(540, surface.get_height() - self.topbar_height - 36)
        popup_h = min(760, max_popup_h, max(620, self.map_rect.height - 52))
        popup_rect = pygame.Rect(0, 0, popup_w, popup_h)
        if self._domestic_popup_pos is None:
            popup_rect.center = self.map_rect.center
        else:
            popup_rect.topleft = self._domestic_popup_pos
        popup_rect.clamp_ip(surface.get_rect().inflate(-32, -32))
        self._domestic_popup_pos = popup_rect.topleft
        self._domestic_popup_rect = popup_rect

        shadow = pygame.Surface((popup_rect.width + 28, popup_rect.height + 28), pygame.SRCALPHA)
        pygame.draw.rect(shadow, (0, 0, 0, 154), shadow.get_rect(), border_radius=12)
        surface.blit(shadow, (popup_rect.x - 14, popup_rect.y - 10))
        self._draw_glass_panel(surface, popup_rect, radius=8, border=(92, 74, 42), glow=True)

        header_h = 64
        self._domestic_header_rect = pygame.Rect(popup_rect.x, popup_rect.y, popup_rect.width, header_h)
        pygame.draw.line(surface, (76, 64, 38), (popup_rect.x + 16, popup_rect.y + header_h), (popup_rect.right - 16, popup_rect.y + header_h), 1)

        icon = self._topbar_icons.get("domestic_affairs")
        title_x = popup_rect.x + 24
        if icon is not None:
            surface.blit(icon, (title_x, popup_rect.y + 21))
            title_x += icon.get_width() + 12
        title = self.title_font.render("DOMESTIC AFFAIRS", True, _C_GOLD_BRIGHT)
        data = self._domesticaffairsdata or {}
        subtitle_text = data.get("country_name") or data.get("country_id") or "No country selected"
        subtitle = self.small_font.render(str(subtitle_text).upper(), True, _C_TEXT_MUTED)
        surface.blit(title, (title_x, popup_rect.y + 14))
        surface.blit(subtitle, (title_x, popup_rect.y + 40))

        close_size = 34
        self._domestic_close_rect = pygame.Rect(popup_rect.right - close_size - 16, popup_rect.y + 15, close_size, close_size)
        close_hovered = self._domestic_close_rect.collidepoint(mouse)
        close_top = (45, 55, 68) if close_hovered else (23, 32, 48)
        self._draw_vertical_gradient_rect(surface, self._domestic_close_rect, close_top, (10, 16, 25), radius=6)
        pygame.draw.rect(surface, (_C_DANGER if close_hovered else (62, 76, 95)), self._domestic_close_rect, 1, border_radius=6)
        close_icon = self._topbar_icons.get("close")
        if close_icon is not None:
            surface.blit(close_icon, close_icon.get_rect(center=self._domestic_close_rect.center))
        else:
            close_label = self.font_bold.render("X", True, _C_TEXT)
            surface.blit(close_label, close_label.get_rect(center=self._domestic_close_rect.center))

        content_rect = pygame.Rect(popup_rect.x + 28, popup_rect.y + header_h + 18, popup_rect.width - 56, popup_rect.height - header_h - 38)
        self._domestic_tab_rects = {}
        tabs = ("Executive", "Economy", "Internal Policies", "Health")
        gap = 8
        tab_w = min(190, max(132, (content_rect.width - gap * (len(tabs) - 1)) // len(tabs)))
        tab_y = content_rect.y
        for index, tab_name in enumerate(tabs):
            tab_rect = pygame.Rect(content_rect.x + index * (tab_w + gap), tab_y, tab_w, 38)
            self._domestic_tab_rects[tab_name] = tab_rect
            selected = self._domestic_active_tab == tab_name
            hovered = tab_rect.collidepoint(mouse)
            top = (43, 36, 24) if selected else ((28, 39, 59) if hovered else (14, 22, 33))
            bottom = (25, 22, 18) if selected else (9, 15, 24)
            self._draw_vertical_gradient_rect(surface, tab_rect, top, bottom, radius=6)
            pygame.draw.rect(surface, (_C_GOLD if selected else (46, 59, 78)), tab_rect, 1, border_radius=6)
            self._draw_text_fit(surface, tab_name, (_C_GOLD_BRIGHT if selected else _C_TEXT), tab_rect.x + 12, tab_rect.y + 10, tab_rect.width - 24, self.font_bold if selected else self.font)

        body_rect = pygame.Rect(content_rect.x, tab_y + 52, content_rect.width, content_rect.height - 52)
        if not data:
            self._domestic_segment_hitboxes = []
            empty = self.font_bold.render("No domestic affairs data loaded.", True, _C_TEXT)
            surface.blit(empty, empty.get_rect(center=(body_rect.centerx, body_rect.y + 120)))
            return

        if self._domestic_active_tab not in tabs:
            self._domestic_active_tab = "Executive"
        if self._domestic_active_tab == "Economy":
            self._draw_domestic_economy_tab(surface, body_rect, data, mouse)
        elif self._domestic_active_tab == "Internal Policies":
            self._draw_domestic_internal_policies_tab(surface, body_rect, data, mouse)
        elif self._domestic_active_tab == "Health":
            self._draw_domestic_health_tab(surface, body_rect, data, mouse)
        else:
            self._draw_domestic_executive_tab(surface, body_rect, data, mouse)

        hovered_party = self._get_domestic_segment_at_pos(mouse)
        if hovered_party is not None:
            self._draw_domestic_party_tooltip(surface, mouse, hovered_party)

    def _draw_domestic_executive_tab(self, surface, rect, data, mouse):
        self._domestic_segment_hitboxes = []
        left_w = min(540, max(390, int(rect.width * 0.58)))
        gap = 14
        left_rect = pygame.Rect(rect.x, rect.y, left_w, rect.height)
        right_rect = pygame.Rect(left_rect.right + gap, rect.y, rect.width - left_w - gap, rect.height)

        summary_rect = pygame.Rect(left_rect.x, left_rect.y, left_rect.width, 146)
        self._draw_vertical_gradient_rect(surface, summary_rect, (16, 26, 41), (8, 13, 22), radius=6)
        pygame.draw.rect(surface, (52, 65, 82), summary_rect, 1, border_radius=6)

        flag_key = str(data.get("country_id") or data.get("country_name") or "").strip().lower().replace(" ", "_").replace("-", "_")
        flag = self._flags.get(flag_key)
        draw_x = summary_rect.x + 14
        if flag is not None:
            scaled_flag = pygame.transform.smoothscale(flag, (76, 48))
            surface.blit(scaled_flag, (draw_x, summary_rect.y + 16))
            draw_x += 92
        leader_name = data.get("current_prime_minister") or data.get("head_of_government")
        portrait_key = self._portrait_key(leader_name)
        portrait = self._leaderportraits.get(portrait_key)
        portrait_reserved = 0
        if portrait is not None and summary_rect.width >= 420:
            portrait_rect = pygame.Rect(summary_rect.right - 68, summary_rect.y + 14, 50, 70)
            self._draw_vertical_gradient_rect(surface, portrait_rect.inflate(4, 4), (41, 49, 60), (9, 15, 24), radius=5)
            portrait_img = pygame.transform.smoothscale(portrait, portrait_rect.size)
            surface.blit(portrait_img, portrait_rect)
            pygame.draw.rect(surface, _C_GOLD, portrait_rect, 1, border_radius=4)
            portrait_reserved = 84
        text_w = summary_rect.right - draw_x - 12 - portrait_reserved
        self._draw_text_fit(surface, data.get("country_name", "Unknown"), _C_TEXT, draw_x, summary_rect.y + 12, text_w, self.title_font)
        self._draw_text_fit(surface, data.get("government_system", ""), _C_TEXT_MUTED, draw_x, summary_rect.y + 42, text_w, self.small_font)
        self._draw_domestic_info_row(surface, draw_x, summary_rect.y + 68, data.get("head_of_state_title", "Head of state"), data.get("head_of_state", "Unknown"), text_w)
        pm_title = "Interim Prime Minister" if data.get("interim_prime_minister") else data.get("head_of_government_title", "Government")
        self._draw_domestic_info_row(surface, draw_x, summary_rect.y + 92, pm_title, leader_name or "Unknown", text_w)
        self._draw_domestic_info_row(surface, draw_x, summary_rect.y + 116, "Coalition", data.get("ruling_coalition", data.get("current_ruling_bloc", "Unknown")), text_w)

        chart_rect = pygame.Rect(left_rect.x, summary_rect.bottom + 14, left_rect.width, min(250, max(212, rect.height // 2)))
        self._draw_legislature_chart(surface, chart_rect, data, mouse)

        legend_rect = pygame.Rect(left_rect.x, chart_rect.bottom + 12, left_rect.width, max(96, rect.bottom - chart_rect.bottom - 12))
        self._draw_domestic_legend(surface, legend_rect, data)

        metrics_rect = pygame.Rect(right_rect.x, right_rect.y, right_rect.width, min(242, rect.height))
        self._draw_vertical_gradient_rect(surface, metrics_rect, (16, 26, 41), (8, 13, 22), radius=6)
        pygame.draw.rect(surface, (52, 65, 82), metrics_rect, 1, border_radius=6)
        y = metrics_rect.y + 14
        self._draw_text_fit(surface, "EXECUTIVE CONTROL", _C_GOLD_BRIGHT, metrics_rect.x + 14, y, metrics_rect.width - 28, self.font_bold)
        y += 28
        rows = (
            ("Ruling coalition", data.get("ruling_coalition", data.get("current_ruling_bloc", "Unknown"))),
            ("Government status", data.get("government_status", data.get("legislature_status", "Unknown"))),
            ("Crisis risk", data.get("political_crisis_risk", data.get("no_confidence_risk", "Unknown"))),
            ("Succession tension", f"{float(data.get('succession_tension', 0) or 0):.0f}%"),
            ("Legislature", data.get("legislature_name", "Unknown")),
            ("Lower house", data.get("main_chamber_name", data.get("lower_house_name", "Unknown"))),
            ("Total seats", self._format_number(data.get("total_seats", 0))),
            ("Majority", self._format_number(data.get("majority_needed", 0))),
            ("Government", self._format_number(data.get("government_seats", 0))),
            ("Opposition", self._format_number(data.get("opposition_seats", 0))),
        )
        for label, value in rows:
            self._draw_domestic_info_row(surface, metrics_rect.x + 14, y, label, value, metrics_rect.width - 28)
            y += 18

        bars_y = metrics_rect.bottom + 10
        bars_rect = pygame.Rect(right_rect.x, bars_y, right_rect.width, 112)
        if bars_rect.bottom <= rect.bottom:
            self._draw_vertical_gradient_rect(surface, bars_rect, (14, 23, 36), (8, 13, 22), radius=6)
            pygame.draw.rect(surface, (52, 65, 82), bars_rect, 1, border_radius=6)
            bar_x = bars_rect.x + 14
            bar_w = bars_rect.width - 28
            self._draw_value_bar(surface, pygame.Rect(bar_x, bars_rect.y + 8, bar_w, 30), "Political stability", data.get("government_stability", 0), _C_SUCCESS)
            self._draw_value_bar(surface, pygame.Rect(bar_x, bars_rect.y + 42, bar_w, 30), "Public approval", data.get("public_approval", 0), _C_INFO)
            self._draw_value_bar(surface, pygame.Rect(bar_x, bars_rect.y + 76, bar_w, 30), "Corruption level", data.get("corruption_level", 0), _C_DANGER)

        panel_y = (bars_rect.bottom + 10) if bars_rect.bottom <= rect.bottom else (metrics_rect.bottom + 10)
        panel_rect = pygame.Rect(right_rect.x, panel_y, right_rect.width, max(96, rect.bottom - panel_y))
        if panel_rect.height > 40:
            selected_party = None
            for party in data.get("chart_parties", ()):
                if party.get("party_id") == self._domestic_selected_party_id:
                    selected_party = party
                    break
            if selected_party is not None:
                self._draw_domestic_party_panel(surface, panel_rect, selected_party)
            else:
                self._draw_domestic_warning_panel(surface, panel_rect, data)

    def _draw_legislature_chart(self, surface, rect, data, mouse):
        self._draw_vertical_gradient_rect(surface, rect, (13, 21, 34), (7, 12, 20), radius=6)
        pygame.draw.rect(surface, (52, 65, 82), rect, 1, border_radius=6)
        self._draw_text_fit(surface, data.get("main_chamber_name", data.get("lower_house_name", "Legislature")), _C_GOLD_BRIGHT, rect.x + 14, rect.y + 10, rect.width - 28, self.font_bold)

        parties = [party for party in data.get("chart_parties", ()) if int(party.get("seat_count", 0) or 0) > 0]
        total_seats = max(1, int(data.get("total_seats", 0) or sum(int(p.get("seat_count", 0) or 0) for p in parties) or 1))
        center = (rect.centerx, rect.bottom - 20)
        outer_radius = max(70, min(rect.width // 2 - 24, rect.height - 58))
        inner_radius = max(44, int(outer_radius * 0.52))
        start_angle = math.pi
        segments = []
        for party in parties:
            seats = max(0, int(party.get("seat_count", 0) or 0))
            sweep = math.pi * seats / total_seats
            end_angle = start_angle + sweep
            segments.append({
                "party": party,
                "party_id": party.get("party_id"),
                "center": center,
                "inner_radius": inner_radius,
                "outer_radius": outer_radius,
                "start_angle": start_angle,
                "end_angle": end_angle,
            })
            start_angle = end_angle
        self._domestic_segment_hitboxes = segments
        hovered_party = self._get_domestic_segment_at_pos(mouse)
        hovered_id = hovered_party.get("party_id") if hovered_party else None

        for segment in segments:
            party = segment["party"]
            points = []
            sweep = max(0.003, segment["end_angle"] - segment["start_angle"])
            steps = max(4, int(28 * sweep / math.pi))
            for step in range(steps + 1):
                angle = segment["start_angle"] + sweep * step / steps
                points.append((
                    int(center[0] + math.cos(angle) * outer_radius),
                    int(center[1] + math.sin(angle) * outer_radius),
                ))
            for step in range(steps, -1, -1):
                angle = segment["start_angle"] + sweep * step / steps
                points.append((
                    int(center[0] + math.cos(angle) * inner_radius),
                    int(center[1] + math.sin(angle) * inner_radius),
                ))
            color = self._parse_ui_color(party.get("color"), _C_STEEL)
            pygame.draw.polygon(surface, color, points)
            border = _C_GOLD_BRIGHT if hovered_id == party.get("party_id") or self._domestic_selected_party_id == party.get("party_id") else (11, 18, 32)
            pygame.draw.polygon(surface, border, points, 2 if border == _C_GOLD_BRIGHT else 1)

        self._draw_legislature_side_brackets(surface, rect, center, outer_radius, segments)

        majority = max(1, int(data.get("majority_needed", 1) or 1))
        marker_angle = math.pi + min(1.0, majority / total_seats) * math.pi
        inner_point = (
            int(center[0] + math.cos(marker_angle) * (inner_radius - 8)),
            int(center[1] + math.sin(marker_angle) * (inner_radius - 8)),
        )
        outer_point = (
            int(center[0] + math.cos(marker_angle) * (outer_radius + 10)),
            int(center[1] + math.sin(marker_angle) * (outer_radius + 10)),
        )
        pygame.draw.line(surface, _C_GOLD_BRIGHT, inner_point, outer_point, 2)
        majority_label = self.small_font_bold.render(str(majority), True, _C_GOLD_BRIGHT)
        surface.blit(majority_label, (outer_point[0] - majority_label.get_width() // 2, outer_point[1] - 18))

        total_surface = self.title_font.render(self._format_number(total_seats), True, _C_TEXT)
        total_label = self.small_font.render("SEATS", True, _C_TEXT_MUTED)
        surface.blit(total_surface, total_surface.get_rect(center=(center[0], center[1] - 35)))
        surface.blit(total_label, total_label.get_rect(center=(center[0], center[1] - 12)))
        status = data.get("legislature_status", "")
        status_surface = self.small_font_bold.render(str(status).upper(), True, _C_GOLD_BRIGHT)
        surface.blit(status_surface, status_surface.get_rect(center=(center[0], rect.bottom - 10)))

    def _draw_legislature_side_brackets(self, surface, rect, center, outer_radius, segments):
        groups = []
        for segment in segments:
            side = str(segment.get("party", {}).get("status", "neutral"))
            seats = int(segment.get("party", {}).get("seat_count", 0) or 0)
            if groups and groups[-1]["side"] == side:
                groups[-1]["end_angle"] = segment["end_angle"]
                groups[-1]["seats"] += seats
            else:
                groups.append({
                    "side": side,
                    "start_angle": segment["start_angle"],
                    "end_angle": segment["end_angle"],
                    "seats": seats,
                })

        colors = {
            "government": _C_GOLD_BRIGHT,
            "opposition": (210, 104, 104),
            "neutral": (150, 162, 176),
            "military": (132, 145, 160),
            "appointed": (132, 145, 160),
        }
        labels = {
            "government": "Government",
            "opposition": "Opposition",
        }
        bracket_radius = outer_radius + 13
        arc_rect = pygame.Rect(0, 0, bracket_radius * 2, bracket_radius * 2)
        arc_rect.center = center
        for group in groups:
            side = group["side"]
            if side not in labels:
                continue
            start_angle = group["start_angle"] + 0.012
            end_angle = group["end_angle"] - 0.012
            if end_angle <= start_angle:
                continue
            color = colors.get(side, _C_TEXT_MUTED)
            pygame.draw.arc(surface, color, arc_rect, start_angle, end_angle, 3)
            for angle in (start_angle, end_angle):
                outer_point = (
                    int(center[0] + math.cos(angle) * (bracket_radius + 4)),
                    int(center[1] + math.sin(angle) * (bracket_radius + 4)),
                )
                inner_point = (
                    int(center[0] + math.cos(angle) * (bracket_radius - 9)),
                    int(center[1] + math.sin(angle) * (bracket_radius - 9)),
                )
                pygame.draw.line(surface, color, inner_point, outer_point, 3)

            label = f"{labels[side]} {group['seats']}"
            text = self.small_font_bold.render(label, True, color)
            mid_angle = (start_angle + end_angle) * 0.5
            label_x = int(center[0] + math.cos(mid_angle) * (bracket_radius + 28) - text.get_width() / 2)
            label_y = int(center[1] + math.sin(mid_angle) * (bracket_radius + 28) - text.get_height() / 2)
            label_x = max(rect.x + 8, min(rect.right - text.get_width() - 8, label_x))
            label_y = max(rect.y + 32, min(rect.bottom - text.get_height() - 26, label_y))
            label_bg = pygame.Rect(label_x - 5, label_y - 3, text.get_width() + 10, text.get_height() + 6)
            pygame.draw.rect(surface, (7, 12, 20), label_bg, border_radius=4)
            pygame.draw.rect(surface, color, label_bg, 1, border_radius=4)
            surface.blit(text, (label_x, label_y))

    def _draw_domestic_legend(self, surface, rect, data):
        self._draw_vertical_gradient_rect(surface, rect, (13, 21, 34), (7, 12, 20), radius=6)
        pygame.draw.rect(surface, (52, 65, 82), rect, 1, border_radius=6)
        self._draw_text_fit(surface, "LEGISLATURE", _C_GOLD_BRIGHT, rect.x + 14, rect.y + 10, rect.width - 28, self.font_bold)
        parties = list(data.get("chart_parties", ()))
        row_h = 34
        y = rect.y + 38
        max_rows = max(0, (rect.bottom - y - 8) // row_h)
        for party in parties[:max_rows]:
            seats = max(0, int(party.get("seat_count", 0) or 0))
            color = self._parse_ui_color(party.get("color"), _C_STEEL)
            row_rect = pygame.Rect(rect.x + 10, y, rect.width - 20, row_h - 5)
            hovered = self._domestic_selected_party_id == party.get("party_id")
            self._draw_vertical_gradient_rect(surface, row_rect, (20, 30, 46) if hovered else (14, 22, 34), (8, 13, 22), radius=5)
            pygame.draw.rect(surface, _C_GOLD if hovered else (40, 52, 69), row_rect, 1, border_radius=5)
            swatch = pygame.Rect(row_rect.x + 8, row_rect.y + 8, 14, 14)
            pygame.draw.rect(surface, color, swatch, border_radius=3)
            pygame.draw.rect(surface, (9, 15, 24), swatch, 1, border_radius=3)
            text_x = swatch.right + 8
            name = f"{party.get('short_name', party.get('party_name', '?'))} - {seats} seats ({party.get('seat_percent', 0)}%)"
            self._draw_text_fit(surface, name, _C_TEXT, text_x, row_rect.y + 3, row_rect.width - 168, self.small_font_bold)
            detail = f"{party.get('status', 'neutral').title()} | {party.get('leader_name', 'Unknown')} | {party.get('ideology', 'Unknown')}"
            self._draw_text_fit(surface, detail, _C_TEXT_MUTED, text_x, row_rect.y + 17, row_rect.width - 28, self.small_font)
            y += row_h
        if len(parties) > max_rows:
            self._draw_text_fit(surface, f"+{len(parties) - max_rows} more blocs", _C_TEXT_MUTED, rect.x + 14, rect.bottom - 22, rect.width - 28, self.small_font)

    def _draw_domestic_warning_panel(self, surface, rect, data):
        self._draw_vertical_gradient_rect(surface, rect, (14, 23, 36), (8, 13, 22), radius=6)
        pygame.draw.rect(surface, (52, 65, 82), rect, 1, border_radius=6)
        self._draw_text_fit(surface, "POLITICAL WARNINGS", _C_GOLD_BRIGHT, rect.x + 14, rect.y + 12, rect.width - 28, self.font_bold)
        y = rect.y + 42
        warnings = list(data.get("warnings", ()))
        if not warnings:
            warnings = ["No immediate domestic crisis."]
        max_warning_rows = max(1, (rect.bottom - y - 8) // 20)
        for warning in warnings[:max_warning_rows]:
            color = _C_DANGER if "lost" in warning.lower() or "risk" in warning.lower() else _C_TEXT
            self._draw_text_fit(surface, warning, color, rect.x + 14, y, rect.width - 28, self.small_font_bold if color == _C_DANGER else self.small_font)
            y += 20
        mechanics = data.get("special_mechanics", ())
        if y + 42 < rect.bottom and mechanics:
            self._draw_text_fit(surface, "SPECIAL MECHANICS", _C_GOLD_BRIGHT, rect.x + 14, y + 6, rect.width - 28, self.small_font_bold)
            y += 28
            for mechanic in mechanics[:4]:
                self._draw_text_fit(surface, mechanic, _C_TEXT_MUTED, rect.x + 14, y, rect.width - 28, self.small_font)
                y += 18

    def _draw_domestic_party_panel(self, surface, rect, party):
        color = self._parse_ui_color(party.get("color"), _C_GOLD)
        self._draw_vertical_gradient_rect(surface, rect, (14, 23, 36), (8, 13, 22), radius=6)
        pygame.draw.rect(surface, color, rect, 1, border_radius=6)
        pygame.draw.line(surface, color, (rect.x + 8, rect.y + 10), (rect.x + 8, rect.bottom - 10), 3)
        self._draw_text_fit(surface, party.get("party_name", "Unknown party"), _C_TEXT, rect.x + 18, rect.y + 12, rect.width - 32, self.font_bold)
        y = rect.y + 42
        rows = (
            ("Short name", party.get("short_name", "")),
            ("Leader", party.get("leader_name", "Unknown")),
            ("Coalition", party.get("coalition", "None")),
            ("Status", party.get("status", "neutral").title()),
            ("Ideology", party.get("ideology", "Unknown")),
            ("Seats", self._format_number(party.get("seat_count", 0))),
            ("Vote share", f"{float(party.get('vote_share', 0) or 0):.1f}%"),
            ("Loyalty", f"{float(party.get('loyalty_to_government', 0) or 0):.0f}%"),
            ("Defection risk", f"{float(party.get('defection_risk', 0) or 0):.0f}%"),
        )
        for label, value in rows:
            if y + 18 > rect.bottom - 8:
                break
            self._draw_domestic_info_row(surface, rect.x + 18, y, label, value, rect.width - 36)
            y += 22

    def _draw_domestic_party_tooltip(self, surface, mouse, party):
        lines = [
            str(party.get("party_name", "Unknown party")),
            f"Coalition: {party.get('coalition', 'None')}",
            f"Seats: {self._format_number(party.get('seat_count', 0))}",
            f"Vote share: {float(party.get('vote_share', 0) or 0):.1f}%",
            f"Leader: {party.get('leader_name', 'Unknown')}",
            f"Status: {party.get('status', 'neutral').title()}",
            f"Loyalty: {float(party.get('loyalty_to_government', 0) or 0):.0f}%",
            f"Defection risk: {float(party.get('defection_risk', 0) or 0):.0f}%",
        ]
        text_surfs = []
        for index, line in enumerate(lines):
            font = self.small_font_bold if index == 0 else self.small_font
            color = _C_GOLD_BRIGHT if index == 0 else _C_TEXT
            text_surfs.append(font.render(line, True, color))
        padding = 10
        width = max(text.get_width() for text in text_surfs) + padding * 2
        height = sum(text.get_height() for text in text_surfs) + padding * 2 + 3
        x = min(self.window_size[0] - width - 8, mouse[0] + 16)
        y = min(self.window_size[1] - height - 8, mouse[1] + 16)
        tooltip_rect = pygame.Rect(max(8, x), max(8, y), width, height)
        self._draw_glass_panel(surface, tooltip_rect, radius=5, border=(126, 102, 58), glow=False)
        draw_y = tooltip_rect.y + padding
        for text in text_surfs:
            surface.blit(text, (tooltip_rect.x + padding, draw_y))
            draw_y += text.get_height()

    def _draw_domestic_economy_tab(self, surface, rect, data, mouse):
        effects = data.get("economy_effects", {}) if isinstance(data.get("economy_effects", {}), dict) else {}
        chip_gap = 10
        chip_w = (rect.width - chip_gap * 2) // 3
        self._draw_metric_chip(surface, pygame.Rect(rect.x, rect.y, chip_w, 58), "Investor confidence", f"{float(effects.get('investor_confidence', 0) or 0):.0f}%", icon_key="gold", accent=_C_GOLD)
        self._draw_metric_chip(surface, pygame.Rect(rect.x + chip_w + chip_gap, rect.y, chip_w, 58), "Currency stability", f"{float(effects.get('currency_stability', 0) or 0):.0f}%", icon_key="trade", accent=_C_INFO)
        self._draw_metric_chip(surface, pygame.Rect(rect.x + (chip_w + chip_gap) * 2, rect.y, chip_w, 58), "Policy chance", f"{int(data.get('policy_passing_chance', 0) or 0)}%", icon_key="political_power", accent=_C_SUCCESS)

        body_y = rect.y + 78
        left_rect = pygame.Rect(rect.x, body_y, rect.width // 2 - 7, rect.bottom - body_y)
        right_rect = pygame.Rect(left_rect.right + 14, body_y, rect.width - left_rect.width - 14, rect.bottom - body_y)
        self._draw_vertical_gradient_rect(surface, left_rect, (15, 24, 38), (8, 13, 22), radius=6)
        pygame.draw.rect(surface, (52, 65, 82), left_rect, 1, border_radius=6)
        self._draw_text_fit(surface, "ECONOMIC LINK", _C_GOLD_BRIGHT, left_rect.x + 14, left_rect.y + 12, left_rect.width - 28, self.font_bold)
        y = left_rect.y + 44
        rows = (
            ("Budget", effects.get("budget_passing", "Unknown")),
            ("Projects", effects.get("project_speed", "Normal")),
            ("Election rule", data.get("election_system", "Unknown")),
            ("Next election", str(data.get("next_election_year", "Unknown"))),
        )
        for label, value in rows:
            self._draw_domestic_info_row(surface, left_rect.x + 14, y, label, value, left_rect.width - 28)
            y += 42 if label == "Budget" else 24

        self._draw_vertical_gradient_rect(surface, right_rect, (15, 24, 38), (8, 13, 22), radius=6)
        pygame.draw.rect(surface, (52, 65, 82), right_rect, 1, border_radius=6)
        self._draw_text_fit(surface, "ELECTION OUTCOMES", _C_GOLD_BRIGHT, right_rect.x + 14, right_rect.y + 12, right_rect.width - 28, self.font_bold)
        outcome_lines = [
            "Stable result: investor confidence and currency stability improve.",
            "Disputed result: protest risk and corruption risk rise.",
            "Landslide: reforms pass faster, but checks can weaken.",
            "Hung parliament: budgets slow and investor confidence drops.",
        ]
        y = right_rect.y + 44
        for line in outcome_lines:
            self._draw_text_fit(surface, line, _C_TEXT, right_rect.x + 14, y, right_rect.width - 28, self.small_font)
            y += 25
        self._draw_value_bar(surface, pygame.Rect(right_rect.x + 14, right_rect.bottom - 48, right_rect.width - 28, 32), "Coalition loyalty", data.get("coalition_loyalty", 0), _C_GOLD)

    def _draw_domestic_internal_policies_tab(self, surface, rect, data, mouse):
        effects = data.get("internal_policy_effects", {}) if isinstance(data.get("internal_policy_effects", {}), dict) else {}
        top_h = 142
        top_rect = pygame.Rect(rect.x, rect.y, rect.width, top_h)
        self._draw_vertical_gradient_rect(surface, top_rect, (15, 24, 38), (8, 13, 22), radius=6)
        pygame.draw.rect(surface, (52, 65, 82), top_rect, 1, border_radius=6)
        bar_gap = 18
        bar_w = (top_rect.width - 28 - bar_gap) // 2
        self._draw_value_bar(surface, pygame.Rect(top_rect.x + 14, top_rect.y + 16, bar_w, 32), "Protest risk", effects.get("protest_risk", 0), _C_DANGER)
        self._draw_value_bar(surface, pygame.Rect(top_rect.x + 14 + bar_w + bar_gap, top_rect.y + 16, bar_w, 32), "Anti-corruption swing", effects.get("anti_corruption_swing", 0), _C_GOLD)
        self._draw_value_bar(surface, pygame.Rect(top_rect.x + 14, top_rect.y + 74, bar_w, 32), "Policy passing chance", effects.get("policy_passing_chance", 0), _C_SUCCESS)
        self._draw_value_bar(surface, pygame.Rect(top_rect.x + 14 + bar_w + bar_gap, top_rect.y + 74, bar_w, 32), "Regime pressure", effects.get("regime_survival_pressure", 0), _C_INFO)

        body_y = top_rect.bottom + 14
        left_rect = pygame.Rect(rect.x, body_y, rect.width // 2 - 7, rect.bottom - body_y)
        right_rect = pygame.Rect(left_rect.right + 14, body_y, rect.width - left_rect.width - 14, rect.bottom - body_y)
        for panel_rect, title in ((left_rect, "INTERNAL POLICY LINKS"), (right_rect, "POLITICAL RULES")):
            self._draw_vertical_gradient_rect(surface, panel_rect, (15, 24, 38), (8, 13, 22), radius=6)
            pygame.draw.rect(surface, (52, 65, 82), panel_rect, 1, border_radius=6)
            self._draw_text_fit(surface, title, _C_GOLD_BRIGHT, panel_rect.x + 14, panel_rect.y + 12, panel_rect.width - 28, self.font_bold)

        policy_lines = [
            "Low civil liberties with strong opposition raises protest risk.",
            "High corruption creates anti-government swing in elections.",
            "High media freedom spreads scandals but improves legitimacy.",
            "Identity tension strengthens identity-based parties.",
            "Police effectiveness can lower unrest; brutality raises anger.",
        ]
        y = left_rect.y + 44
        for line in policy_lines:
            self._draw_text_fit(surface, line, _C_TEXT, left_rect.x + 14, y, left_rect.width - 28, self.small_font)
            y += 24

        rule_rows = (
            ("Snap election", "Yes" if data.get("can_call_snap_election") else "No"),
            ("No-confidence", "Yes" if data.get("can_have_no_confidence_vote") else "No"),
            ("Coalition collapse", "Yes" if data.get("can_have_coalition_collapse") else "No"),
            ("Coup risk", "Yes" if data.get("can_have_coup_risk") else "No"),
            ("One-party election", "Yes" if data.get("can_have_single_party_election") else "No"),
            ("Appointed legislature", "Yes" if data.get("can_have_appointed_legislature") else "No"),
        )
        y = right_rect.y + 44
        for label, value in rule_rows:
            self._draw_domestic_info_row(surface, right_rect.x + 14, y, label, value, right_rect.width - 28)
            y += 24
            
    def _draw_domestic_health_tab(self, surface, rect, data, mouse):

       health = data.get("health", {}) if isinstance(data.get("health", {}), dict) else {}

       chip_gap = 10
       chip_w = (rect.width - chip_gap * 2) // 3

       # Top chips (summary)
       self._draw_metric_chip(
           surface,
           pygame.Rect(rect.x, rect.y, chip_w, 58),
           "Active Epidemic",
           str(health.get("active_epidemic", "None")),
           icon_key="warning",
           accent=(200, 80, 80)
        )

       self._draw_metric_chip(
           surface,
           pygame.Rect(rect.x + chip_w + chip_gap, rect.y, chip_w, 58),
           "Current Cases",
           f"{int(health.get('current_cases', 0) or 0)}",
           icon_key="health",
           accent=_C_INFO
        )

       self._draw_metric_chip(
           surface,
           pygame.Rect(rect.x + (chip_w + chip_gap) * 2, rect.y, chip_w, 58),
           "Mortality Rate",
           f"{float(health.get('mortality', 0) or 0):.2f}%",
           icon_key="skull",
           accent=_C_GOLD
        )

       body_y = rect.y + 78
       left_rect = pygame.Rect(rect.x, body_y, rect.width // 2 - 7, rect.bottom - body_y)
       right_rect = pygame.Rect(left_rect.right + 14, body_y, rect.width - left_rect.width - 14, rect.bottom - body_y)

       # LEFT PANEL
       self._draw_vertical_gradient_rect(surface, left_rect, (15, 24, 38), (8, 13, 22), radius=6)
       pygame.draw.rect(surface, (52, 65, 82), left_rect, 1, border_radius=6)

       self._draw_text_fit(
           surface,
           "HEALTH STATUS",
           _C_GOLD_BRIGHT,
           left_rect.x + 14,
           left_rect.y + 12,
           left_rect.width - 28,
           self.font_bold
        )

       y = left_rect.y + 44
       rows = (
           ("Hospitalisation", f"{int(health.get('hospitalisation', 0) or 0)}"),
           ("Mortality Rate", f"{float(health.get('mortality', 0) or 0):.2f}%"),
           ("Healthcare Load", health.get("healthcare_load", "Normal")),
           ("Risk Level", health.get("risk_level", "Low")),
        )

       for label, value in rows:
           self._draw_domestic_info_row(
               surface,
               left_rect.x + 14,
               y,
               label,
               value,
               left_rect.width - 28
            )
           y += 28

       # RIGHT PANEL
       self._draw_vertical_gradient_rect(surface, right_rect, (15, 24, 38), (8, 13, 22), radius=6)
       pygame.draw.rect(surface, (52, 65, 82), right_rect, 1, border_radius=6)

       self._draw_text_fit(
           surface,
           "EPIDEMIC NOTES",
           _C_GOLD_BRIGHT,
           right_rect.x + 14,
           right_rect.y + 12,
           right_rect.width - 28,
           self.font_bold
        )

       notes = [
           "Epidemics reduce population growth and stability.",
           "High hospitalisation increases economic pressure.",
           "Outbreak severity depends on healthcare capacity.",
           "Government response can reduce spread rate.",
        ]

       y = right_rect.y + 44
       for line in notes:
           self._draw_text_fit(
               surface,
               line,
               _C_TEXT,
               right_rect.x + 14,
               y,
               right_rect.width - 28,
               self.small_font
           )
           y += 25

       # Optional bar 
       self._draw_value_bar(
           surface,
           pygame.Rect(right_rect.x + 14, right_rect.bottom - 48, right_rect.width - 28, 32),
           "Healthcare Capacity",
           health.get("healthcare_capacity", 0),
           _C_INFO
        )
       
       mco_enabled = bool(data.get("mco_enabled", False))

       self._mco_button_rect = pygame.Rect(
           right_rect.x + 14,
           right_rect.bottom - 95,
           180,
           36
        )

       pygame.draw.rect(
           surface,
           (60, 160, 80) if mco_enabled else (180, 70, 70),
           self._mco_button_rect,
           border_radius=6
        )

       self._draw_text_fit(
           surface,
           f"MCO: {'ON' if mco_enabled else 'OFF'}",
           (255,255,255),
           self._mco_button_rect.x,
           self._mco_button_rect.y + 8,
           self._mco_button_rect.width,
           self.small_font
        )
        

    def _draw_war_progress_popup(self, surface, mouse):
        popup_w = min(900, max(640, self.map_rect.width - 72))
        max_popup_h = max(520, surface.get_height() - self.topbar_height - 36)
        popup_h = min(740, max_popup_h, max(620, self.map_rect.height - 64))
        popup_rect = pygame.Rect(0, 0, popup_w, popup_h)
        if self._warprogress_popup_pos is None:
            popup_rect.center = self.map_rect.center
        else:
            popup_rect.topleft = self._warprogress_popup_pos
        popup_rect.clamp_ip(surface.get_rect().inflate(-32, -32))
        self._warprogress_popup_pos = popup_rect.topleft
        self._warprogress_popup_rect = popup_rect

        shadow = pygame.Surface((popup_rect.width + 28, popup_rect.height + 28), pygame.SRCALPHA)
        pygame.draw.rect(shadow, (0, 0, 0, 150), shadow.get_rect(), border_radius=12)
        surface.blit(shadow, (popup_rect.x - 14, popup_rect.y - 10))
        self._draw_glass_panel(surface, popup_rect, radius=8, border=(72, 86, 108), glow=True)

        header_h = 64
        self._warprogress_header_rect = pygame.Rect(popup_rect.x, popup_rect.y, popup_rect.width, header_h)
        pygame.draw.line(surface, (76, 64, 38), (popup_rect.x + 16, popup_rect.y + header_h), (popup_rect.right - 16, popup_rect.y + header_h), 1)
        icon = self._topbar_icons.get("war_progress")
        title_x = popup_rect.x + 24
        if icon is not None:
            surface.blit(icon, (title_x, popup_rect.y + 21))
            title_x += icon.get_width() + 12
        title = self.title_font.render("WAR PROGRESS", True, _C_GOLD_BRIGHT)
        subtitle = self.small_font.render("OCCUPATION AND CAPITULATION RISK", True, _C_TEXT_MUTED)
        surface.blit(title, (title_x, popup_rect.y + 14))
        surface.blit(subtitle, (title_x, popup_rect.y + 40))

        close_size = 34
        self._warprogress_close_rect = pygame.Rect(popup_rect.right - close_size - 16, popup_rect.y + 15, close_size, close_size)
        close_hovered = self._warprogress_close_rect.collidepoint(mouse)
        close_top = (45, 55, 68) if close_hovered else (23, 32, 48)
        self._draw_vertical_gradient_rect(surface, self._warprogress_close_rect, close_top, (10, 16, 25), radius=6)
        pygame.draw.rect(surface, (_C_DANGER if close_hovered else (62, 76, 95)), self._warprogress_close_rect, 1, border_radius=6)
        close_icon = self._topbar_icons.get("close")
        if close_icon is not None:
            surface.blit(close_icon, close_icon.get_rect(center=self._warprogress_close_rect.center))
        else:
            close_label = self.font_bold.render("X", True, _C_TEXT)
            surface.blit(close_label, close_label.get_rect(center=self._warprogress_close_rect.center))

        data = self._warprogressdata or {}
        wars = [war for war in data.get("wars", []) if isinstance(war, dict)]
        if not wars and data.get("aggressor") and data.get("defender"):
            wars = [data]
        if wars:
            self._warprogress_active_index = max(0, min(self._warprogress_active_index, len(wars) - 1))
            data = wars[self._warprogress_active_index]
        else:
            self._warprogress_active_index = 0
        content_x = popup_rect.x + 28
        content_y = popup_rect.y + header_h + 18
        content_w = popup_rect.width - 56

        tab_label = self.small_font.render("WAR THEATERS", True, _C_TEXT_MUTED)
        surface.blit(tab_label, (content_x, content_y))
        self._warprogress_tab_rects = []
        tab_y = content_y + 18
        if wars:
            gap = 8
            tab_w = max(150, min(238, (content_w - gap * max(0, len(wars) - 1)) // max(1, len(wars))))
            for index, war in enumerate(wars):
                tab_rect = pygame.Rect(content_x + index * (tab_w + gap), tab_y, tab_w, 38)
                if tab_rect.right > content_x + content_w:
                    break
                self._warprogress_tab_rects.append(tab_rect)
                selected = index == self._warprogress_active_index
                hovered = tab_rect.collidepoint(mouse)
                top = (43, 36, 24) if selected else ((28, 39, 59) if hovered else (14, 22, 33))
                bottom = (25, 22, 18) if selected else (9, 15, 24)
                self._draw_vertical_gradient_rect(surface, tab_rect, top, bottom, radius=6)
                pygame.draw.rect(surface, (_C_GOLD if selected else (46, 59, 78)), tab_rect, 1, border_radius=6)
                label = war.get("name") or f"{war.get('aggressor', '?')} - {war.get('defender', '?')}"
                self._draw_text_fit(surface, label, (_C_GOLD_BRIGHT if selected else _C_TEXT), tab_rect.x + 10, tab_rect.y + 10, tab_rect.width - 20, self.font_bold if selected else self.font)

        content_y = tab_y + 52
        aggressor = data.get("aggressor")
        defender = data.get("defender")
        attackers = [entry for entry in data.get("attackers", []) if isinstance(entry, dict)]
        defenders = [entry for entry in data.get("defenders", []) if isinstance(entry, dict)]
        if not attackers and aggressor:
            attackers = [{
                "country": aggressor,
                "casualties": data.get("aggressor_casualties", 0),
                "manpower": data.get("aggressor_manpower", 0),
                "capitulation_progress": data.get("defender_progress", 0.0),
                "enemy_occupied_percent": data.get("aggressor_occupied_percent", 0.0),
            }]
        if not defenders and defender:
            defenders = [{
                "country": defender,
                "casualties": data.get("defender_casualties", 0),
                "manpower": data.get("defender_manpower", 0),
                "capitulation_progress": data.get("progress", 0.0),
                "enemy_occupied_percent": data.get("defender_occupied_percent", 0.0),
            }]

        if not attackers or not defenders:
            empty = self.font_bold.render("No active war", True, _C_TEXT)
            surface.blit(empty, empty.get_rect(center=(popup_rect.centerx, content_y + 120)))
            return

        attacker_side = data.get("attacker_side", {}) if isinstance(data.get("attacker_side", {}), dict) else {}
        defender_side = data.get("defender_side", {}) if isinstance(data.get("defender_side", {}), dict) else {}
        attacker_label = data.get("attacker_label") or attacker_side.get("label") or aggressor
        defender_label = data.get("defender_label") or defender_side.get("label") or defender
        war_title = data.get("name") or f"{attacker_label} vs {defender_label}"
        self._draw_text_fit(surface, war_title, _C_TEXT, content_x, content_y, content_w, self.font_bold)
        since = data.get("start_turn")
        pair_count = max(1, int(data.get("pair_count", 1) or 1))
        active_pair_count = max(pair_count, int(data.get("active_pair_count", data.get("active_war_count", pair_count)) or pair_count))
        meta = (
            f"{len(attackers)} attackers vs {len(defenders)} defenders"
            f"  |  Linked wars: {self._format_number(pair_count)}"
        )
        if active_pair_count > pair_count:
            meta += f" of {self._format_number(active_pair_count)}"
        if since:
            meta += f"  |  Since turn {self._format_number(since)}"
        self._draw_text_fit(surface, meta, _C_TEXT_MUTED, content_x, content_y + 24, content_w)

        def clamp_percent(value):
            try:
                return max(0.0, min(100.0, float(value or 0.0)))
            except (TypeError, ValueError):
                return 0.0

        def country_flag(country):
            key = (
                str(country or "")
                .strip()
                .lower()
                .replace(" ", "_")
                .replace("-", "_")
            )
            return self._flags.get(key)

        pressure_y = content_y + 54
        attacker_pressure = clamp_percent(data.get("progress", 0.0))
        defender_pressure = clamp_percent(data.get("defender_progress", 0.0))
        self._draw_text_fit(surface, "CAPITULATION PRESSURE", _C_TEXT_MUTED, content_x, pressure_y, content_w, self.small_font_bold)
        meter_rect = pygame.Rect(content_x, pressure_y + 18, content_w, 24)
        pygame.draw.rect(surface, (7, 12, 20), meter_rect, border_radius=5)
        pygame.draw.rect(surface, (43, 56, 73), meter_rect, 1, border_radius=5)
        pressure_total = attacker_pressure + defender_pressure
        attacker_share = 0.5 if pressure_total <= 0 else attacker_pressure / pressure_total
        attacker_w = int(meter_rect.width * attacker_share)
        if attacker_w > 0:
            self._draw_vertical_gradient_rect(surface, pygame.Rect(meter_rect.x, meter_rect.y, attacker_w, meter_rect.height), (182, 73, 73), (117, 45, 45), radius=5)
        if attacker_w < meter_rect.width:
            self._draw_vertical_gradient_rect(surface, pygame.Rect(meter_rect.x + attacker_w, meter_rect.y, meter_rect.width - attacker_w, meter_rect.height), (74, 143, 231), (38, 83, 151), radius=5)
        pygame.draw.line(surface, _C_GOLD_BRIGHT, (meter_rect.centerx, meter_rect.y - 3), (meter_rect.centerx, meter_rect.bottom + 3), 1)
        left_text = f"{attacker_label}: {attacker_pressure:.1f}%"
        right_text = f"{defender_label}: {defender_pressure:.1f}%"
        self._draw_text_fit(surface, left_text, _C_TEXT, meter_rect.x + 8, meter_rect.y + 5, meter_rect.width // 2 - 12, self.small_font_bold)
        right_surface = self.small_font_bold.render(self._fit_text(self.small_font_bold, right_text, meter_rect.width // 2 - 12), True, _C_TEXT)
        surface.blit(right_surface, (meter_rect.right - right_surface.get_width() - 8, meter_rect.y + 5))

        def draw_country_row(row_rect, entry, accent):
            row_top = (20, 30, 46)
            self._draw_vertical_gradient_rect(surface, row_rect, row_top, (9, 15, 24), radius=5)
            pygame.draw.rect(surface, (39, 52, 69), row_rect, 1, border_radius=5)
            pygame.draw.line(surface, accent, (row_rect.x + 5, row_rect.y + 7), (row_rect.x + 5, row_rect.bottom - 7), 2)

            draw_x = row_rect.x + 12
            flag_img = country_flag(entry.get("country"))
            if flag_img is not None:
                flag = pygame.transform.smoothscale(flag_img, (24, 16))
                surface.blit(flag, (draw_x, row_rect.y + 8))
                draw_x += 32

            country_name = str(entry.get("country", "Unknown"))
            stat_text = (
                f"MP {self._format_compact_number(entry.get('manpower', 0))}"
                f" | Losses {self._format_compact_number(entry.get('casualties', 0))}"
            )
            right_w = 58
            self._draw_text_fit(surface, country_name, _C_TEXT, draw_x, row_rect.y + 4, row_rect.width - (draw_x - row_rect.x) - right_w - 10, self.font_bold)
            self._draw_text_fit(surface, stat_text, _C_TEXT_MUTED, draw_x, row_rect.y + 21, row_rect.width - (draw_x - row_rect.x) - right_w - 10, self.small_font)

            cap_percent = clamp_percent(entry.get("capitulation_progress", entry.get("enemy_occupied_percent", 0.0)))
            cap_text = self.small_font_bold.render(f"{cap_percent:.0f}%", True, _C_DANGER if cap_percent >= 80.0 else _C_TEXT)
            surface.blit(cap_text, (row_rect.right - cap_text.get_width() - 10, row_rect.y + 6))
            cap_label = self.small_font.render("CAP", True, _C_TEXT_MUTED)
            surface.blit(cap_label, (row_rect.right - cap_label.get_width() - 10, row_rect.y + 21))

            bar_rect = pygame.Rect(row_rect.x + 12, row_rect.bottom - 5, row_rect.width - 24, 3)
            pygame.draw.rect(surface, (24, 34, 49), bar_rect, border_radius=2)
            fill_w = int(bar_rect.width * (cap_percent / 100.0))
            if fill_w > 0:
                pygame.draw.rect(surface, accent, pygame.Rect(bar_rect.x, bar_rect.y, fill_w, bar_rect.height), border_radius=2)

        def draw_side_panel(panel_rect, title, label, entries, accent):
            self._draw_vertical_gradient_rect(surface, panel_rect, (15, 23, 36), (8, 13, 22), radius=6)
            pygame.draw.rect(surface, accent, panel_rect, 1, border_radius=6)
            self._draw_text_fit(surface, title, accent, panel_rect.x + 12, panel_rect.y + 9, panel_rect.width - 24, self.small_font_bold)
            self._draw_text_fit(surface, label, _C_TEXT, panel_rect.x + 12, panel_rect.y + 25, panel_rect.width - 24, self.font_bold)

            manpower = sum(max(0, int(entry.get("manpower", 0) or 0)) for entry in entries)
            casualties = sum(max(0, int(entry.get("casualties", 0) or 0)) for entry in entries)
            stat_line = f"Fielded {self._format_compact_number(manpower)}  |  Losses {self._format_compact_number(casualties)}"
            self._draw_text_fit(surface, stat_line, _C_TEXT_MUTED, panel_rect.x + 12, panel_rect.y + 45, panel_rect.width - 24, self.small_font)

            list_y = panel_rect.y + 66
            row_h = 38
            row_gap = 5
            max_rows = max(0, (panel_rect.bottom - list_y - 10) // (row_h + row_gap))
            if not entries or max_rows <= 0:
                self._draw_text_fit(surface, "No combatants tracked.", _C_TEXT_MUTED, panel_rect.x + 12, list_y, panel_rect.width - 24)
                return
            for index, entry in enumerate(entries[:max_rows]):
                draw_country_row(
                    pygame.Rect(panel_rect.x + 10, list_y + index * (row_h + row_gap), panel_rect.width - 20, row_h),
                    entry,
                    accent,
                )
            if len(entries) > max_rows:
                overflow = len(entries) - max_rows
                self._draw_text_fit(surface, f"+{overflow} more combatants", _C_TEXT_MUTED, panel_rect.x + 12, panel_rect.bottom - 20, panel_rect.width - 24, self.small_font)

        chip_gap = 10
        chip_w = (content_w - chip_gap * 2) // 3
        chip_y = popup_rect.bottom - 76
        sides_y = pressure_y + 56
        col_gap = 12
        col_w = (content_w - col_gap) // 2
        middle_space = max(0, chip_y - sides_y - 12)
        if middle_space >= 230:
            side_panel_h = min(292, middle_space - 82)
        else:
            side_panel_h = max(112, int(middle_space * 0.66))
        draw_side_panel(
            pygame.Rect(content_x, sides_y, col_w, side_panel_h),
            "ATTACKERS",
            str(attacker_label),
            attackers,
            (208, 86, 86),
        )
        draw_side_panel(
            pygame.Rect(content_x + col_w + col_gap, sides_y, col_w, side_panel_h),
            "DEFENDERS",
            str(defender_label),
            defenders,
            (74, 143, 231),
        )

        transfer_y = sides_y + side_panel_h + 12
        transfer_h = chip_y - transfer_y - 12
        if transfer_h >= 44:
            transfer_rect = pygame.Rect(content_x, transfer_y, content_w, transfer_h)
            self._draw_vertical_gradient_rect(surface, transfer_rect, (13, 21, 34), (7, 12, 20), radius=6)
            pygame.draw.rect(surface, (43, 56, 73), transfer_rect, 1, border_radius=6)
            self._draw_text_fit(surface, "Linked Fronts", _C_GOLD_BRIGHT, transfer_rect.x + 12, transfer_rect.y + 9, transfer_rect.width - 24, self.font_bold)
            pair_lines = []
            for pair in data.get("war_pairs", [])[:4]:
                if not isinstance(pair, dict):
                    continue
                pair_lines.append(f"{pair.get('aggressor', '?')} vs {pair.get('defender', '?')}")
            if pair_count > len(pair_lines):
                pair_lines.append(f"+{pair_count - len(pair_lines)} more fronts")
            line_y = transfer_rect.y + 34
            line_max = max(1, (transfer_rect.bottom - line_y - 6) // 18)
            if not pair_lines:
                self._draw_text_fit(surface, "No linked fronts tracked.", _C_TEXT_MUTED, transfer_rect.x + 12, line_y, transfer_rect.width // 2 - 18)
            else:
                for line in pair_lines[:line_max]:
                    self._draw_text_fit(surface, line, _C_TEXT, transfer_rect.x + 12, line_y, transfer_rect.width // 2 - 18, self.small_font)
                    line_y += 18

            transfer_col_x = transfer_rect.x + transfer_rect.width // 2 + 8
            self._draw_text_fit(surface, "Recent Transfers", _C_GOLD_BRIGHT, transfer_col_x, transfer_rect.y + 9, transfer_rect.right - transfer_col_x - 12, self.font_bold)
            transfer_lines = data.get("occupation_transfers", [])
            line_y = transfer_rect.y + 34
            if not transfer_lines:
                self._draw_text_fit(surface, "No occupation handoffs tracked yet.", _C_TEXT_MUTED, transfer_col_x, line_y, transfer_rect.right - transfer_col_x - 12, self.small_font)
            else:
                line_max = max(1, (transfer_rect.bottom - line_y - 6) // 18)
                for transfer in transfer_lines[:line_max]:
                    if transfer.get("from_occupation"):
                        line = (
                            f"{transfer.get('controller', 'Unknown')} seized {transfer.get('owner', 'Unknown')} "
                            f"{transfer.get('provinceid', 'province')} from {transfer.get('previous_controller', 'Unknown')}'s occupation"
                        )
                    else:
                        line = (
                            f"{transfer.get('controller', 'Unknown')} occupied {transfer.get('owner', 'Unknown')} "
                            f"{transfer.get('provinceid', 'province')}"
                        )
                    self._draw_text_fit(surface, line, _C_TEXT, transfer_col_x, line_y, transfer_rect.right - transfer_col_x - 12, self.small_font)
                    line_y += 18

        self._draw_metric_chip(
            surface,
            pygame.Rect(content_x, chip_y, chip_w, 50),
            "Attackers fielded",
            self._format_compact_number(data.get("aggressor_manpower", 0)),
            icon_key="manpower",
            accent=(208, 86, 86),
        )
        self._draw_metric_chip(
            surface,
            pygame.Rect(content_x + chip_w + chip_gap, chip_y, chip_w, 50),
            "Defenders fielded",
            self._format_compact_number(data.get("defender_manpower", 0)),
            icon_key="manpower",
            accent=_C_INFO,
        )
        total_casualties = int(data.get("total_casualties", 0) or 0)
        self._draw_metric_chip(
            surface,
            pygame.Rect(content_x + (chip_w + chip_gap) * 2, chip_y, chip_w, 50),
            "Total casualties",
            self._format_compact_number(total_casualties),
            icon_key="combat",
            accent=_C_DANGER,
        )

    def _draw_glow_btn(self, surface, key, rect, enabled, label, primary=False, selected=False, mouse=None, icon_key=None, align='center'):
        if mouse is None:
            mouse = pygame.mouse.get_pos()
        hovered = rect.collidepoint(mouse) and enabled
        glow = self._button_glows.get(key, 0.0)
        if hovered:
            glow = min(1.0, glow + 0.12)
        else:
            glow = max(0.0, glow - 0.08)
        self._button_glows[key] = glow

        radius = 8
        drawrect = scale_rect(
            rect,
            1.0 + glow * 0.035,
            (math.sin(self._motion_time * 3.0 + len(str(key))) * glow * 2.0, -glow * 1.5),
        )
        if primary:
            top = (26, 93, 60) if hovered else ((20, 74, 50) if enabled else (48, 53, 60))
            bottom = (9, 38, 29) if enabled else (35, 38, 43)
            border = (72, 183, 123) if enabled else (69, 75, 84)
        else:
            top = (31, 48, 74) if hovered else ((22, 34, 53) if enabled else (48, 53, 60))
            bottom = (11, 17, 27) if enabled else (35, 38, 43)
            border = _C_GOLD if hovered and enabled else ((69, 84, 104) if enabled else (69, 75, 84))

        self._draw_vertical_gradient_rect(surface, drawrect, top, bottom, radius=radius)
        pygame.draw.rect(surface, border, drawrect, 1, border_radius=radius)
        draw_light_sweep(surface, drawrect, self._motion_time + len(str(key)) * 0.17, border, alpha=int(10 + glow * 24))

        if glow > 0.01 and enabled:
            w, h = drawrect.size
            glow_surf = pygame.Surface((w + 24, h + 24), pygame.SRCALPHA)
            for ring in range(5):
                ring_alpha = int(glow * (28 - ring * 5))
                if ring_alpha <= 0:
                    continue
                offset = ring * 2 + 2
                gw = w + offset * 2
                gh = h + offset * 2
                glow_color = _C_SUCCESS if primary else _C_GOLD
                pygame.draw.rect(glow_surf, (*glow_color, ring_alpha),
                    (12 - offset, 12 - offset, gw, gh),
                    border_radius=radius + offset, width=2)
            surface.blit(glow_surf, (drawrect.x - 12, drawrect.y - 12))

        if hovered:
            text_color = _C_TEXT
            fnt = self.font_bold
        elif primary and enabled:
            text_color = _C_TEXT
            fnt = self.font
        else:
            text_color = _C_TEXT if enabled else _C_TEXT_MUTED
            fnt = self.font
        txt = fnt.render(label, True, text_color)
        icon = self._topbar_icons.get(icon_key) if icon_key else None

        if align == 'left':
            text_x = drawrect.x + 16
            if icon is not None and drawrect.width >= 80:
                draw_animated_icon(
                    surface, icon,
                    (text_x + icon.get_width()//2, drawrect.centery),
                    self._motion_time,
                    hover=1.0 if (hovered or selected) else 0.0,
                    accent=_C_SUCCESS if primary else _C_GOLD,
                    phase=len(str(key)) * 0.21,
                )
                text_x += icon.get_width() + 8
            surface.blit(txt, (text_x, drawrect.centery - txt.get_height() // 2))
        else:  
            if icon is not None and drawrect.width >= 80:
                gap = 6
                total_width = icon.get_width() + gap + txt.get_width()
                start_x = drawrect.centerx - total_width // 2
                draw_animated_icon(surface, icon, (start_x + icon.get_width() // 2, drawrect.centery), self._motion_time, hover=1.0 if (hovered or selected) else 0.0, accent=_C_SUCCESS if primary else _C_GOLD, phase=len(str(key)) * 0.21)
                surface.blit(txt, (start_x + icon.get_width() + gap, drawrect.centery - txt.get_height() // 2))
            else:
                surface.blit(txt, txt.get_rect(center=drawrect.center))

    def _draw_pausemenu(self, surface: pygame.Surface):
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        draw_scanlines(overlay, overlay.get_rect(), self._motion_time, color=(212, 169, 77), alpha=12, spacing=26)
        surface.blit(overlay, (0, 0))

        draw_rect = scale_rect(self._pausemenu_rect, 1.0 + 0.015 * pulse(self._motion_time, 1.8))
        draw_soft_glow(surface, draw_rect, _C_GOLD, 0.42 + 0.18 * pulse(self._motion_time, 2.5), radius=9, rings=5)
        self._draw_glass_panel(surface, draw_rect, radius=7, border=(92, 74, 42), glow=True)

        title = self.title_font.render("PAUSED", True, (230, 230, 230))
        surface.blit(title, title.get_rect(center=(draw_rect.centerx, draw_rect.y + 34)))

        info = self.font.render("Press ESC to resume", True, (200, 200, 200))
        surface.blit(info, info.get_rect(center=(draw_rect.centerx, draw_rect.y + 72)))

        self._draw_glow_btn(surface, "pause_quit", self._pausequit_rect, True, "QUIT GAME", mouse=pygame.mouse.get_pos())
