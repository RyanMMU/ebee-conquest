import pygame

from game.animation import motion


def _surface_bytes(surface):
    return pygame.image.tobytes(surface, "RGBA")


def _reference_scanlines(surface, rect, time_value, color, alpha, spacing):
    overlay = pygame.Surface(rect.size, pygame.SRCALPHA)
    offset = int((time_value * 42.0) % max(1, spacing))
    for y in range(-spacing, rect.height + spacing, spacing):
        pygame.draw.line(
            overlay,
            (*color, alpha),
            (0, y + offset),
            (rect.width, y + offset),
            1,
        )
    surface.blit(overlay, rect.topleft)


def _reference_light_sweep(surface, rect, time_value, color, alpha):
    travel = rect.width + rect.height + 120
    sweep_x = int((time_value * 180.0) % travel) - rect.height - 60
    overlay = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.polygon(
        overlay,
        (*color, alpha),
        [
            (sweep_x, 0),
            (sweep_x + 36, 0),
            (sweep_x + rect.height + 36, rect.height),
            (sweep_x + rect.height, rect.height),
        ],
    )
    surface.blit(overlay, rect.topleft)


def test_cached_scanlines_match_original_pixels():
    rect = pygame.Rect(-12, 18, 140, 90)
    color = (74, 143, 231)
    for time_value in (0.0, 0.01, 0.3, 1.234, 50.0):
        actual = pygame.Surface((180, 160), pygame.SRCALPHA)
        expected = pygame.Surface((180, 160), pygame.SRCALPHA)
        actual.fill((7, 9, 11, 255))
        expected.fill((7, 9, 11, 255))
        clip = pygame.Rect(10, 5, 150, 140)
        actual.set_clip(clip)
        expected.set_clip(clip)

        motion.draw_scanlines(actual, rect, time_value, color, 16, 28)
        _reference_scanlines(expected, rect, time_value, color, 16, 28)

        assert actual.get_clip() == clip
        assert _surface_bytes(actual) == _surface_bytes(expected)


def test_cached_light_sweep_matches_original_pixels_and_restores_clip():
    rect = pygame.Rect(-12, 18, 140, 90)
    color = (255, 230, 150)
    for time_value in (0.0, 0.01, 0.3, 1.234, 50.0):
        actual = pygame.Surface((180, 160), pygame.SRCALPHA)
        expected = pygame.Surface((180, 160), pygame.SRCALPHA)
        actual.fill((7, 9, 11, 255))
        expected.fill((7, 9, 11, 255))
        clip = pygame.Rect(10, 5, 150, 140)
        actual.set_clip(clip)
        expected.set_clip(clip)

        motion.draw_light_sweep(actual, rect, time_value, color, 38)
        _reference_light_sweep(expected, rect, time_value, color, 38)

        assert actual.get_clip() == clip
        assert _surface_bytes(actual) == _surface_bytes(expected)


def test_ambient_particle_overlay_reuse_does_not_leave_old_pixels():
    reused = motion.AmbientParticleField(24, seed=203)
    reused.draw(
        pygame.Surface((220, 140), pygame.SRCALPHA),
        pygame.Rect(0, 0, 220, 140),
        0.25,
    )
    actual = pygame.Surface((220, 140), pygame.SRCALPHA)
    reused.draw(actual, actual.get_rect(), 12.5)

    fresh = motion.AmbientParticleField(24, seed=203)
    expected = pygame.Surface((220, 140), pygame.SRCALPHA)
    fresh.draw(expected, expected.get_rect(), 12.5)

    assert _surface_bytes(actual) == _surface_bytes(expected)


def test_fully_offscreen_pulses_do_not_allocate_draw_surfaces(monkeypatch):
    layer = motion.PulseLayer()
    layer.emit((-1000, -1000), radius=220, duration=10.0)
    destination = pygame.Surface((320, 180), pygame.SRCALPHA)
    original_surface = pygame.Surface
    allocation_count = 0

    def counted_surface(*args, **kwargs):
        nonlocal allocation_count
        allocation_count += 1
        return original_surface(*args, **kwargs)

    monkeypatch.setattr(motion.pygame, "Surface", counted_surface)
    layer.draw(destination)

    assert allocation_count == 0
