import math
import os
import random
import shutil
import sys

import pygame

from engine.runtime import main as run_game
from engine import savegame as savegamemodule
from engine.settings import loadsettings, savesettings, updatesettings
from game.animation.motion import (
    AmbientParticleField,
    PulseLayer,
    clamp,
    draw_light_sweep,
    draw_scanlines,
    draw_soft_glow,
    ease_out_back,
    exp_lerp,
    mix_color,
    pulse,
    scale_rect,
)
from game.script_menu import ScriptMenuController
from game.window_icon import set_window_icon


WIDTH, HEIGHT = 1280, 720

_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
_FONTS = os.path.join(_ROOT, "fonts")
_IMAGES = os.path.join(_ROOT, "images")
_MENU_BACKGROUND = os.path.join(_IMAGES, "Game Menu UI Design (1).png")
_SPLASH_ASSETS = os.path.join(_ROOT, "game", "images")
_GAME_LOGO = os.path.join(_SPLASH_ASSETS, "developer_logo.png")
_ILMU_LOGO = os.path.join(_SPLASH_ASSETS, "ilmulogo.svg")
_MMU_LOGO = os.path.join(_SPLASH_ASSETS, "mmulogo.svg")
_MMU_PADU_SFX = os.path.join(_SPLASH_ASSETS, "mmupadusfx.mp3")
_BGM_DIRECTORY = os.path.join(_ROOT, "game", "sounds", "bgm")

_C_TEXT = (248, 250, 252)
_C_MUTED = (156, 163, 175)
_C_GOLD = (212, 169, 77)
_C_GOLD_BRIGHT = (242, 204, 119)
_C_BLUE = (74, 143, 231)
_C_DANGER = (224, 93, 93)


def remove_cache():
    targets = [
        os.path.join(_ROOT, ".ebee_super_optimization"),
        os.path.join(_ROOT, "map", ".ebee_super_optimization"),
    ]
    for path in targets:
        try:
            if os.path.exists(path):
                shutil.rmtree(path)
                print(f"Deleted {path}")
        except Exception as exc:
            print(f"Error deleting {path}: {exc}")


def _load_font(name, size, fallback="bahnschrift", bold=False):
    filepath = os.path.join(_FONTS, name)
    if os.path.isfile(filepath):
        return pygame.font.Font(filepath, size)
    return pygame.font.SysFont(fallback, size, bold=bold)


def _safe_sound(path, volume=0.4):
    try:
        sound = pygame.mixer.Sound(path)
        sound.set_volume(volume)
        return sound
    except pygame.error:
        return None


def _play_random_bgm(volume):
    try:
        track_paths = [
            entry.path
            for entry in os.scandir(_BGM_DIRECTORY)
            if entry.is_file() and entry.name.lower().endswith((".mp3", ".ogg", ".wav"))
        ]
        if not track_paths:
            return None

        track_path = random.choice(track_paths)
        pygame.mixer.music.load(track_path)
        pygame.mixer.music.set_volume(max(0.0, min(1.0, volume)))
        pygame.mixer.music.play(-1)
        return track_path
    except (OSError, pygame.error):
        return None


def _scale_splash_logo(logo, max_width, max_height):
    scale = min(max_width / logo.get_width(), max_height / logo.get_height())
    size = (
        max(1, int(logo.get_width() * scale)),
        max(1, int(logo.get_height() * scale)),
    )
    return pygame.transform.smoothscale(logo, size)


def _create_splash_card(screen_size, logo_path, heading=None, footer=None, game_logo=False):
    width, height = screen_size
    card = pygame.Surface(screen_size, pygame.SRCALPHA)
    try:
        logo = pygame.image.load(logo_path).convert_alpha()
    except (FileNotFoundError, pygame.error):
        logo = pygame.Surface((1, 1), pygame.SRCALPHA)
    if game_logo:
        logo = _scale_splash_logo(logo, width * 0.6, height * 0.6)
        card.blit(logo, logo.get_rect(center=(width // 2, height // 2)))
        return card

    logo = _scale_splash_logo(logo, width * 0.48, height * 0.30)
    heading_font = _load_font("Inter_18pt-Medium.ttf", max(20, int(height * 0.042)))
    footer_font = _load_font("Inter_18pt-Medium.ttf", max(22, int(height * 0.05)), bold=True)
    logo_center_y = height // 2

    if heading:
        heading_surface = heading_font.render(heading, True, _C_MUTED)
        heading_rect = heading_surface.get_rect(center=(width // 2, int(height * 0.22)))
        card.blit(heading_surface, heading_rect)

    if footer:
        logo_center_y = int(height * 0.47)
        footer_surface = footer_font.render(footer, True, _C_TEXT)
        footer_rect = footer_surface.get_rect(center=(width // 2, int(height * 0.79)))
        card.blit(footer_surface, footer_rect)

    card.blit(logo, logo.get_rect(center=(width // 2, logo_center_y)))
    return card


def show_splash_screen(screen, volume=1.0):
    clock = pygame.time.Clock()
    mmu_sound = _safe_sound(_MMU_PADU_SFX, max(0.0, min(1.0, volume)))
    final_hold_seconds = 1.2
    if mmu_sound is not None:
        final_hold_seconds = max(final_hold_seconds, mmu_sound.get_length() - 1.0)

    cards = [
        (_create_splash_card(screen.get_size(), _GAME_LOGO, game_logo=True), 1.2, None),
        (_create_splash_card(screen.get_size(), _ILMU_LOGO, heading="Powered by"), 1.2, None),
        (
            _create_splash_card(
                screen.get_size(),
                _MMU_LOGO,
                heading="Part of",
                footer="Mini IT Project 2026",
            ),
            final_hold_seconds,
            mmu_sound,
        ),
    ]

    fade_seconds = 0.5
    for card, hold_seconds, sound in cards:
        if sound is not None:
            sound.play()

        elapsed = 0.0
        total_seconds = fade_seconds + hold_seconds + fade_seconds
        while elapsed < total_seconds:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    if mmu_sound is not None:
                        mmu_sound.stop()
                    return False

            if elapsed < fade_seconds:
                alpha = int(255 * elapsed / fade_seconds)
            elif elapsed > fade_seconds + hold_seconds:
                alpha = int(255 * (total_seconds - elapsed) / fade_seconds)
            else:
                alpha = 255

            screen.fill((0, 0, 0))
            card.set_alpha(max(0, min(255, alpha)))
            screen.blit(card, (0, 0))
            pygame.display.flip()
            elapsed += clock.tick(60) / 1000.0

    return True


def _draw_vertical_gradient(surface, rect, top_color, bottom_color, radius=0):
    if rect.width <= 0 or rect.height <= 0:
        return
    gradient = pygame.Surface(rect.size, pygame.SRCALPHA)
    for y in range(rect.height):
        t = y / max(1, rect.height - 1)
        color = mix_color(top_color, bottom_color, t)
        pygame.draw.line(gradient, (*color, 255), (0, y), (rect.width, y))
    if radius:
        mask = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255), mask.get_rect(), border_radius=radius)
        gradient.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    surface.blit(gradient, rect.topleft)


class AnimatedMainMenu:
    def __init__(self, is_fullscreen=False):
        self.is_fullscreen = bool(is_fullscreen)
        flags = pygame.FULLSCREEN if self.is_fullscreen else 0
        size = (0, 0) if self.is_fullscreen else (WIDTH, HEIGHT)
        set_window_icon()
        self.screen = pygame.display.set_mode(size, flags)
        pygame.display.set_caption("Ebee Conquest - Main Menu")
        self.clock = pygame.time.Clock()
        self.running = True
        self.menu = "main"
        self.menu_transition = 1.0
        self.settings = loadsettings()
        self.volume = int(self.settings.get("volume", 50))
        self.setup_active = not bool(self.settings.get("setup_complete"))
        self.setup_player_name = str(self.settings.get("player_name") or "")
        self.setup_mode = str(self.settings.get("llm_mode") or "online")
        self.setup_api_key = str(self.settings.get("online_api_key") or "")
        self.setup_use_demo_key = bool(self.settings.get("use_demo_key", True))
        self.setup_active_field = "player_name"
        self.setup_error = ""
        self.setup_expand = 1.0 if self.setup_mode == "online" else 0.0
        self.volume_dragging = False
        self.mouse = (0, 0)
        self.notice = None
        self.notice_time = 0.0
       
        self.loadgame_open = False
        self.loadgame_slots = []
        self.loadgame_slot_rects = {}
        self.loadgame_back_rect = pygame.Rect(0, 0, 10, 10)

        self.title_font = _load_font("Inter_18pt-Medium.ttf", 42, bold=True)
        self.heading_font = _load_font("Inter_18pt-Medium.ttf", 28, bold=True)
        self.main_font = _load_font("Inter_18pt-Medium.ttf", 18)
        self.small_font = _load_font("Inter_18pt-Medium.ttf", 13)

        self.click_sound = _safe_sound("game/sounds/click.wav")
        self.script_menu = ScriptMenuController()
        self.particles = AmbientParticleField(96, seed=37)
        self.pulses = PulseLayer()
        self.button_motion = {}
        self._bg_surface = None
        self._bg_size = None
        self._refresh_background()
        
        if not show_splash_screen(self.screen, self.volume / 100.0):
            self.running = False
        else:
            self.bgm_path = _play_random_bgm(self.volume / 100.0)

    def _setup_controls(self):
        w, h = self.screen.get_size()
        panelwidth = min(760, max(600, int(w * 0.62)))
        expandedheight = 485 + int(115 * self.setup_expand)
        panelheight = min(h - 36, expandedheight)
        panel = pygame.Rect(0, 0, panelwidth, panelheight)
        panel.center = (w // 2, h // 2)
        namerect = pygame.Rect(panel.x + 44, panel.y + 96, panel.width - 88, 46)
        optionrects = {}
        optiontop = namerect.bottom + 42
        for index, mode in enumerate(("online", "ollama", "graph")):
            optionrects[mode] = pygame.Rect(
                panel.x + 44,
                optiontop + index * 60,
                panel.width - 88,
                50,
            )
        apirect = pygame.Rect(panel.x + 44, optionrects["graph"].bottom + 42, panel.width - 88, 44)
        demorect = pygame.Rect(panel.x + 44, apirect.bottom + 10, panel.width - 88, 34)
        continuebutton = pygame.Rect(panel.right - 220, panel.bottom - 58, 176, 42)
        return panel, namerect, optionrects, apirect, demorect, continuebutton

    def _draw_setup_popup(self, dt):
        targetexpand = 1.0 if self.setup_mode == "online" else 0.0
        self.setup_expand = exp_lerp(self.setup_expand, targetexpand, 11.0, dt)

        overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 196))
        self.screen.blit(overlay, (0, 0))
        panel, namerect, optionrects, apirect, demorect, continuebutton = self._setup_controls()
        draw_soft_glow(self.screen, panel, _C_GOLD, 0.38, radius=14, rings=7)
        _draw_vertical_gradient(self.screen, panel, (19, 30, 48), (5, 10, 18), radius=12)
        pygame.draw.rect(self.screen, (104, 89, 52), panel, 1, border_radius=12)

        title = self.heading_font.render("FIRST-RUN COMMAND SETUP", True, _C_GOLD_BRIGHT)
        self.screen.blit(title, (panel.x + 44, panel.y + 28))
        subtitle = self.small_font.render(
            "Choose how Ebee's non-player nations reason and negotiate.",
            True,
            _C_MUTED,
        )
        self.screen.blit(subtitle, (panel.x + 44, panel.y + 62))

        namelabel = self.small_font.render("PLAYER NAME", True, _C_GOLD)
        self.screen.blit(namelabel, (namerect.x, namerect.y - 20))
        nameactive = self.setup_active_field == "player_name"
        pygame.draw.rect(self.screen, (9, 17, 29), namerect, border_radius=7)
        pygame.draw.rect(
            self.screen,
            _C_GOLD if nameactive else (66, 82, 103),
            namerect,
            2 if nameactive else 1,
            border_radius=7,
        )
        namevalue = self.setup_player_name or "Enter your name"
        namecolor = _C_TEXT if self.setup_player_name else _C_MUTED
        namesurface = self.main_font.render(namevalue[-42:], True, namecolor)
        self.screen.blit(namesurface, (namerect.x + 14, namerect.centery - namesurface.get_height() // 2))

        modelabel = self.small_font.render("CHOOSE MODE", True, _C_GOLD)
        self.screen.blit(modelabel, (namerect.x, namerect.bottom + 18))
        labels = {
            "online": ("EBEE CONQUEST ONLINE LLM (RECOMMENDED)", "Hosted through the ILMU OpenAI-compatible API"),
            "ollama": ("OLLAMA LOCAL LLM", "Runs through localhost · model: llama3.2"),
            "graph": ("GRAPH-BASED LLM", "Offline deterministic negotiation logic"),
        }
        for mode, rect in optionrects.items():
            selected = mode == self.setup_mode
            hovered = rect.collidepoint(self.mouse)
            fill = (47, 43, 29) if selected else ((25, 39, 60) if hovered else (11, 20, 33))
            pygame.draw.rect(self.screen, fill, rect, border_radius=7)
            pygame.draw.rect(
                self.screen,
                _C_GOLD if selected else (62, 77, 96),
                rect,
                2 if selected else 1,
                border_radius=7,
            )
            pygame.draw.circle(self.screen, _C_GOLD if selected else (104, 115, 130), (rect.x + 22, rect.centery), 8, 2)
            if selected:
                pygame.draw.circle(self.screen, _C_GOLD_BRIGHT, (rect.x + 22, rect.centery), 4)
            label, detail = labels[mode]
            self.screen.blit(self.small_font.render(label, True, _C_TEXT), (rect.x + 42, rect.y + 8))
            self.screen.blit(self.small_font.render(detail, True, _C_MUTED), (rect.x + 42, rect.y + 27))

        if self.setup_expand > 0.03:
            fieldalpha = int(255 * self.setup_expand)
            slideoffset = int((1.0 - self.setup_expand) * -34)
            apirect = apirect.move(0, slideoffset)
            demorect = demorect.move(0, slideoffset)
            apilabel = self.small_font.render(
                'INPUT API KEY OR USE DEMO MODE KEY',
                True,
                (*_C_GOLD, fieldalpha),
            )
            self.screen.blit(apilabel, (apirect.x, apirect.y - 21))
            apiactive = self.setup_active_field == "api_key" and not self.setup_use_demo_key
            pygame.draw.rect(self.screen, (8, 15, 26), apirect, border_radius=7)
            pygame.draw.rect(
                self.screen,
                _C_GOLD if apiactive else (65, 80, 100),
                apirect,
                2 if apiactive else 1,
                border_radius=7,
            )
            if self.setup_use_demo_key:
                displaykey = "Demo key selected"
                keycolor = _C_MUTED
            elif self.setup_api_key:
                displaykey = "•" * min(34, max(8, len(self.setup_api_key) - 4)) + self.setup_api_key[-4:]
                keycolor = _C_TEXT
            else:
                displaykey = "Paste your sk-… key"
                keycolor = _C_MUTED
            keysurface = self.main_font.render(displaykey, True, keycolor)
            keysurface.set_alpha(fieldalpha)
            self.screen.blit(keysurface, (apirect.x + 14, apirect.centery - keysurface.get_height() // 2))

            demofill = (42, 49, 32) if self.setup_use_demo_key else (11, 20, 33)
            pygame.draw.rect(self.screen, demofill, demorect, border_radius=6)
            pygame.draw.rect(self.screen, (79, 91, 104), demorect, 1, border_radius=6)
            checkbox = pygame.Rect(demorect.x + 10, demorect.y + 8, 18, 18)
            pygame.draw.rect(self.screen, _C_GOLD if self.setup_use_demo_key else _C_MUTED, checkbox, 2, border_radius=3)
            if self.setup_use_demo_key:
                pygame.draw.line(self.screen, _C_GOLD_BRIGHT, (checkbox.x + 4, checkbox.centery), (checkbox.x + 8, checkbox.bottom - 4), 2)
                pygame.draw.line(self.screen, _C_GOLD_BRIGHT, (checkbox.x + 8, checkbox.bottom - 4), (checkbox.right - 3, checkbox.y + 4), 2)
            demolabel = self.small_font.render(
                "Use temporary demo key (expires in one month)",
                True,
                _C_TEXT,
            )
            demolabel.set_alpha(fieldalpha)
            self.screen.blit(demolabel, (demorect.x + 38, demorect.y + 9))

        if self.setup_error:
            errorsurface = self.small_font.render(self.setup_error, True, (241, 128, 128))
            self.screen.blit(errorsurface, (panel.x + 44, panel.bottom - 48))
        self._draw_button(continuebutton, "setup_continue", "CONTINUE", dt, primary=True)

    def _complete_setup(self):
        playername = self.setup_player_name.strip()
        if not playername:
            self.setup_error = "Enter a player name to continue."
            self.setup_active_field = "player_name"
            return
        if self.setup_mode == "online" and not self.setup_use_demo_key and not self.setup_api_key.strip():
            self.setup_error = "Enter an API key or enable the demo key."
            self.setup_active_field = "api_key"
            return
        self.settings.update({
            "setup_complete": True,
            "player_name": playername,
            "llm_mode": self.setup_mode,
            "online_api_key": self.setup_api_key.strip(),
            "use_demo_key": self.setup_use_demo_key,
            "volume": self.volume,
        })
        self.settings = savesettings(self.settings)
        self.setup_active = False
        self.setup_error = ""
        self.notice = f"Welcome, {playername}."
        self.notice_time = 2.4

    def _handle_setup_event(self, event):
        panel, namerect, optionrects, apirect, demorect, continuebutton = self._setup_controls()
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_TAB:
                self.setup_active_field = "api_key" if self.setup_active_field == "player_name" else "player_name"
            elif event.key == pygame.K_RETURN:
                self._complete_setup()
            elif event.key == pygame.K_BACKSPACE:
                if self.setup_active_field == "player_name":
                    self.setup_player_name = self.setup_player_name[:-1]
                elif not self.setup_use_demo_key:
                    self.setup_api_key = self.setup_api_key[:-1]
            elif event.unicode and event.unicode.isprintable():
                if self.setup_active_field == "player_name" and len(self.setup_player_name) < 36:
                    self.setup_player_name += event.unicode
                elif (
                    self.setup_active_field == "api_key"
                    and not self.setup_use_demo_key
                    and len(self.setup_api_key) < 256
                ):
                    self.setup_api_key += event.unicode
            return
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return
        if namerect.collidepoint(event.pos):
            self.setup_active_field = "player_name"
            return
        for mode, rect in optionrects.items():
            if rect.collidepoint(event.pos):
                self.setup_mode = mode
                self.setup_error = ""
                return
        if self.setup_mode == "online" and apirect.collidepoint(event.pos):
            self.setup_use_demo_key = False
            self.setup_active_field = "api_key"
            return
        if self.setup_mode == "online" and demorect.collidepoint(event.pos):
            self.setup_use_demo_key = not self.setup_use_demo_key
            if not self.setup_use_demo_key:
                self.setup_active_field = "api_key"
            return
        if continuebutton.collidepoint(event.pos):
            self._button_click("setup_continue", continuebutton)
            self._complete_setup()

    def _refresh_background(self):
        size = self.screen.get_size()
        if size == self._bg_size:
            return
        self._bg_size = size
        try:
            image = pygame.image.load(_MENU_BACKGROUND).convert()
            self._bg_surface = pygame.transform.smoothscale(image, size)
        except pygame.error:
            self._bg_surface = pygame.Surface(size)
            self._bg_surface.fill((8, 12, 20))

    def _play_click(self):
        if self.click_sound is not None:
            self.click_sound.play()

    def _handle_game_exit(self, destination):
        if destination != "main_menu":
            pygame.quit()
            sys.exit()

        current_surface = pygame.display.get_surface()
        self.is_fullscreen = bool(
            current_surface and current_surface.get_flags() & pygame.FULLSCREEN
        )
        flags = pygame.FULLSCREEN if self.is_fullscreen else 0
        size = (0, 0) if self.is_fullscreen else (WIDTH, HEIGHT)
        self.screen = pygame.display.set_mode(size, flags)
        set_window_icon()
        pygame.display.set_caption("Ebee Conquest - Main Menu")
        self.clock = pygame.time.Clock()
        self.settings = loadsettings()
        self.volume = int(self.settings.get("volume", 50))
        self.setup_player_name = str(self.settings.get("player_name") or "")
        self.setup_mode = str(self.settings.get("llm_mode") or "online")
        self.setup_api_key = str(self.settings.get("online_api_key") or "")
        self.setup_use_demo_key = bool(self.settings.get("use_demo_key", True))
        self.running = True
        self.menu = "main"
        self.menu_transition = 0.0
        self.loadgame_open = False
        if self.click_sound is not None:
            self.click_sound.set_volume(self.volume / 250.0)
        self._bg_size = None
        self._refresh_background()
        self.bgm_path = _play_random_bgm(self.volume / 100.0)
        pygame.event.clear()

    def _set_menu(self, name):
        if name == self.menu:
            return
        self.menu = name
        self.menu_transition = 0.0
        if name == "scripts":
            self.script_menu._opened_at = pygame.time.get_ticks() / 1000.0
        self.pulses.emit(self.screen.get_rect().center, _C_GOLD, radius=220, duration=0.8, width=3)

    def _toggle_fullscreen(self):
        self.is_fullscreen = not self.is_fullscreen
        flags = pygame.FULLSCREEN if self.is_fullscreen else 0
        size = (0, 0) if self.is_fullscreen else (WIDTH, HEIGHT)
        self.screen = pygame.display.set_mode(size, flags)
        set_window_icon()
        self._bg_size = None
        self._refresh_background()
        self.pulses.emit(self.screen.get_rect().center, _C_BLUE, radius=260, duration=0.9, width=2)

    def _main_button_rects(self):
        w, h = self.screen.get_size()
        scale = 1.22 if self.is_fullscreen else max(0.9, min(1.08, w / WIDTH))
        button_w = int(312 * scale)
        button_h = int(56 * scale)
        gap = int(15 * scale)
        labels = [
            ("new_game", "NEW GAME"),
            ("load_game", "LOAD GAME"),
            ("scripts", "SCRIPTS"),
            ("settings", "SETTINGS"),
            ("quit", "QUIT"),
        ]
        total_h = len(labels) * button_h + (len(labels) - 1) * gap
        start_y = int(h * 0.5 - total_h * 0.42)
        start_x = int(w * 0.5 - button_w * 0.5)
        return [
            (key, label, pygame.Rect(start_x, start_y + i * (button_h + gap), button_w, button_h))
            for i, (key, label) in enumerate(labels)
        ]

    def _button_hover_value(self, key, hovered, dt, speed=10.0):
        motion = self.button_motion.setdefault(key, {"hover": 0.0, "press": 0.0})
        motion["hover"] = exp_lerp(motion["hover"], 1.0 if hovered else 0.0, speed, dt)
        motion["press"] = exp_lerp(motion["press"], 0.0, 13.0, dt)
        return motion

    def _button_click(self, key, rect):
        motion = self.button_motion.setdefault(key, {"hover": 0.0, "press": 0.0})
        motion["press"] = 1.0
        self.pulses.emit(rect.center, _C_GOLD_BRIGHT, radius=90, duration=0.45, width=2)
        self._play_click()

    def _draw_button(self, rect, key, label, dt, primary=False, danger=False):
        hovered = rect.collidepoint(self.mouse)
        motion = self._button_hover_value(key, hovered, dt)
        hover = motion["hover"]
        press = motion["press"]
        t = pygame.time.get_ticks() / 1000.0
        scale = 1.0 + hover * 0.055 - press * 0.035
        offset_x = math.sin(t * 2.2 + len(key)) * hover * 3.0
        draw_rect = scale_rect(rect, scale, (offset_x, 0))
        radius = 8

        accent = _C_DANGER if danger else (_C_BLUE if not primary else _C_GOLD)
        draw_soft_glow(self.screen, draw_rect, accent, hover * 0.95 + press * 0.9, radius=radius, rings=5)
        top = mix_color((16, 25, 42), (34, 54, 86), hover)
        bottom = mix_color((6, 10, 18), (13, 24, 42), hover)
        if primary:
            top = mix_color((31, 56, 64), (98, 76, 30), hover * 0.85)
            bottom = mix_color((7, 24, 29), (42, 27, 10), hover * 0.7)
        if danger:
            top = mix_color((38, 30, 35), (90, 38, 45), hover)
            bottom = mix_color((18, 12, 17), (42, 14, 20), hover)

        _draw_vertical_gradient(self.screen, draw_rect, top, bottom, radius=radius)
        pygame.draw.rect(self.screen, mix_color((69, 84, 104), accent, hover), draw_rect, 1, border_radius=radius)
        pygame.draw.line(
            self.screen,
            (*mix_color((105, 121, 142), accent, 0.65 + hover * 0.35),),
            (draw_rect.x + 14, draw_rect.y + 2),
            (draw_rect.right - 14, draw_rect.y + 2),
            1,
        )
        draw_light_sweep(self.screen, draw_rect, t + len(key) * 0.33, accent, alpha=int(18 + hover * 34))

        glyph_x = draw_rect.x + 24
        glyph_y = draw_rect.centery
        glyph_color = mix_color((92, 116, 144), accent, 0.4 + hover * 0.6)
        glyph_radius = int(8 + hover * 4)
        pygame.draw.circle(self.screen, glyph_color, (glyph_x, glyph_y), glyph_radius, 1)
        pygame.draw.line(self.screen, glyph_color, (glyph_x - 12, glyph_y), (glyph_x + 12, glyph_y), 1)
        pygame.draw.line(self.screen, glyph_color, (glyph_x, glyph_y - 12), (glyph_x, glyph_y + 12), 1)

        text_color = mix_color(_C_TEXT, _C_GOLD_BRIGHT if primary else (226, 236, 248), hover)
        font = self.heading_font if draw_rect.height >= 60 else self.main_font
        text_surface = font.render(label, True, text_color)
        text_rect = text_surface.get_rect(center=(draw_rect.centerx + int(hover * 4), draw_rect.centery))
        self.screen.blit(text_surface, text_rect)
        return hovered

    def _draw_background(self, dt):
        self._refresh_background()
        w, h = self.screen.get_size()
        t = pygame.time.get_ticks() / 1000.0
        if self._bg_surface:
            self.screen.blit(self._bg_surface, (0, 0))

        wash = pygame.Surface((w, h), pygame.SRCALPHA)
        wash.fill((2, 6, 14, 132))
        pygame.draw.rect(wash, (0, 0, 0, 98), pygame.Rect(0, 0, int(w * 0.34), h))
        pygame.draw.rect(wash, (0, 0, 0, 74), pygame.Rect(int(w * 0.66), 0, int(w * 0.34), h))
        self.screen.blit(wash, (0, 0))

        self.particles.draw(self.screen, self.screen.get_rect(), t, color=(124, 196, 255), parallax=(0.0, 0.0))
        draw_scanlines(self.screen, self.screen.get_rect(), t, color=(74, 143, 231), alpha=14, spacing=32)
        self.pulses.update(dt)
        self.pulses.draw(self.screen)

    def _handle_main_click(self):
        for key, _label, rect in self._main_button_rects():
            if not rect.collidepoint(self.mouse):
                continue
            self._button_click(key, rect)
            if key == "new_game":
                self._launch_transition(rect)
                destination = run_game(
                    is_fullscreen=self.is_fullscreen,
                    volume=self.volume / 100.0,
                )
                self._handle_game_exit(destination)
            if key == "settings":
                self._set_menu("settings")
            elif key == "scripts":
                self._set_menu("scripts")
            elif key == "quit":
                self.running = False
            elif key == "load_game":
                self.loadgame_slots = savegamemodule.listsaveslots()
                self.loadgame_open = True
            return
                    
    def _loadgame_popup_rect(self):
        w, h = self.screen.get_size()
        popup_w = min(520, max(360, int(w * 0.42)))
        popup_h = min(560, max(360, int(h * 0.66)))
        rect = pygame.Rect(0, 0, popup_w, popup_h)
        rect.center = (w // 2, h // 2)
        return rect

    def _draw_loadgame_popup(self, dt):
        overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        self.screen.blit(overlay, (0, 0))

        popup = self._loadgame_popup_rect()
        draw_soft_glow(self.screen, popup, _C_GOLD, 0.32, radius=12, rings=6)
        _draw_vertical_gradient(self.screen, popup, (18, 27, 42), (6, 10, 18), radius=10)
        pygame.draw.rect(self.screen, (86, 78, 52), popup, 1, border_radius=10)

        title = self.heading_font.render("LOAD GAME", True, _C_GOLD_BRIGHT)
        self.screen.blit(title, (popup.x + 28, popup.y + 24))

        self.loadgame_slot_rects = {}
        row_h = 56
        gap = 10
        list_top = popup.y + 70
        list_bottom = popup.bottom - 70

        if not self.loadgame_slots:
            empty = self.main_font.render("No saved games found.", True, _C_MUTED)
            self.screen.blit(empty, (popup.x + 28, list_top + 10))
        else:
            y = list_top
            for entry in self.loadgame_slots:
                if y + row_h > list_bottom:
                    break
                row_rect = pygame.Rect(popup.x + 24, y, popup.width - 48, row_h)
                self.loadgame_slot_rects[entry["slot"]] = row_rect
                hovered = row_rect.collidepoint(self.mouse)
                top = (34, 54, 86) if hovered else (16, 25, 42)
                bottom = (13, 24, 42) if hovered else (6, 10, 18)
                _draw_vertical_gradient(self.screen, row_rect, top, bottom, radius=8)
                pygame.draw.rect(self.screen, _C_GOLD if hovered else (69, 84, 104), row_rect, 1, border_radius=8)
                label = self.main_font.render(entry["label"], True, _C_TEXT)
                self.screen.blit(label, (row_rect.x + 16, row_rect.y + 8))
                detail = f"{entry.get('playercountry') or 'Unknown'} - Turn {entry.get('turn') or 1}"
                detail_surface = self.small_font.render(detail, True, _C_MUTED)
                self.screen.blit(detail_surface, (row_rect.x + 16, row_rect.y + 30))
                y += row_h + gap

        back_w, back_h = 140, 44
        self.loadgame_back_rect = pygame.Rect(popup.centerx - back_w // 2, popup.bottom - back_h - 20, back_w, back_h)
        self._draw_button(self.loadgame_back_rect, "loadgame_back", "BACK", dt)

    def _handle_loadgame_click(self):
        if self.loadgame_back_rect.collidepoint(self.mouse):
            self._play_click()
            self.loadgame_open = False
            return
        for slotnumber, rect in self.loadgame_slot_rects.items():
            if rect.collidepoint(self.mouse):
                self._play_click()
                self.loadgame_open = False
                destination = run_game(
                    is_fullscreen=self.is_fullscreen,
                    volume=self.volume / 100.0,
                    load_slot=slotnumber,
                )
                self._handle_game_exit(destination)
          

    def _launch_transition(self, origin_rect):
        start_time = pygame.time.get_ticks() / 1000.0
        duration = 0.78
        while True:
            dt = self.clock.tick(144) / 1000.0
            self.mouse = pygame.mouse.get_pos()
            elapsed = pygame.time.get_ticks() / 1000.0 - start_time
            progress = clamp(elapsed / duration)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    return

            self._draw_background(dt)
            self._draw_main(dt)

            overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, int(185 * progress)))
            self.screen.blit(overlay, (0, 0))

            cx, cy = origin_rect.center
            radius = int(40 + progress * max(self.screen.get_size()) * 0.82)
            pulse_surface = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
            pygame.draw.circle(pulse_surface, (*_C_GOLD_BRIGHT, int(120 * (1.0 - progress))), (cx, cy), radius, 3)
            pygame.draw.circle(pulse_surface, (*_C_BLUE, int(70 * (1.0 - progress))), (cx, cy), max(1, radius // 2), 1)
            self.screen.blit(pulse_surface, (0, 0))

            pygame.display.flip()
            if progress >= 1.0:
                return

    def _draw_main(self, dt):
        for index, (key, label, rect) in enumerate(self._main_button_rects()):
            staged = clamp((self.menu_transition - index * 0.045) / 0.82)
            enter = ease_out_back(staged)
            draw_rect = rect.move(int((1.0 - enter) * 84), int((1.0 - enter) * 22))
            self._draw_button(draw_rect, key, label, dt, primary=key == "new_game", danger=key == "quit")

        if self.notice_time > 0.0 and self.notice:
            self.notice_time = max(0.0, self.notice_time - dt)
            alpha = int(230 * clamp(min(self.notice_time, 0.35) / 0.35))
            surf = self.main_font.render(self.notice, True, _C_TEXT)
            pad = 18
            rect = surf.get_rect()
            rect.inflate_ip(pad * 2, 18)
            rect.center = (self.screen.get_width() // 2, int(self.screen.get_height() * 0.84))
            toast = pygame.Surface(rect.size, pygame.SRCALPHA)
            pygame.draw.rect(toast, (7, 13, 22, alpha), toast.get_rect(), border_radius=8)
            pygame.draw.rect(toast, (*_C_GOLD, alpha), toast.get_rect(), 1, border_radius=8)
            toast.blit(surf, surf.get_rect(center=toast.get_rect().center))
            self.screen.blit(toast, rect.topleft)

    def _settings_controls(self):
        w, h = self.screen.get_size()
        panel_w = min(720, max(440, int(w * 0.54)))
        panel_h = min(530, h - 36)
        panel = pygame.Rect(0, 0, panel_w, panel_h)
        panel.center = (w // 2, h // 2)
        slider = pygame.Rect(panel.x + 54, panel.y + 118, panel.width - 108, 12)
        fullscreen = pygame.Rect(panel.x + 54, panel.y + 170, panel.width - 108, 50)
        aimode = pygame.Rect(panel.x + 54, panel.y + 238, panel.width - 108, 50)
        back = pygame.Rect(panel.x + 54, panel.y + 326, (panel.width - 124) // 2, 50)
        cache = pygame.Rect(back.right + 16, back.y, back.width, 50)
        reset_setup = pygame.Rect(panel.x + 54, panel.y + 394, panel.width - 108, 50)
        return panel, slider, fullscreen, aimode, back, cache, reset_setup

    def _draw_settings(self, dt):
        panel, slider, fullscreen, aimode, back, cache, reset_setup = self._settings_controls()
        t = pygame.time.get_ticks() / 1000.0
        enter = ease_out_back(self.menu_transition)
        panel = panel.move(0, int((1.0 - enter) * 42))
        draw_soft_glow(self.screen, panel, _C_GOLD, 0.32 + pulse(t, 1.5) * 0.12, radius=12, rings=7)
        _draw_vertical_gradient(self.screen, panel, (18, 27, 42), (6, 10, 18), radius=10)
        pygame.draw.rect(self.screen, (86, 78, 52), panel, 1, border_radius=10)
        draw_light_sweep(self.screen, panel, t, _C_GOLD_BRIGHT, alpha=22)

        title = self.heading_font.render("SETTINGS", True, _C_GOLD_BRIGHT)
        self.screen.blit(title, (panel.x + 34, panel.y + 30))
        volume_label = self.main_font.render(f"Volume: {self.volume}%", True, _C_TEXT)
        self.screen.blit(volume_label, (slider.x, slider.y - 34))

        pygame.draw.rect(self.screen, (36, 45, 60), slider, border_radius=6)
        fill = slider.copy()
        fill.width = int(slider.width * self.volume / 100)
        _draw_vertical_gradient(self.screen, fill, (83, 199, 132), (39, 130, 82), radius=6)
        knob_x = slider.x + fill.width
        knob_hover = abs(self.mouse[0] - knob_x) < 18 and abs(self.mouse[1] - slider.centery) < 18
        knob_radius = 10 + int((knob_hover or self.volume_dragging) * 3)
        pygame.draw.circle(self.screen, _C_TEXT, (knob_x, slider.centery), knob_radius)
        pygame.draw.circle(self.screen, _C_GOLD, (knob_x, slider.centery), knob_radius + 4, 1)

        fs_label = "FULLSCREEN: ON" if self.is_fullscreen else "FULLSCREEN: OFF"
        self._draw_button(fullscreen, "settings_fullscreen", fs_label, dt, primary=self.is_fullscreen)
        aimodelabels = {
            "online": "AI MODE: ONLINE LLM (ILMU)",
            "ollama": "AI MODE: OLLAMA LOCAL LLM",
            "graph": "AI MODE: GRAPH-BASED",
        }
        self._draw_button(
            aimode,
            "settings_ai_mode",
            aimodelabels.get(self.setup_mode, "AI MODE: GRAPH-BASED"),
            dt,
            primary=self.setup_mode == "online",
        )
        modenote = self.small_font.render(
            "Click to change · applies when the next campaign is launched",
            True,
            _C_MUTED,
        )
        self.screen.blit(modenote, (aimode.x, aimode.bottom + 9))
        self._draw_button(back, "settings_back", "BACK", dt)
        self._draw_button(cache, "settings_cache", "REMOVE CACHE", dt, danger=True)
        self._draw_button(
            reset_setup,
            "settings_reset_setup",
            "RESET FIRST-RUN SETUP",
            dt,
            danger=True,
        )

        warning = self.small_font.render("WARNING: REMOVING CACHE WILL CAUSE THE GAME TO LAUNCH SLOWER WHEN YOU RUN IT !!!", True, (236, 166, 166))
        self.screen.blit(warning, (panel.x + 54, panel.bottom - 50))

    def _handle_settings_click(self):
        panel, slider, fullscreen, aimode, back, cache, reset_setup = self._settings_controls()
        if slider.inflate(6, 24).collidepoint(self.mouse):
            self.volume_dragging = True
            self._update_volume_from_mouse(slider)
            self.pulses.emit((self.mouse[0], slider.centery), (83, 199, 132), radius=60, duration=0.45)
            return
        if fullscreen.collidepoint(self.mouse):
            self._button_click("settings_fullscreen", fullscreen)
            self._toggle_fullscreen()
            return
        if aimode.collidepoint(self.mouse):
            self._button_click("settings_ai_mode", aimode)
            modes = ("online", "ollama", "graph")
            currentmode = self.setup_mode if self.setup_mode in modes else "graph"
            self.setup_mode = modes[(modes.index(currentmode) + 1) % len(modes)]
            self.settings = updatesettings({"llm_mode": self.setup_mode})
            self.notice = f"AI mode set to {self.setup_mode.title()}."
            self.notice_time = 2.0
            return
        if back.collidepoint(self.mouse):
            self._button_click("settings_back", back)
            self._set_menu("main")
            return
        if cache.collidepoint(self.mouse):
            self._button_click("settings_cache", cache)
            remove_cache()
            self.notice = "Cache removed."
            self.notice_time = 2.2
            return
        if reset_setup.collidepoint(self.mouse):
            self._button_click("settings_reset_setup", reset_setup)
            self.settings = updatesettings({"setup_complete": False})
            self.setup_active = True
            self.setup_active_field = "player_name"
            self.setup_error = ""
            self.setup_expand = 1.0 if self.setup_mode == "online" else 0.0
            return

    def _update_volume_from_mouse(self, slider=None):
        if slider is None:
            (
                _panel,
                slider,
                _fullscreen,
                _aimode,
                _back,
                _cache,
                _reset_setup,
            ) = self._settings_controls()
        self.volume = int(clamp((self.mouse[0] - slider.x) / max(1, slider.width)) * 100)
        vol = self.volume / 100.0
        try:
            pygame.mixer.music.set_volume(vol)
        except pygame.error:
            pass
        if self.click_sound is not None:
            self.click_sound.set_volume(vol * 0.4)

        try:
            self.settings = updatesettings({"volume": self.volume})
        except OSError:
            pass
    def _draw_scripts(self):
        self.script_menu.draw(self.screen)

    def _handle_event(self, event):
        if event.type == pygame.QUIT:
            self.running = False
            return

        if self.setup_active:
            self._handle_setup_event(event)
            return

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            if self.menu == "main":
                self.running = False
            else:
                self._set_menu("main")
            return
        
        if self.loadgame_open:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self._handle_loadgame_click()
            return

        if self.menu == "scripts":

            
            action = self.script_menu.handle_event(event, self.mouse, self.screen.get_size())
            if action == "back":
                self._play_click()
                self._set_menu("main")
            elif action == "handled":
                self._play_click()
            if event.type == pygame.MOUSEBUTTONDOWN:
                self.pulses.emit(self.mouse, _C_BLUE, radius=72, duration=0.45)
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.menu == "main":
                self._handle_main_click()
            elif self.menu == "settings":
                self._handle_settings_click()

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.volume_dragging = False

        elif event.type == pygame.MOUSEMOTION and self.volume_dragging and self.menu == "settings":
            self._update_volume_from_mouse()

    def run(self):
        while self.running:
            dt = self.clock.tick(144) / 1000.0
            dt = max(0.0, min(0.05, dt))
            self.mouse = pygame.mouse.get_pos()
            self.menu_transition = min(1.0, self.menu_transition + dt * 2.9)

            for event in pygame.event.get():
                self._handle_event(event)

            self._draw_background(dt)
            if self.menu == "settings":
                self._draw_settings(dt)
            elif self.menu == "scripts":
                self._draw_scripts()
            else:
                self._draw_main(dt)
            if self.loadgame_open:
                self._draw_loadgame_popup(dt)
            if self.setup_active:
                self._draw_setup_popup(dt)
            pygame.display.flip()


def main():
    pygame.mixer.pre_init(44100, -16, 2, 1024)
    pygame.init()
    AnimatedMainMenu().run()
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
