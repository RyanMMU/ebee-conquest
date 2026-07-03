import pygame

from engine.scriptloader import ScriptUIManager


class _Manager:
    def callscript(self, *args, **kwargs):
        raise AssertionError("no script callbacks should run in this test")


def test_script_ui_fonts_are_created_once(monkeypatch):
    pygame.font.init()
    originalsysfont = pygame.font.SysFont
    calls = []

    def countedsysfont(*args, **kwargs):
        calls.append((args, kwargs))
        return originalsysfont(*args, **kwargs)

    monkeypatch.setattr(pygame.font, "SysFont", countedsysfont)
    monkeypatch.setattr(pygame.mouse, "get_pos", lambda: (0, 0))
    ui = ScriptUIManager(_Manager())
    surface = pygame.Surface((320, 180))

    ui.draw(surface)
    ui.draw(surface)

    assert len(calls) == 2
