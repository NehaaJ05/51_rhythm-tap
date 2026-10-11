import pygame
import random

LANES = 4
LANE_KEYS = [pygame.K_d, pygame.K_f, pygame.K_j, pygame.K_k]
LANE_LABELS = ['D', 'F', 'J', 'K']
LANE_COLORS = [(220,80,80),(80,180,220),(100,220,100),(220,180,60)]
HOLD_DURATION = 1000
HOLD_HEIGHT = 300

class Note:
    WIDTH = 70
    HEIGHT = 20
    HOLD_HEIGHT = 300

    def __init__(self, lane, y=-30, speed=4, is_hold=False):
        self.lane = lane
        self.y = y
        self.speed = speed
        self.is_hold = is_hold
        self.hit = False
        self.missed = False

        # Hold-note state
        self.holding = False
        self.hold_started = 0
        self.hold_duration = 1000  # milliseconds
        self.hold_grade = None
        self.hold_points = 0
        self.hold_color = None

    def update(self):
        self.y += self.speed

    def get_rect(self, lane_x):
        if self.is_hold:
            hold_height = int(self.speed * 60 * self.hold_duration / 1000)
            hold_height = max(self.HEIGHT, hold_height)

            return pygame.Rect(
                lane_x - self.WIDTH // 2,
                int(self.y) - (hold_height - self.HEIGHT),
                self.WIDTH,
                hold_height,
            )

        return pygame.Rect(
            lane_x - self.WIDTH // 2,
            int(self.y),
            self.WIDTH,
            self.HEIGHT,
        )