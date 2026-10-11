import pygame
import random
import math
from array import array
from game.beat import Note, LANES, LANE_KEYS, LANE_LABELS, LANE_COLORS

WIDTH, HEIGHT = 480, 640
FPS = 60
HIT_Y = HEIGHT - 80
HIT_WINDOW = 30
BG = (15, 10, 25)
LANE_W = WIDTH // LANES

class GameEngine:
    def __init__(self):
        pygame.init()

        self.sounds = {}
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
            self.sounds = self.create_hit_sounds()
        except Exception:
            self.sounds = {}

        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Rhythm Tap")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("monospace", 26, bold=True)
        self.big_font = pygame.font.SysFont("monospace", 44, bold=True)
        self.reset()

    def create_hit_sounds(self):
        sample_rate = 22050
        duration = 0.12
        sounds = {}

        for grade, frequency in {
            "PERFECT": 880,
            "GREAT": 660,
            "OK": 440,
        }.items():
            samples = array("h")
            total_samples = int(sample_rate * duration)

            for i in range(total_samples):
                t = i / sample_rate
                envelope = min(
                    1.0,
                    t / 0.008,
                    (duration - t) / 0.03,
                )
                value = int(
                    9000
                    * envelope
                    * math.sin(2 * math.pi * frequency * t)
                )
                samples.append(value)

            sounds[grade] = pygame.mixer.Sound(buffer=samples.tobytes())

        return sounds

    def play_hit_sound(self, grade):
        try:
            sound = self.sounds.get(grade)
            if sound is not None:
                sound.play()
        except Exception:
            pass

    def reset(self):
        self.notes = []
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.misses = 0
        self.bpm = 120
        self.beat_interval = 60000 / self.bpm
        self.last_spawn_time = pygame.time.get_ticks()
        self.speed = 5
        self.frame = 0
        self.feedback = []  # (text, color, ttl, x, y)
        self.game_over = False
        self.grade_counts = {
            "PERFECT": 0,
            "GREAT": 0,
            "OK": 0,
            "MISS": 0,
        }

    def record_grade(self, grade):
        self.grade_counts[grade] += 1


    def get_accuracy(self):
        counts = self.grade_counts
        total = sum(counts.values())

        if total == 0:
            return 0.0

        weighted_points = (
            counts["PERFECT"] * 300
            + counts["GREAT"] * 200
            + counts["OK"] * 100
        )

        return (weighted_points / (total * 300)) * 100

    def spawn_note(self):
        lane = random.randint(0, LANES - 1)
        is_hold =  random.random() < 0.2
        self.notes.append(
            Note(lane, y=-30, speed=self.speed, is_hold=is_hold)
        )

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    self.reset()
                elif not self.game_over:
                    for i, key in enumerate(LANE_KEYS):
                        if event.key == key:
                            self.process_tap(i)
                            break

            elif event.type == pygame.KEYUP:
                for i, key in enumerate(LANE_KEYS):
                    if event.key == key:
                        self.release_hold(i)
                        break

        return True

    def process_tap(self, lane):
        # Find the closest available note in this lane.
        best = None
        best_dist = 9999

        for note in self.notes:
            if (
                note.lane == lane
                and not note.hit
                and not note.missed
                and not note.holding
            ):
                dist = abs(note.y + Note.HEIGHT // 2 - HIT_Y)
                if dist < best_dist:
                    best_dist = dist
                    best = note

        lane_x = lane * LANE_W + LANE_W // 2

        if best and best_dist <= HIT_WINDOW:
            if best.is_hold:
                # Start the hold, but do not award points yet.
                if best_dist < 8:
                    best.hold_grade = "PERFECT"
                    best.hold_points = 300
                    best.hold_color = (255, 220, 0)
                elif best_dist < 18:
                    best.hold_grade = "GREAT"
                    best.hold_points = 200
                    best.hold_color = (100, 220, 100)
                else:
                    best.hold_grade = "OK"
                    best.hold_points = 100
                    best.hold_color = (180, 180, 255)

                best.holding = True
                best.hold_started = pygame.time.get_ticks()
            else:
                # Existing tap-note scoring remains unchanged.
                best.hit = True

                if best_dist < 8:
                    grade, pts = "PERFECT", 300
                    col = (255, 220, 0)
                elif best_dist < 18:
                    grade, pts = "GREAT", 200
                    col = (100, 220, 100)
                else:
                    grade, pts = "OK", 100
                    col = (180, 180, 255)

                self.record_grade(grade)
                self.combo += 1
                self.max_combo = max(self.max_combo, self.combo)
                self.score += pts * max(1, self.combo // 5)
                self.play_hit_sound(grade)
                self.feedback.append(
                    [grade, col, 40, lane_x, HIT_Y - 30]
                )
        else:
            self.record_grade("MISS")
            self.combo = 0
            self.feedback.append(
                ["MISS", (220, 60, 60), 40, lane_x, HIT_Y - 30]
            )

    def complete_hold(self, note):
        if not note.holding or note.hit or note.missed:
            return

        lane_x = note.lane * LANE_W + LANE_W // 2
        note.holding = False
        note.hit = True
        self.record_grade(note.hold_grade)
        self.combo += 1
        self.max_combo = max(self.max_combo, self.combo)
        self.score += note.hold_points * max(1, self.combo // 5)

        self.play_hit_sound(note.hold_grade)
        self.feedback.append(
            [
                note.hold_grade,
                note.hold_color,
                40,
                lane_x,
                HIT_Y - 30,
            ]
        )

    

    def release_hold(self, lane):
        now = pygame.time.get_ticks()
        lane_x = lane * LANE_W + LANE_W // 2

        for note in self.notes:
            if note.lane != lane or not note.holding:
                continue

            elapsed = now - note.hold_started

            if elapsed >= note.hold_duration:
                self.complete_hold(note)
            else:
                note.holding = False
                note.missed = True
                self.combo = 0
                self.record_grade("MISS")
                self.misses += 1
                self.feedback.append(
                    ["MISS", (220, 60, 60), 40, lane_x, HIT_Y - 30]
                )


            
    def update(self):
        if self.game_over: return
        
        self.frame += 1

        now = pygame.time.get_ticks()

        if now - self.last_spawn_time >= self.beat_interval:
            self.spawn_note()
            self.last_spawn_time += self.beat_interval

        # Preserve the existing difficulty progression.
        if self.frame % 600 == 0:
            self.speed = min(10, self.speed + 0.5)


        for note in self.notes:
            note.update()

            if note.holding:
                elapsed = pygame.time.get_ticks() - note.hold_started
                if elapsed >= note.hold_duration:
                    self.complete_hold(note)

            if (
                not note.hit
                and not note.missed
                and not note.holding
                and note.y > HIT_Y + HIT_WINDOW + Note.HEIGHT
            ):
                note.missed = True
                self.record_grade("MISS")
                self.misses += 1
                self.combo = 0

        self.notes = [n for n in self.notes if not (n.hit or n.missed and n.y > HEIGHT + 10)]
        self.feedback = [[t,c,ttl-1,x,y] for t,c,ttl,x,y in self.feedback if ttl > 1]

        if self.misses >= 15:
            self.game_over = True

    def draw(self):
        self.screen.fill(BG)
        # Lane dividers
        for i in range(LANES + 1):
            pygame.draw.line(self.screen, (40,40,60), (i*LANE_W,0), (i*LANE_W,HEIGHT), 1)

        # Hit line
        pygame.draw.line(self.screen, (80,80,100), (0,HIT_Y), (WIDTH,HIT_Y), 2)
        for i in range(LANES):
            lx = i*LANE_W + LANE_W//2
            pygame.draw.rect(self.screen, LANE_COLORS[i],
                pygame.Rect(lx - Note.WIDTH//2, HIT_Y - 12, Note.WIDTH, 24), border_radius=6)
            lbl = self.font.render(LANE_LABELS[i], True, (20,20,20))
            self.screen.blit(lbl, (lx - lbl.get_width()//2, HIT_Y - 10))

        # Notes
        for note in self.notes:
            if note.hit: continue
            lx = note.lane * LANE_W + LANE_W // 2
            rect = note.get_rect(lx)
            pygame.draw.rect(self.screen, LANE_COLORS[note.lane], rect, border_radius=5)

        # Feedback
        for text, color, ttl, x, y in self.feedback:
            surf = self.font.render(text, True, color)
            alpha = min(255, ttl * 7)
            surf.set_alpha(alpha)
            self.screen.blit(surf, (x - surf.get_width()//2, y))

        # HUD
        sc = self.font.render(f"Score: {self.score}", True, (220,220,220))
        co = self.font.render(f"Combo: {self.combo}x", True, (255,220,80))
        mi = self.font.render(f"Misses: {self.misses}/15", True, (220,100,100))
        self.screen.blit(sc, (10, 10))
        self.screen.blit(co, (10, 40))
        self.screen.blit(mi, (WIDTH - mi.get_width() - 10, 10))
        
        if self.game_over:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 235))
            self.screen.blit(overlay, (0, 0))

            msg = self.big_font.render("GAME OVER", True, (220, 60, 60))
            score_font = pygame.font.SysFont("monospace", 20, bold=True)

            score_line = score_font.render(
                f"Final Score: {self.score}", True, (220, 220, 220)
            )
            combo_line = score_font.render(
                f"Max Combo: {self.max_combo}x", True, (200, 200, 200)
            )

            self.screen.blit(
                msg, (WIDTH // 2 - msg.get_width() // 2, 150)
            )
            self.screen.blit(
                score_line,
                (WIDTH // 2 - score_line.get_width() // 2, 215),
            )
            self.screen.blit(
                combo_line,
                (WIDTH // 2 - combo_line.get_width() // 2, 245),
            )

            counts = self.grade_counts

            perfect = score_font.render(
                f"PERFECT: {counts['PERFECT']}", True, (255, 220, 0)
            )
            great = score_font.render(
                f"GREAT: {counts['GREAT']}", True, (100, 220, 100)
            )
            ok = score_font.render(
                f"OK: {counts['OK']}", True, (180, 180, 255)
            )
            miss = score_font.render(
                f"MISS: {counts['MISS']}", True, (220, 80, 80)
            )

            self.screen.blit(perfect, (35, 310))
            self.screen.blit(great, (250, 310))
            self.screen.blit(ok, (35, 350))
            self.screen.blit(miss, (250, 350))

            accuracy = score_font.render(
                f"Accuracy: {self.get_accuracy():.2f}%",
                True,
                (220, 220, 220),
            )
            self.screen.blit(
                accuracy,
                (WIDTH // 2 - accuracy.get_width() // 2, 420),
            )

            restart = self.font.render(
                "Press R to Restart", True, (160, 160, 160)
            )
            self.screen.blit(
                restart,
                (WIDTH // 2 - restart.get_width() // 2, 500),
            )


        pygame.display.flip()


    def run(self):
        running = True
        while running:
            running = self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)
        pygame.quit()
