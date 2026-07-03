import random
import time

import pygame

from engine.gui import gui_gettroopbadgecandidatepairs


def _entries(rectangles):
    return [{"_visualrect": rectangle} for rectangle in rectangles]


def _bruteforce_overlap_pairs(rectangles):
    return [
        (firstindex, secondindex)
        for firstindex in range(len(rectangles))
        for secondindex in range(firstindex + 1, len(rectangles))
        if rectangles[firstindex].colliderect(rectangles[secondindex])
    ]


def test_troop_badge_candidate_pairs_match_bruteforce_and_legacy_order():
    generator = random.Random(1701)
    for _ in range(40):
        rectangles = [
            pygame.Rect(
                generator.randrange(-200, 1200),
                generator.randrange(-100, 800),
                generator.randrange(20, 180),
                generator.randrange(20, 80),
            )
            for _ in range(generator.randrange(0, 180))
        ]

        candidates = gui_gettroopbadgecandidatepairs(_entries(rectangles))
        assert candidates == sorted(candidates)
        assert set(_bruteforce_overlap_pairs(rectangles)).issubset(candidates)


def test_troop_badge_candidate_filter_reduces_sparse_pair_checks():
    rectangles = [
        pygame.Rect((index % 20) * 90, (index // 20) * 70, 64, 32)
        for index in range(200)
    ]
    allpaircount = len(rectangles) * (len(rectangles) - 1) // 2

    started = time.perf_counter()
    candidates = gui_gettroopbadgecandidatepairs(_entries(rectangles))
    elapsed = time.perf_counter() - started

    assert len(candidates) < allpaircount // 20
    assert elapsed < 0.05
