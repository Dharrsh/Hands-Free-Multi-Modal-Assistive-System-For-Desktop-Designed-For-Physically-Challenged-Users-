import cv2
import mediapipe as mp
import pyautogui
import pygame
import numpy as np

# Initialize webcam
cam = cv2.VideoCapture(0)
face_mesh = mp.solutions.face_mesh.FaceMesh(refine_landmarks=True)
screen_w, screen_h = pyautogui.size()

# Initialize Pygame
pygame.init()
window_w, window_h = 640, 480
screen = pygame.display.set_mode((window_w, window_h))
pygame.display.set_caption("Eye Controlled Mouse")

# Colors
RED = (255, 0, 0)  # Blink indicator
BLUE = (0, 0, 255)  # Eye tracking dots
WHITE = (255, 255, 255)  # Text color
BLACK = (0, 0, 0)  # Background color

# Fonts
font = pygame.font.Font(None, 36)

# Sensitivity Settings
BLINK_THRESHOLD = 0.008  # Blink detection threshold
BLINK_DELAY = 0.3  # Delay for normal clicks
HOLD_CLICK_THRESHOLD = 0.008  # Sensitivity for holding click

holding_click = False  # Track if click is being held
blink_counter = 0  # Track number of blinks
blink_detected = False

# Pygame main loop
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    _, frame = cam.read()
    frame = cv2.flip(frame, 1)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    output = face_mesh.process(rgb_frame)
    landmark_points = output.multi_face_landmarks
    frame_h, frame_w, _ = frame.shape

    if landmark_points:
        landmarks = landmark_points[0].landmark

        # Move cursor using eye landmarks
        for id, landmark in enumerate(landmarks[474:478]):  # Eye tracking points
            x = int(landmark.x * frame_w)
            y = int(landmark.y * frame_h)
            if id == 1:
                screen_x = screen_w * landmark.x
                screen_y = screen_h * landmark.y
                pyautogui.moveTo(screen_x, screen_y)
            cv2.circle(frame, (x, y), 5, BLUE, -1)

        # Blink detection using eye landmarks
        left_eye = [landmarks[145], landmarks[159]]
        right_eye = [landmarks[374], landmarks[386]]

        left_eye_distance = left_eye[0].y - left_eye[1].y
        right_eye_distance = right_eye[0].y - right_eye[1].y

        # Normal Click (Right Eye Blink)
        if right_eye_distance < BLINK_THRESHOLD:
            pyautogui.click()
            pyautogui.sleep(BLINK_DELAY)  # Reduce false clicks
            blink_detected = True
            blink_counter += 1  # Increment blink counter
        else:
            blink_detected = False

        # Hold Click (Left Eye Closed)
        if left_eye_distance < HOLD_CLICK_THRESHOLD:
            if not holding_click:
                pyautogui.mouseDown()
                holding_click = True
        else:
            if holding_click:
                pyautogui.mouseUp()
                holding_click = False

    # Convert OpenCV frame to Pygame surface
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    frame = np.rot90(frame)
    frame = pygame.surfarray.make_surface(frame)
    screen.blit(frame, (0, 0))

    # Display cursor position
    cursor_x, cursor_y = pyautogui.position()
    cursor_text = font.render(f"Cursor: ({cursor_x}, {cursor_y})", True, WHITE)
    screen.blit(cursor_text, (10, 10))

    # Display blink counter
    blink_text = font.render(f"Blinks: {blink_counter}", True, WHITE)
    screen.blit(blink_text, (10, 40))

    # Display hold click indicator
    if holding_click:
        hold_text = font.render("Holding Click", True, RED)
        screen.blit(hold_text, (10, 70))

    # Draw red circle if blink detected
    if blink_detected:
        pygame.draw.circle(screen, RED, (window_w // 2, window_h // 2), 20)

    pygame.display.update()

pygame.quit()
cam.release()
cv2.destroyAllWindows()

