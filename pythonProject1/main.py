import cv2
import mediapipe as mp
import pygame
import random
import sys
import numpy as np
import os

# ---------- Settings ----------
SCREEN_WIDTH = 640
SCREEN_HEIGHT = 480
FONT_SIZE = 30
SHIP_IMAGE_PATH = r"C:\Users\Ritesh\Downloads\WhatsApp Image 2025-09-15 at 4.36.53 PM.jpeg"

pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("AstroDodger Base Game")
clock = pygame.time.Clock()
font = pygame.font.SysFont("Arial", FONT_SIZE)

WHITE = (255, 255, 255)
RED = (255, 0, 0)
YELLOW = (255, 255, 0)
BLUE = (0, 0, 255)
GREEN = (0, 255, 0)

# ---------- Ship ----------
def build_ship_triangle():
    surf = pygame.Surface((50,50), pygame.SRCALPHA)
    pygame.draw.polygon(surf, GREEN, [(25,0),(50,50),(0,50)])
    return surf

def build_ship_diamond():
    surf = pygame.Surface((50,50), pygame.SRCALPHA)
    pygame.draw.polygon(surf, GREEN, [(25,0),(50,25),(25,50),(0,25)])
    return surf

def build_ship_from_image(path):
    if not os.path.exists(path):
        return build_ship_triangle()
    img = pygame.image.load(path).convert_alpha()
    img = pygame.transform.scale(img, (50,50))
    return img

# ---------- Mediapipe ----------
mp_face = mp.solutions.face_detection
face_detection = mp_face.FaceDetection(min_detection_confidence=0.7)
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(min_detection_confidence=0.5, min_tracking_confidence=0.5)

cap = cv2.VideoCapture(0)

# ---------- Wireframe ----------
def draw_nose_wireframe(detection):
    h, w = SCREEN_HEIGHT, SCREEN_WIDTH
    box = detection.location_data.relative_bounding_box
    x_min = int(box.xmin * w)
    y_min = int(box.ymin * h)
    box_width = int(box.width * w)
    box_height = int(box.height * h)
    nose = (x_min + box_width // 2, y_min + box_height // 2)
    pygame.draw.circle(screen, WHITE, nose, 3)
    return nose[0]

# ---------- Mouth ----------
def mouth_open(frame):
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb)
    if not results.multi_face_landmarks:
        return False
    landmarks = results.multi_face_landmarks[0].landmark
    h, w, _ = frame.shape
    top = int(landmarks[13].y * h)
    bottom = int(landmarks[14].y * h)
    return (bottom - top) > 15

# ---------- Game ----------
def game_loop(level, SHIP_IMG):
    spaceship_x = SCREEN_WIDTH // 2 - 25
    spaceship_y = SCREEN_HEIGHT - 100
    bullets = []
    asteroids = []
    frame_count = 0
    score = 0
    last_shot = 0
    shooting = False
    cooldown = False
    primary_face_box = None  # to lock the first detected face

    # Difficulty settings
    if level=="normal":
        ASTEROID_FREQ = 25
        asteroid_speed_range = [5,7,9]
        flicker = False
    else:  # hardest
        ASTEROID_FREQ = 15
        asteroid_speed_range = [12,14,16]
        flicker = True

    running = True
    while running:
        ret, frame = cap.read()
        if not ret:
            break
        frame = cv2.flip(frame,1)  # mirror camera
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = face_detection.process(rgb_frame)
        is_mouth_open = mouth_open(frame)

        # Face tracking (only first primary face)
        if results.detections:
            if primary_face_box is None:
                # lock onto the first detected face
                primary_face_box = results.detections[0].location_data.relative_bounding_box

            # find the detection that matches the primary face
            detection = results.detections[0]
            nose_x = draw_nose_wireframe(detection)
            spaceship_x = max(0, min(SCREEN_WIDTH-50, nose_x-25))

        now = pygame.time.get_ticks()
        if is_mouth_open and not cooldown:
            if not shooting:
                shooting = True
                last_shot = now
            if shooting and now-last_shot<2000:
                bullets.append({"x": spaceship_x+22, "y": spaceship_y, "speed":10})
            elif shooting and now-last_shot>=2000:
                shooting=False
                cooldown=True
                last_shot=now
        if cooldown and now-last_shot>=1000:
            cooldown=False

        for event in pygame.event.get():
            if event.type==pygame.QUIT:
                pygame.quit()
                cap.release()
                sys.exit()

        # Asteroids
        frame_count+=1
        if frame_count%ASTEROID_FREQ==0:
            size = random.randint(20,60)
            x = random.randint(0, SCREEN_WIDTH-size)
            speed = random.choice(asteroid_speed_range)
            color = random.choice([RED,YELLOW,BLUE])
            asteroids.append({"x":x,"y":-size,"size":size,"speed":speed,"color":color})

        for asteroid in asteroids:
            asteroid["y"] += asteroid["speed"]

        # Bullet update
        for bullet in bullets[:]:
            bullet["y"] -= bullet["speed"]
            if bullet["y"]<0:
                bullets.remove(bullet)
                continue
            for asteroid in asteroids[:]:
                if (bullet["x"]>asteroid["x"] and bullet["x"]<asteroid["x"]+asteroid["size"] and
                    bullet["y"]>asteroid["y"] and bullet["y"]<asteroid["y"]+asteroid["size"]):
                    asteroids.remove(asteroid)
                    bullets.remove(bullet)
                    score+=10
                    break

        # Collision check
        for asteroid in asteroids:
            if (spaceship_x<asteroid["x"]+asteroid["size"] and spaceship_x+50>asteroid["x"] and
                spaceship_y<asteroid["y"]+asteroid["size"] and spaceship_y+50>asteroid["y"]):
                return score

        asteroids = [a for a in asteroids if a["y"]<SCREEN_HEIGHT]

        # Draw camera
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_rgb = cv2.resize(frame_rgb,(SCREEN_WIDTH,SCREEN_HEIGHT))
        frame_surface = pygame.surfarray.make_surface(frame_rgb.swapaxes(0,1)).convert()
        screen.blit(frame_surface,(0,0))

        # Draw asteroids
        for asteroid in asteroids:
            color = asteroid["color"]
            if flicker:
                color = random.choice([RED,YELLOW,BLUE,GREEN,WHITE])
            pygame.draw.rect(screen, color, (asteroid["x"], asteroid["y"], asteroid["size"], asteroid["size"]))

        # Draw bullets
        for bullet in bullets:
            pygame.draw.rect(screen,GREEN,(bullet["x"],bullet["y"],5,10))

        # Draw ship
        screen.blit(SHIP_IMG,(spaceship_x,spaceship_y))

        # Draw score
        score_text = font.render(f"Score: {score}",True,WHITE)
        screen.blit(score_text,(10,10))

        pygame.display.flip()
        clock.tick(30)

# ---------- Menus ----------
def ship_menu():
    while True:
        screen.fill((0,0,0))
        title = font.render("Select Ship: 1-Triangle 2-Diamond 3-Image", True, WHITE)
        screen.blit(title,(50,SCREEN_HEIGHT//2-20))
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type==pygame.QUIT:
                pygame.quit()
                cap.release()
                sys.exit()
            if event.type==pygame.KEYDOWN:
                if event.key==pygame.K_1:
                    return build_ship_triangle()
                elif event.key==pygame.K_2:
                    return build_ship_diamond()
                elif event.key==pygame.K_3:
                    return build_ship_from_image(SHIP_IMAGE_PATH)

def level_menu():
    while True:
        screen.fill((0,0,0))
        title = font.render("Select Level: N-Normal H-Hardest", True, WHITE)
        screen.blit(title,(50,SCREEN_HEIGHT//2-20))
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type==pygame.QUIT:
                pygame.quit()
                cap.release()
                sys.exit()
            if event.type==pygame.KEYDOWN:
                if event.key==pygame.K_n:
                    return "normal"
                elif event.key==pygame.K_h:
                    return "hardest"

def draw_retry(score):
    screen.fill((0,0,0))
    score_text = font.render(f"Score: {score}", True, WHITE)
    screen.blit(score_text,(SCREEN_WIDTH//2-score_text.get_width()//2, SCREEN_HEIGHT//2-60))
    retry_text = font.render("Press R to Retry", True, WHITE)
    quit_text = font.render("Press Q to Quit", True, WHITE)
    screen.blit(retry_text,(SCREEN_WIDTH//2-retry_text.get_width()//2, SCREEN_HEIGHT//2))
    screen.blit(quit_text,(SCREEN_WIDTH//2-quit_text.get_width()//2, SCREEN_HEIGHT//2+40))
    pygame.display.flip()

# ---------- Main ----------
def main():
    SHIP_IMG = ship_menu()
    while True:
        level = level_menu()
        while True:
            score = game_loop(level, SHIP_IMG)
            draw_retry(score)
            waiting=True
            while waiting:
                for event in pygame.event.get():
                    if event.type==pygame.QUIT:
                        pygame.quit()
                        cap.release()
                        sys.exit()
                    if event.type==pygame.KEYDOWN:
                        if event.key==pygame.K_r:
                            waiting=False  # Retry same level & ship
                        elif event.key==pygame.K_q:
                            pygame.quit()
                            cap.release()
                            sys.exit()

if __name__=="__main__":
    main()
