import pygame
import sys
import random
import json
import os
import re
from pygame.locals import *

pygame.init() # This should be the very first thing
pygame.mixer.init() # And this should be right after pygame.init()

# --- CONSTANTS ---

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
GRAY = (100, 100, 100)
DARK_GRAY = (30, 30, 30)
YELLOW = (255, 255, 0)
CYAN = (0, 255, 255)
MAGENTA = (255, 0, 255)
LIGHT_BLUE = (100, 150, 255)
DARK_BLUE = (10, 20, 40)
ORANGE = (255, 165, 0)

CELL_SIZE = 20

FPS = 15 # Base frames per second / game speed

# Files
LEADERBOARD_FILE = "leaderboard.json"
SAVE_FILE = "savegame.json"

# Powerup types: duration is in game ticks (FPS)
POWERUP_TYPES = {
    "speed_boost": {"color": CYAN, "duration": FPS * 5}, # 5 seconds boost
    "slow_down": {"color": MAGENTA, "duration": FPS * 5}, # 5 seconds slow
}

# --- INITIAL SETUP ---


desktop_info = pygame.display.Info()
screen_width, screen_height = desktop_info.current_w, desktop_info.current_h
if screen_width == 0 or screen_height == 0:
    screen_width, screen_height = 800, 600

screen = pygame.display.set_mode((screen_width, screen_height), pygame.FULLSCREEN)
pygame.display.set_caption("Snake Game - Fullscreen")

clock = pygame.time.Clock()
font_main = pygame.font.SysFont("consolas", 72, bold=True)
font_button = pygame.font.SysFont("consolas", 48)
font_small = pygame.font.SysFont("consolas", 30)
font_tiny = pygame.font.SysFont("consolas", 20)

# Load sounds with error handling
print("--- Sound Loading Debug ---")
try:
    # Determine the base path for assets in an executable
    # sys._MEIPASS is the temporary directory PyInstaller uses
    if hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
        print(f"Running from PyInstaller bundle. Base path: {base_path}")
    else:
        base_path = os.path.abspath(os.path.dirname(__file__))
        print(f"Running as script. Base path: {base_path}")

    bg_music_path = os.path.join(base_path, "assets", "background.mp3")
    eat_sound_path = os.path.join(base_path, "assets", "eat.wav")
    game_over_sound_path = os.path.join(base_path, "assets", "game_over.wav")

    print(f"Attempting to load background music from: {bg_music_path}")
    pygame.mixer.music.load(bg_music_path)
    pygame.mixer.music.play(-1) # Loop indefinitely
except pygame.error as e:
    print(f"ERROR: Could not load background music. Pygame error: {e}")
    # You might also want to print the path that caused the error here
    print(f"Path attempted: {bg_music_path}")
except Exception as e:
    print(f"An unexpected error occurred loading background music: {e}")

try:
    print(f"Attempting to load eat sound from: {eat_sound_path}")
    eat_sound = pygame.mixer.Sound(eat_sound_path)
except pygame.error as e:
    print(f"ERROR: Could not load eat sound. Pygame error: {e}")
    print(f"Path attempted: {eat_sound_path}")
    eat_sound = None
except Exception as e:
    print(f"An unexpected error occurred loading eat sound: {e}")

try:
    print(f"Attempting to load game over sound from: {game_over_sound_path}")
    game_over_sound = pygame.mixer.Sound(game_over_sound_path)
except pygame.error as e:
    print(f"ERROR: Could not load game over sound. Pygame error: {e}")
    print(f"Path attempted: {game_over_sound_path}")
    game_over_sound = None
except Exception as e:
    print(f"An unexpected error occurred loading game over sound: {e}")

print("--- End Sound Loading Debug ---")

# --- UTILS ---

def clamp(value, minimum, maximum):
    """Clamps a value between a minimum and maximum."""
    return max(minimum, min(value, maximum))

def load_leaderboard():
    """Loads the leaderboard from a JSON file."""
    if os.path.exists(LEADERBOARD_FILE):
        try:
            with open(LEADERBOARD_FILE, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            print("Warning: Leaderboard file is corrupted. Resetting leaderboard.")
            return [] # Return empty if JSON is malformed
        except Exception as e:
            print(f"An unexpected error occurred loading leaderboard: {e}")
            return []
    return []

def save_leaderboard(leaderboard):
    """Saves the top 5 scores to the leaderboard JSON file."""
    try:
        with open(LEADERBOARD_FILE, "w") as f:
            json.dump(leaderboard[:5], f, indent=4) # Save only top 5
    except Exception as e:
        print(f"Error saving leaderboard: {e}")

def save_score(name, score):
    """Adds a new score to the leaderboard and saves it."""
    name = re.sub(r"[^a-zA-Z0-9 ]", "", name).strip() # Sanitize name
    if not name:
        name = "Anonymous"
    leaderboard = load_leaderboard()
    leaderboard.append({"name": name, "score": score})
    leaderboard.sort(key=lambda x: x["score"], reverse=True) # Sort by score, highest first
    save_leaderboard(leaderboard)

def reset_leaderboard():
    """Resets the leaderboard by deleting the file."""
    if os.path.exists(LEADERBOARD_FILE):
        os.remove(LEADERBOARD_FILE)
        print("Leaderboard reset successfully.")
    else:
        print("Leaderboard file not found, nothing to reset.")
    save_leaderboard([]) # Ensure an empty file is created

def random_position(width, height):
    """Generates a random grid-aligned position within the screen boundaries."""
    return (
        random.randint(0, (width - CELL_SIZE) // CELL_SIZE) * CELL_SIZE,
        random.randint(0, (height - CELL_SIZE) // CELL_SIZE) * CELL_SIZE,
    )

def draw_button(rect, text, mouse_pos, base_color, hover_color, radius=12):
    """Draws a rounded rectangle button with hover effect."""
    color = hover_color if rect.collidepoint(mouse_pos) else base_color
    pygame.draw.rect(screen, color, rect, border_radius=radius)
    text_surf = font_button.render(text, True, BLACK)
    screen.blit(text_surf, text_surf.get_rect(center=rect.center))

def draw_text_center(text, y, font, color=WHITE):
    """Draws text centered horizontally on the screen at a given Y coordinate."""
    surf = font.render(text, True, color)
    screen.blit(surf, surf.get_rect(center=(screen.get_width() // 2, y)))

# --- SKINS ---

# Snake skins: list of dictionaries with 'name' and 'colors' for body and head
SNAKE_SKINS = [
    {"name": "Classic Green", "body_color": (0, 180, 0), "head_color": (0, 255, 0)},
    {"name": "Blue Neon", "body_color": (50, 100, 255), "head_color": (0, 200, 255)},
    {"name": "Fire", "body_color": (255, 80, 0), "head_color": (255, 180, 0)},
    {"name": "Purple", "body_color": (120, 0, 180), "head_color": (200, 0, 255)},
    {"name": "Rainbow", "body_color": None, "head_color": None},  # colors cycle
]

# Fruit skins: simple colored circles or squares with slight visual difference
FRUIT_SKINS = [
    {"name": "Red Apple", "color": (220, 30, 30)},
    {"name": "Orange", "color": (255, 165, 0)},
    {"name": "Blue Berry", "color": (40, 70, 200)},
    {"name": "Lime", "color": (50, 200, 50)},
    {"name": "Purple Grape", "color": (130, 30, 130)},
]

def draw_background():
    """Draws the game's animated background."""
    screen.fill(DARK_BLUE)
    # Draw diagonal stripes
    stripe_width = 60
    stripe_color = (20, 30, 70)
    for x in range(-screen.get_height(), screen.get_width(), stripe_width):
        pygame.draw.line(screen, stripe_color, (x, 0), (x + screen.get_height(), screen.get_height()), 15)
    # Overlay a transparent dark layer to soften stripes
    overlay = pygame.Surface(screen.get_size())
    overlay.set_alpha(80) # Semi-transparent
    overlay.fill(DARK_BLUE)
    screen.blit(overlay, (0, 0))

# --- GAME OBJECTS ---

class Snake:
    def __init__(self, start_pos, skin_idx=0):
        self.body = [start_pos]
        self.direction = (CELL_SIZE, 0) # Initial direction: right
        self.skin_idx = skin_idx
        self.speed_modifier = 0 # Not directly used for speed, but can be for other modifiers

        # For rainbow skin cycling colors
        self.rainbow_colors = [
            (255, 0, 0), (255, 127, 0), (255, 255, 0), # Red, Orange, Yellow
            (0, 255, 0), (0, 0, 255), (75, 0, 130), (148, 0, 211) # Green, Blue, Indigo, Violet
        ]

    def move(self):
        """Moves the snake by adding a new head and potentially removing the tail."""
        head_x, head_y = self.body[0]
        dx, dy = self.direction
        new_head = (head_x + dx, head_y + dy)
        self.body.insert(0, new_head)

    def shrink_tail(self):
        """Removes the last segment of the snake's body."""
        self.body.pop()

    def draw(self):
        """Draws the snake on the screen with its selected skin."""
        skin = SNAKE_SKINS[self.skin_idx]
        for i, segment in enumerate(self.body):
            if skin["name"] == "Rainbow":
                color = self.rainbow_colors[i % len(self.rainbow_colors)]
            else:
                color = skin["body_color"]

            if i == 0: # Head segment
                color = skin["head_color"] if skin["head_color"] else color
                # Pulsate head brightness for effect
                pulse = 30 + int(70 * (pygame.time.get_ticks() % 1000) / 1000) # Subtle pulsation
                color = (
                    clamp(color[0] + pulse, 0, 255),
                    clamp(color[1] + pulse, 0, 255),
                    clamp(color[2] + pulse, 0, 255),
                )
            pygame.draw.rect(screen, color, pygame.Rect(segment[0]+2, segment[1]+2, CELL_SIZE-4, CELL_SIZE-4), border_radius=5)

class Food:
    def __init__(self, position, skin_idx=0):
        self.position = position
        self.skin_idx = skin_idx
        self.particles = []

    def draw(self):
        """Draws the food item and its particle effects."""
        skin = FRUIT_SKINS[self.skin_idx]
        base_color = skin["color"]
        center = (self.position[0] + CELL_SIZE//2, self.position[1] + CELL_SIZE//2)
        # Draw white glow, then the fruit itself
        pygame.draw.circle(screen, WHITE, center, CELL_SIZE//2)
        pygame.draw.circle(screen, base_color, center, CELL_SIZE//2 - 4)
        
        # Draw particles animation
        for p in self.particles:
            pygame.draw.circle(screen, base_color, (int(p[0]), int(p[1])), max(1,int(p[2])))
            p[1] -= 0.5 # Move particles upwards
            p[2] -= 0.05 # Shrink particles over time
        self.particles = [p for p in self.particles if p[2] > 0] # Remove dead particles

    def spawn_particles(self):
        """Creates particles when food is eaten."""
        cx = self.position[0] + CELL_SIZE // 2
        cy = self.position[1] + CELL_SIZE // 2
        for _ in range(8): # Spawn 8 particles
            x = cx + random.uniform(-CELL_SIZE//2, CELL_SIZE//2)
            y = cy + random.uniform(-CELL_SIZE//2, CELL_SIZE//2)
            size = random.uniform(2, 4)
            self.particles.append([x, y, size])

class Obstacle:
    def __init__(self, position):
        self.position = position

    def draw(self):
        """Draws a static obstacle."""
        pygame.draw.rect(screen, (70, 70, 70), pygame.Rect(self.position[0], self.position[1], CELL_SIZE, CELL_SIZE), border_radius=4)

class Powerup:
    def __init__(self, position, type_):
        self.position = position
        self.type = type_
        self.color = POWERUP_TYPES[type_]["color"]
        self.duration = POWERUP_TYPES[type_]["duration"]

    def draw(self):
        """Draws a power-up with an indicator symbol."""
        pygame.draw.rect(screen, self.color, pygame.Rect(self.position[0], self.position[1], CELL_SIZE, CELL_SIZE), border_radius=4)
        center_x = self.position[0] + CELL_SIZE // 2
        center_y = self.position[1] + CELL_SIZE // 2
        
        # Draw symbols for powerup type
        if self.type == "speed_boost":
            pygame.draw.line(screen, WHITE, (center_x - 5, center_y), (center_x + 5, center_y), 2) # Horizontal line
            pygame.draw.line(screen, WHITE, (center_x, center_y - 5), (center_x, center_y + 5), 2) # Vertical line (plus sign)
        elif self.type == "slow_down":
            pygame.draw.line(screen, WHITE, (center_x - 5, center_y), (center_x + 5, center_y), 2) # Horizontal line (minus sign)

# --- GAME STATES and UI ---

# Global variables to hold current skin indexes
current_snake_skin = 0
current_fruit_skin = 0

def main_menu():
    """Displays the main menu and handles user interaction."""
    global screen, current_snake_skin, current_fruit_skin

    buttons = {
        "start": pygame.Rect(screen.get_width() // 2 - 150, screen.get_height() // 2 - 110, 300, 60),
        "skins": pygame.Rect(screen.get_width() // 2 - 150, screen.get_height() // 2 - 30, 300, 60),
        "instructions": pygame.Rect(screen.get_width() // 2 - 150, screen.get_height() // 2 + 50, 300, 60),
        "leaderboard": pygame.Rect(screen.get_width() // 2 - 150, screen.get_height() // 2 + 130, 300, 60),
        "reset": pygame.Rect(screen.get_width() // 2 - 150, screen.get_height() // 2 + 210, 300, 60),
        "exit": pygame.Rect(screen.get_width() // 2 - 150, screen.get_height() // 2 + 290, 300, 60),
    }

    while True:
        draw_background()
        draw_text_center("Snake Game", screen.get_height() // 4 - 50, font_main, YELLOW)

        # Show selected skins in preview boxes
        preview_y_start = screen.get_height() // 4 + 40

        # Draw snake skin preview box
        preview_snake_rect = pygame.Rect(screen.get_width() // 2 - 160, preview_y_start, 140, 70)
        pygame.draw.rect(screen, (50, 50, 50), preview_snake_rect, border_radius=12)
        draw_text_center("Snake Skin", preview_y_start - 30, font_small, WHITE)
        
        # Draw snake preview within its rect
        snake_skin = SNAKE_SKINS[current_snake_skin]
        # Simulate a small snake body for preview
        preview_snake_body_positions = [(preview_snake_rect.x + 12 + i * 20, preview_snake_rect.y + 25) for i in range(4)]
        
        for i, seg_pos in enumerate(preview_snake_body_positions):
            color = None
            if snake_skin["name"] == "Rainbow":
                colors = [
                    (255, 0, 0), (255, 127, 0), (255, 255, 0),
                    (0, 255, 0), (0, 0, 255), (75, 0, 130), (148, 0, 211)
                ]
                color = colors[i % len(colors)]
            else:
                color = snake_skin["body_color"]
            
            if i == 0: # Head segment
                color = snake_skin["head_color"] if snake_skin["head_color"] else color
            
            pygame.draw.rect(screen, color, pygame.Rect(seg_pos[0], seg_pos[1], CELL_SIZE - 6, CELL_SIZE - 6), border_radius=4)


        # Draw fruit skin preview box
        preview_fruit_rect = pygame.Rect(screen.get_width() // 2 + 30, preview_y_start, 140, 70)
        pygame.draw.rect(screen, (50, 50, 50), preview_fruit_rect, border_radius=12)
        draw_text_center("Fruit Skin", preview_y_start - 30, font_small, WHITE)
        
        # Draw fruit preview circle within its rect
        center_x = preview_fruit_rect.x + preview_fruit_rect.width // 2
        center_y = preview_fruit_rect.y + preview_fruit_rect.height // 2
        fruit_skin = FRUIT_SKINS[current_fruit_skin]
        pygame.draw.circle(screen, WHITE, (center_x, center_y), CELL_SIZE//2)
        pygame.draw.circle(screen, fruit_skin["color"], (center_x, center_y), CELL_SIZE//2 - 4)

        # High score
        leaderboard = load_leaderboard()
        if leaderboard:
            high_score = leaderboard[0]['score']
            hs_text = font_small.render(f"High Score: {high_score}", True, WHITE)
            screen.blit(hs_text, hs_text.get_rect(center=(screen.get_width() // 2, preview_fruit_rect.bottom + 20)))
        else:
            no_hs_text = font_small.render("No High Score yet. Be the first!", True, WHITE)
            screen.blit(no_hs_text, no_hs_text.get_rect(center=(screen.get_width() // 2, preview_fruit_rect.bottom + 20)))


        mouse_pos = pygame.mouse.get_pos()

        for key, rect in buttons.items():
            if key == "start":
                base = LIGHT_BLUE
                hover = (150, 190, 255)
            elif key == "exit":
                base = RED
                hover = (255, 100, 100)
            else:
                base = GRAY
                hover = (180, 180, 180)
            draw_button(rect, key.capitalize(), mouse_pos, base, hover)

        pygame.display.update()

        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                sys.exit()
            if event.type == KEYDOWN and event.key == K_ESCAPE:
                pygame.quit()
                sys.exit()
            if event.type == MOUSEBUTTONDOWN and event.button == 1:
                for key, rect in buttons.items():
                    if rect.collidepoint(event.pos):
                        if key == "start":
                            difficulty = {"speed": FPS} # Use FPS as base speed
                            game_loop(difficulty, current_snake_skin, current_fruit_skin)
                        elif key == "skins":
                            skin_selection_screen()
                        elif key == "instructions":
                            instructions_screen()
                        elif key == "leaderboard":
                            leaderboard_screen()
                        elif key == "reset":
                            reset_leaderboard()
                        elif key == "exit":
                            pygame.quit()
                            sys.exit()
        clock.tick(60)

def skin_selection_screen():
    """Allows players to select snake and fruit skins."""
    global current_snake_skin
    global current_fruit_skin
    global screen

    back_rect = pygame.Rect(20, 20, 120, 40)

    snake_rects = []
    fruit_rects = []
    margin_x = 80
    snake_y = 180
    fruit_y = snake_y + 160

    # Build rects for snake skins
    for idx in range(len(SNAKE_SKINS)):
        rect = pygame.Rect(margin_x + idx * 140, snake_y, 120, 80)
        snake_rects.append(rect)
    
    # Build rects for fruit skins
    for idx in range(len(FRUIT_SKINS)):
        rect = pygame.Rect(margin_x + idx * 140, fruit_y, 120, 80)
        fruit_rects.append(rect)

    while True:
        draw_background()
        draw_text_center("Select Your Skins", 80, font_main, YELLOW)

        # Draw snake skin options
        draw_text_center("Snake Skins", snake_y - 40, font_small, WHITE)
        mouse_pos = pygame.mouse.get_pos()
        for idx, rect in enumerate(snake_rects):
            base = LIGHT_BLUE if idx == current_snake_skin else GRAY
            hover = (150, 190, 255)
            color = hover if rect.collidepoint(mouse_pos) else base
            pygame.draw.rect(screen, color, rect, border_radius=12)
            skin = SNAKE_SKINS[idx]
            
            # Draw snake preview in rect center
            cx, cy = rect.center
            for i in range(4):
                block_x = cx - 30 + i * 20
                block_y = cy - 8 
                
                color_block = None
                if skin["name"] == "Rainbow":
                    colors = [
                        (255, 0, 0), (255, 127, 0), (255, 255, 0),
                        (0, 255, 0), (0, 0, 255), (75, 0, 130), (148, 0, 211)
                    ]
                    color_block = colors[i % len(colors)]
                else:
                    color_block = skin["body_color"]
                
                if i == 0: # Head
                    color_block = skin["head_color"] if skin["head_color"] else color_block
                
                pygame.draw.rect(screen, color_block, pygame.Rect(block_x+3, block_y+3, CELL_SIZE-6, CELL_SIZE-6), border_radius=3)

            # Label
            label_surf = font_tiny.render(skin["name"], True, WHITE)
            screen.blit(label_surf, label_surf.get_rect(center=(rect.centerx, rect.y + rect.height - 15)))

        # Draw fruit skin options
        draw_text_center("Fruit Skins", fruit_y - 40, font_small, WHITE)
        for idx, rect in enumerate(fruit_rects):
            base = LIGHT_BLUE if idx == current_fruit_skin else GRAY
            hover = (150, 190, 255)
            color = hover if rect.collidepoint(mouse_pos) else base
            pygame.draw.rect(screen, color, rect, border_radius=12)
            skin = FRUIT_SKINS[idx]
            cx, cy = rect.center
            pygame.draw.circle(screen, WHITE, (cx, cy - 8), CELL_SIZE//2) 
            pygame.draw.circle(screen, skin["color"], (cx, cy - 8), CELL_SIZE//2 - 4)
            label_surf = font_tiny.render(skin["name"], True, WHITE)
            screen.blit(label_surf, label_surf.get_rect(center=(rect.centerx, rect.y + rect.height - 15)))

        # Draw back button
        draw_button(back_rect, "Back", mouse_pos, GREEN, (0, 200, 0))

        pygame.display.update()

        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                sys.exit()
            if event.type == KEYDOWN and event.key == K_ESCAPE:
                return
            if event.type == MOUSEBUTTONDOWN and event.button == 1:
                for idx, rect in enumerate(snake_rects):
                    if rect.collidepoint(event.pos):
                        current_snake_skin = idx
                for idx, rect in enumerate(fruit_rects):
                    if rect.collidepoint(event.pos):
                        current_fruit_skin = idx
                if back_rect.collidepoint(event.pos):
                    return
        clock.tick(60)

def instructions_screen():
    """Displays game instructions."""
    global screen

    back_rect = pygame.Rect(20, 20, 120, 40)
    instructions = [
        "Use arrow keys or WASD to move the snake.",
        "Eat fruit to grow and increase score.",
        "Avoid hitting walls, obstacles and yourself.",
        "Pause with P. In pause menu: Resume, Restart, or Quit.",
        "Power-ups appear randomly: speed boost (cyan) & slow down (magenta).",
        "Save game (S) and Load game (L) during gameplay.",
        "Use 'Skins' menu to customize snake and fruit appearance.",
        "Press ESC anytime to exit to the main menu.",
        "Enjoy the colorful snake adventure!",
    ]

    while True:
        draw_background()
        draw_text_center("Instructions", 80, font_main, YELLOW)

        y = 150
        for line in instructions:
            line_surf = font_small.render(line, True, WHITE)
            screen.blit(line_surf, line_surf.get_rect(center=(screen.get_width() // 2, y)))
            y += 35

        mouse_pos = pygame.mouse.get_pos()
        draw_button(back_rect, "Back", mouse_pos, GREEN, (0, 200, 0))

        pygame.display.update()

        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                sys.exit()
            if event.type == KEYDOWN and event.key == K_ESCAPE:
                return
            if event.type == MOUSEBUTTONDOWN and event.button == 1 and back_rect.collidepoint(event.pos):
                return
        clock.tick(60)

def leaderboard_screen():
    """Displays the high scores leaderboard."""
    global screen

    back_rect = pygame.Rect(20, 20, 120, 40)

    while True:
        draw_background()
        draw_text_center("Leaderboard (Top 5)", 80, font_main, YELLOW)

        leaderboard = load_leaderboard()
        y = 180 # Adjusted starting Y for scores
        if leaderboard:
            for idx, entry in enumerate(leaderboard[:5]):
                line = f"{idx+1}. {entry['name']} - {entry['score']}"
                line_surf = font_small.render(line, True, WHITE)
                screen.blit(line_surf, line_surf.get_rect(center=(screen.get_width() // 2, y)))
                y += 40
        else:
            no_scores = font_small.render("No scores yet. Play to set a record!", True, WHITE)
            screen.blit(no_scores, no_scores.get_rect(center=(screen.get_width() // 2, y + 50))) # Center further down

        mouse_pos = pygame.mouse.get_pos()
        draw_button(back_rect, "Back", mouse_pos, GREEN, (0, 200, 0))

        pygame.display.update()

        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                sys.exit()
            if event.type == KEYDOWN and event.key == K_ESCAPE:
                return
            if event.type == MOUSEBUTTONDOWN and event.button == 1 and back_rect.collidepoint(event.pos):
                return
        clock.tick(60)

def input_name(score):
    """Allows the player to input their name for the leaderboard after game over."""
    input_box = pygame.Rect(screen.get_width() // 2 - 150, screen.get_height() // 2, 300, 50)
    color_inactive = WHITE
    color_active = LIGHT_BLUE
    color = color_inactive
    active = False
    text = ""
    done = False

    while not done:
        draw_background()
        draw_text_center(f"Your Score: {score}", screen.get_height() // 3, font_main, YELLOW)

        prompt = font_small.render("Enter your name (letters/numbers/spaces only):", True, WHITE)
        screen.blit(prompt, prompt.get_rect(center=(screen.get_width() // 2, screen.get_height() // 3 + 80)))

        txt_surface = font_button.render(text, True, color)
        # Dynamic width for input box, centered
        input_box.width = max(300, txt_surface.get_width() + 20)
        input_box.x = screen.get_width() // 2 - input_box.width // 2
        
        screen.blit(txt_surface, (input_box.x + 10, input_box.y + 5))
        pygame.draw.rect(screen, color, input_box, 2, border_radius=8)

        # Draw a "Submit" button
        submit_rect = pygame.Rect(screen.get_width() // 2 - 75, input_box.bottom + 20, 150, 50)
        mouse_pos = pygame.mouse.get_pos()
        draw_button(submit_rect, "Submit", mouse_pos, GREEN, (0, 200, 0))

        pygame.display.update()

        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                sys.exit()
            if event.type == MOUSEBUTTONDOWN:
                if input_box.collidepoint(event.pos):
                    active = not active
                elif submit_rect.collidepoint(event.pos):
                    done = True
                else:
                    active = False
                color = color_active if active else color_inactive
            if event.type == KEYDOWN:
                if active:
                    if event.key == K_RETURN:
                        done = True
                    elif event.key == K_BACKSPACE:
                        text = text[:-1]
                    else:
                        # Allow alphanumeric characters and space
                        if event.unicode.isalnum() or event.unicode == " ":
                            text += event.unicode
        clock.tick(60)

    save_score(text, score)

def save_game(state):
    """Saves the current game state to a JSON file."""
    try:
        with open(SAVE_FILE, "w") as f:
            json.dump(state, f, indent=4)
        print("Game saved successfully!")
    except Exception as e:
        print(f"Error saving game: {e}")

def load_game():
    """Loads a game state from a JSON file."""
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            print("Error: Save file corrupted. Cannot load game.")
            if os.path.exists(SAVE_FILE): # Optionally remove corrupted file
                os.remove(SAVE_FILE)
            return None
        except Exception as e:
            print(f"Error loading game: {e}")
            return None
    print("No save game found.")
    return None

def game_loop(difficulty, snake_skin_idx, fruit_skin_idx):
    """The main game loop for active gameplay."""
    global screen

    width, height = screen.get_size()
    grid_width = width // CELL_SIZE
    grid_height = height // CELL_SIZE

    start_pos = (grid_width // 2 * CELL_SIZE, grid_height // 2 * CELL_SIZE)
    snake = Snake(start_pos, snake_skin_idx)
    food = Food(random_position(width, height), fruit_skin_idx)
    obstacles = []
    powerups = []

    # Max obstacles based on percentage of grid cells, with a minimum
    max_obstacles = max(10, (grid_width * grid_height * 5) // 1000) 

    score = 0
    paused = False
    running = True

    powerup_active = None
    powerup_timer = 0

    # Set initial timer based on base FPS (difficulty speed)
    initial_game_speed_ms = int(1000 / difficulty["speed"])
    MOVE_EVENT = pygame.USEREVENT + 1
    pygame.time.set_timer(MOVE_EVENT, initial_game_speed_ms)

    loaded_state = load_game()
    if loaded_state:
        if load_game_state(loaded_state, snake, food, obstacles, powerups):
            score = loaded_state.get("score", 0)
            powerup_active = loaded_state.get("powerup_active", None)
            powerup_timer = loaded_state.get("powerup_timer", 0)
            # Re-apply speed if powerup was active on load
            if powerup_active == "speed_boost":
                pygame.time.set_timer(MOVE_EVENT, max(50, int(1000 / (difficulty["speed"] + 10))))
            elif powerup_active == "slow_down":
                pygame.time.set_timer(MOVE_EVENT, int(1000 / max(1, difficulty["speed"] - 5)))
        else:
            print("Failed to load game state. Starting a new game.")
            # Reset everything if load fails
            snake = Snake(start_pos, snake_skin_idx)
            food = Food(random_position(width, height), fruit_skin_idx)
            obstacles = []
            powerups = []
            score = 0
            powerup_active = None
            powerup_timer = 0
            pygame.time.set_timer(MOVE_EVENT, initial_game_speed_ms) # Reset timer to base speed

    while running:
        draw_background()

        for event in pygame.event.get():
            if event.type == QUIT:
                running = False

            if event.type == KEYDOWN:
                if not paused: # Only allow movement keys when not paused
                    if event.key in (K_UP, K_w) and snake.direction != (0, CELL_SIZE):
                        snake.direction = (0, -CELL_SIZE)
                    elif event.key in (K_DOWN, K_s) and snake.direction != (0, -CELL_SIZE):
                        snake.direction = (0, CELL_SIZE)
                    elif event.key in (K_LEFT, K_a) and snake.direction != (CELL_SIZE, 0):
                        snake.direction = (-CELL_SIZE, 0)
                    elif event.key in (K_RIGHT, K_d) and snake.direction != (-CELL_SIZE, 0):
                        snake.direction = (CELL_SIZE, 0)
                    elif event.key == K_s: # Save game
                        save_state = save_game_state(snake, food, obstacles, powerups, score, powerup_active, powerup_timer)
                        save_game(save_state)
                    elif event.key == K_l: # Load game
                        loaded_state = load_game()
                        if loaded_state:
                            # Re-initialize game objects with current skins before loading
                            snake = Snake(start_pos, snake_skin_idx) 
                            food = Food(random_position(width, height), fruit_skin_idx)
                            obstacles.clear()
                            powerups.clear()

                            if load_game_state(loaded_state, snake, food, obstacles, powerups):
                                score = loaded_state.get("score", 0)
                                powerup_active = loaded_state.get("powerup_active", None)
                                powerup_timer = loaded_state.get("powerup_timer", 0)
                                # Re-apply speed based on loaded state
                                if powerup_active == "speed_boost":
                                    pygame.time.set_timer(MOVE_EVENT, max(50, int(1000 / (difficulty["speed"] + 10))))
                                elif powerup_active == "slow_down":
                                    pygame.time.set_timer(MOVE_EVENT, int(1000 / max(1, difficulty["speed"] - 5)))
                            else:
                                print("Failed to load game state from file. Starting new game.")
                                # Reset to new game state if load fails
                                snake = Snake(start_pos, snake_skin_idx)
                                food = Food(random_position(width, height), fruit_skin_idx)
                                obstacles = []
                                powerups = []
                                score = 0
                                powerup_active = None
                                powerup_timer = 0
                                pygame.time.set_timer(MOVE_EVENT, initial_game_speed_ms) # Reset timer to base speed

                if event.key == K_p: # Toggle pause
                    paused = not paused
                    if paused:
                        pygame.mixer.music.pause()
                    else:
                        pygame.mixer.music.unpause()
                elif event.key == K_ESCAPE: # Exit to main menu
                    running = False


            if event.type == MOVE_EVENT and not paused:
                snake.move()

                head_x, head_y = snake.body[0]
                # Check for wall collision
                if not (0 <= head_x < width and 0 <= head_y < height):
                    game_over(score)
                    return

                # Check for self-collision
                if snake.body[0] in snake.body[1:]:
                    game_over(score)
                    return

                # Check for obstacle collision
                if any(obs.position == snake.body[0] for obs in obstacles):
                    game_over(score)
                    return

                # Check for food collision
                if snake.body[0] == food.position:
                    score += 1
                    if eat_sound:
                        eat_sound.play()
                    food.spawn_particles()

                    # Try to spawn powerup (20% chance)
                    if random.random() < 0.2:
                        attempts = 0
                        while attempts < 100: # Limit attempts to avoid infinite loops
                            ppos = random_position(width, height)
                            # Check if new position overlaps with snake, food, existing obstacles, or other powerups
                            all_occupied_positions = set(snake.body + [food.position] + 
                                                         [o.position for o in obstacles] + 
                                                         [p.position for p in powerups])
                            if ppos not in all_occupied_positions:
                                ptype = random.choice(list(POWERUP_TYPES.keys()))
                                powerups.append(Powerup(ppos, ptype))
                                break
                            attempts += 1

                    # Respawn food in a new valid position
                    while True:
                        new_pos = random_position(width, height)
                        all_occupied_positions = set(snake.body + [o.position for o in obstacles] + 
                                                     [p.position for p in powerups])
                        if new_pos not in all_occupied_positions:
                            food.position = new_pos
                            break

                    # Add obstacle every 20 points, up to max_obstacles
                    if score > 0 and score % 20 == 0 and len(obstacles) < max_obstacles:
                        attempts = 0
                        while attempts < 100:
                            pos = random_position(width, height)
                            all_occupied_positions = set(snake.body + [food.position] + 
                                                         [p.position for p in powerups] + 
                                                         [o.position for o in obstacles])
                            if pos not in all_occupied_positions:
                                obstacles.append(Obstacle(pos))
                                break
                            attempts += 1
                else:
                    snake.shrink_tail() # Snake moves forward if no food is eaten

                # Check for powerup collection
                for p in powerups:
                    if p.position == snake.body[0]:
                        powerup_active = p.type
                        powerup_timer = POWERUP_TYPES[p.type]["duration"]
                        powerups.remove(p)
                        # Immediately apply speed change
                        if powerup_active == "speed_boost":
                            pygame.time.set_timer(MOVE_EVENT, max(50, int(1000 / (difficulty["speed"] + 10))))
                        elif powerup_active == "slow_down":
                            pygame.time.set_timer(MOVE_EVENT, int(1000 / max(1, difficulty["speed"] - 5)))
                        break

                # Manage active powerup timer
                if powerup_active:
                    powerup_timer -= 1
                    if powerup_timer <= 0:
                        powerup_active = None
                        pygame.time.set_timer(MOVE_EVENT, initial_game_speed_ms) # Reset speed to normal

        # Drawing all game elements
        for obs in obstacles:
            obs.draw()
        for p in powerups:
            p.draw()
        snake.draw()
        food.draw()

        # Display score
        score_surf = font_small.render(f"Score: {score}", True, WHITE)
        screen.blit(score_surf, (10, 10))
        
        # Display active powerup and timer
        if powerup_active:
            powerup_text = f"Powerup: {powerup_active.replace('_', ' ').title()} ({powerup_timer // FPS}s)" # Display seconds
            powerup_surf = font_small.render(powerup_text, True, POWERUP_TYPES[powerup_active]["color"])
            screen.blit(powerup_surf, (10, 10 + score_surf.get_height() + 5))


        if paused:
            # Overlay a transparent black screen
            s = pygame.Surface((width, height))
            s.set_alpha(180)
            s.fill(BLACK)
            screen.blit(s, (0, 0))
            
            draw_text_center("Paused", height // 2 - 60, font_main, YELLOW)
            
            buttons = {
                "Resume": pygame.Rect(width // 2 - 150, height // 2, 300, 50),
                "Restart": pygame.Rect(width // 2 - 150, height // 2 + 70, 300, 50),
                "Quit": pygame.Rect(width // 2 - 150, height // 2 + 140, 300, 50),
            }
            mouse_pos = pygame.mouse.get_pos()
            for key, rect in buttons.items():
                draw_button(rect, key, mouse_pos, LIGHT_BLUE, (150, 190, 255))
            pygame.display.update() # Update screen while paused
            
            pause_running = True
            while pause_running: # Separate loop for pause state
                for event in pygame.event.get():
                    if event.type == QUIT:
                        pygame.quit()
                        sys.exit()
                    if event.type == MOUSEBUTTONDOWN and event.button == 1:
                        for key, rect in buttons.items():
                            if rect.collidepoint(event.pos):
                                if key == "Resume":
                                    pause_running = False
                                    paused = False
                                    pygame.mixer.music.unpause()
                                elif key == "Restart":
                                    return game_loop(difficulty, snake_skin_idx, fruit_skin_idx) # Restart game
                                elif key == "Quit":
                                    return # Go back to main menu
                    if event.type == KEYDOWN:
                        if event.key == K_p: # Allow P to unpause
                            pause_running = False
                            paused = False
                            pygame.mixer.music.unpause()
                        elif event.key == K_ESCAPE: # Go back to main menu
                            return 
                clock.tick(30) # Limit FPS while paused to save CPU
        else:
            pygame.display.update()
            clock.tick(FPS) # Maintain game speed when not paused

def save_game_state(snake, food, obstacles, powerups, score, powerup_active, powerup_timer):
    """Gathers the current game elements into a dictionary for saving."""
    return {
        "snake": snake.body,
        "direction": snake.direction,
        "food_pos": food.position,
        "food_skin_idx": food.skin_idx,
        "obstacles": [o.position for o in obstacles],
        "powerups": [{"pos": p.position, "type": p.type} for p in powerups],
        "score": score,
        "powerup_active": powerup_active,
        "powerup_timer": powerup_timer,
        "snake_skin_idx": snake.skin_idx,
    }

def load_game_state(state, snake, food, obstacles, powerups):
    """Loads game elements from a saved state dictionary."""
    try:
        snake.body = [tuple(pos) for pos in state["snake"]] # Ensure positions are tuples
        snake.direction = tuple(state["direction"])
        snake.skin_idx = state.get("snake_skin_idx", 0) # Use .get() for safer access
        food.position = tuple(state["food_pos"])
        food.skin_idx = state.get("food_skin_idx", 0)
        
        obstacles.clear()
        for pos in state["obstacles"]:
            obstacles.append(Obstacle(tuple(pos)))
        
        powerups.clear()
        for p in state["powerups"]:
            powerups.append(Powerup(tuple(p["pos"]), p["type"]))
        return True
    except KeyError as e:
        print(f"Failed to load game state: Missing expected data '{e}'. Save file might be corrupted or from an older version.")
        return False
    except TypeError as e:
        print(f"Failed to load game state: Type error '{e}'. Data format might be incorrect.")
        return False
    except Exception as e:
        print(f"An unexpected error occurred during loading game state: {e}")
        return False

def game_over(score):
    """Handles the game over sequence, including playing sound and prompting for name."""
    if game_over_sound:
        game_over_sound.play()
    input_name(score) # Prompt for name input
    main_menu() # Return to main menu after name input

if __name__ == "__main__":
    main_menu() # Start the game from the main menu