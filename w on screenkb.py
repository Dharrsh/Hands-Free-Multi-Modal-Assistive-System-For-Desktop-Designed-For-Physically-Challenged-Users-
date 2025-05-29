import cv2
import mediapipe as mp
import pyautogui
import pygame
import numpy as np
import speech_recognition as sr
import pyttsx3
import threading
from queue import Queue, Empty
import time
import re
import os
import subprocess
import time


class OnScreenKeyboard:
    def __init__(self, screen, screen_width, screen_height):
        self.screen = screen
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.active = False
        self.font = pygame.font.Font(None, 30)
        self.key_font = pygame.font.Font(None, 24)

        # Colors
        self.bg_color = (40, 40, 40)
        self.key_color = (80, 80, 80)
        self.text_color = (255, 255, 255)
        self.highlight_color = (120, 120, 240)

        # Keyboard dimensions
        self.kb_width = screen_width * 0.9
        self.kb_height = screen_height * 0.4
        self.kb_x = (screen_width - self.kb_width) // 2
        self.kb_y = screen_height - self.kb_height - 10

        # Text input field
        self.text_input = ""
        self.input_rect = pygame.Rect(self.kb_x, self.kb_y - 40, self.kb_width, 30)

        # Define keyboard layout
        self.layout = [
            ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0', 'Backspace'],
            ['q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p'],
            ['a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l'],
            ['z', 'x', 'c', 'v', 'b', 'n', 'm', '.', ','],
            ['Space', 'Enter', 'Clear', 'Close']
        ]
        self.keys = []
        self.build_keyboard()

        # Toggle button
        self.toggle_btn = pygame.Rect(10, screen_height - 40, 120, 30)

    def build_keyboard(self):
        """Build the keyboard with key rectangles"""
        self.keys = []
        num_rows = len(self.layout)

        for row_idx, row in enumerate(self.layout):
            num_keys = len(row)
            key_width = self.kb_width / max(len(layout_row) for layout_row in self.layout)
            key_height = self.kb_height / num_rows

            # Center this row
            row_width = num_keys * key_width
            start_x = self.kb_x + (self.kb_width - row_width) / 2

            for key_idx, key in enumerate(row):
                # Special cases for wider keys
                if key == 'Space':
                    key_rect = pygame.Rect(
                        start_x + key_idx * key_width,
                        self.kb_y + row_idx * key_height,
                        key_width * 3,
                        key_height
                    )
                elif key in ['Backspace', 'Enter', 'Clear', 'Close']:
                    key_rect = pygame.Rect(
                        start_x + key_idx * key_width,
                        self.kb_y + row_idx * key_height,
                        key_width * 1.5,
                        key_height
                    )
                else:
                    key_rect = pygame.Rect(
                        start_x + key_idx * key_width,
                        self.kb_y + row_idx * key_height,
                        key_width,
                        key_height
                    )

                self.keys.append({'rect': key_rect, 'key': key, 'row': row_idx, 'col': key_idx})

    def toggle(self):
        """Toggle keyboard visibility"""
        self.active = not self.active
        return self.active

    def process_key(self, key):
        """Process a key press"""
        if key == 'Backspace':
            if self.text_input:
                self.text_input = self.text_input[:-1]
                # Actually press backspace on the system
                pyautogui.press('backspace')
        elif key == 'Space':
            self.text_input += ' '
            # Actually press space on the system
            pyautogui.press('space')
        elif key == 'Enter':
            # Clear the internal buffer but don't type anything
            temp = self.text_input
            self.text_input = ""
            pyautogui.press('enter')
            return temp
        elif key == 'Clear':
            self.text_input = ""
        elif key == 'Close':
            self.active = False
        else:
            self.text_input += key
            # Actually type the character immediately
            pyautogui.write(key)
        return None

    def get_key_at_pos(self, pos):
        """Get the key at the given position"""
        # Convert global screen coordinates to pygame window coordinates
        window_pos = (pos[0] % self.screen_width, pos[1] % self.screen_height)

        for key in self.keys:
            if key['rect'].collidepoint(window_pos):
                return key['key']
        return None

    def draw(self):
        """Draw the keyboard on screen"""
        if not self.active:
            # Just draw the toggle button
            pygame.draw.rect(self.screen, (100, 100, 200), self.toggle_btn)
            toggle_text = self.font.render("Keyboard", True, self.text_color)
            self.screen.blit(toggle_text, (self.toggle_btn.x + 10, self.toggle_btn.y + 5))
            return

        # Draw keyboard background
        pygame.draw.rect(self.screen, self.bg_color, (self.kb_x, self.kb_y, self.kb_width, self.kb_height))

        # Draw text input field
        pygame.draw.rect(self.screen, (60, 60, 60), self.input_rect)
        text_surface = self.font.render(self.text_input, True, self.text_color)
        self.screen.blit(text_surface, (self.input_rect.x + 5, self.input_rect.y + 5))

        # Draw keys
        mouse_pos = pygame.mouse.get_pos()
        for key in self.keys:
            # Check if mouse is over this key for highlighting
            if key['rect'].collidepoint(mouse_pos):
                key_color = self.highlight_color
            else:
                key_color = self.key_color

            pygame.draw.rect(self.screen, key_color, key['rect'])
            pygame.draw.rect(self.screen, (120, 120, 120), key['rect'], 1)  # Key border

            # Key text
            key_text = self.key_font.render(key['key'], True, self.text_color)
            text_rect = key_text.get_rect(center=key['rect'].center)
            self.screen.blit(key_text, text_rect)

        # Draw toggle button
        pygame.draw.rect(self.screen, (100, 100, 200), self.toggle_btn)
        toggle_text = self.font.render("Hide Keyboard", True, self.text_color)
        self.screen.blit(toggle_text, (self.toggle_btn.x + 5, self.toggle_btn.y + 5))


class VoiceCommandHandler:
    def __init__(self, wake_phrases=None):
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.command_queue = Queue()
        self.is_listening = False
        self.is_actively_listening = False
        self.voice_feedback_enabled = True
        self.engine = pyttsx3.init()
        self.typing_mode = False
        self.typing_thread = None
        self.stop_typing_event = threading.Event()

        # Set default wake phrases if none provided
        if wake_phrases is None:
            self.wake_phrases = ["hey computer", "computer", "eye control", "eye commander"]
        else:
            self.wake_phrases = [phrase.lower() for phrase in wake_phrases]

        # Store multiple variations of each command for better recognition
        self.command_variations = {
            "track": ["track", "tracking", "enable tracking", "start tracking"],
            "stop tracking": ["stop", "stop tracking", "disable tracking", "pause tracking"],
            "right click": ["right", "right click", "secondary click"],
            "double click": ["double", "double click", "twice"],
            "scroll up": ["up", "scroll up", "page up"],
            "scroll down": ["down", "scroll down", "page down"],
            "enable feedback": ["enable feedback", "turn on feedback", "feedback on"],
            "disable feedback": ["disable feedback", "turn off feedback", "feedback off", "quiet"],
            "start typing": ["type", "typing", "start typing", "dictate"],
            "dont type": ["stop typing", "end typing", "dont type", "exit typing", "cancel typing"],
            "cancel command mode": ["cancel", "exit", "stop listening", "stop commands"],
            "toggle keyboard": ["keyboard", "show keyboard", "toggle keyboard", "on screen keyboard"],
            "launch keyboard": ["launch keyboard", "show keyboard", "open keyboard", "system keyboard",
                                "windows keyboard"],
            "close keyboard": ["close keyboard", "hide keyboard"],
        }

        self.wake_word_active = False
        self.wake_word_timeout = 12  # Longer timeout (8 seconds)
        self.wake_word_timer = None
        self.last_heard_text = ""  # Store last heard text for debugging
        self.last_command_time = 0

        # Set recognition parameters with lower energy threshold and longer pause
        self.recognizer.energy_threshold = 250  # Lower threshold for better sensitivity
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 1.0  # Longer pause for better phrase completion

        # Perform initial calibration
        self.calibrate_microphone()

    def launch_system_keyboard(self):
        """Launch the Windows on-screen keyboard"""
        try:
            # Try to close any existing OSK instances first
            try:
                os.system("taskkill /f /im osk.exe")
                time.sleep(0.5)  # Give it time to close
            except:
                pass

            # Launch the keyboard
            subprocess.Popen("osk")
            if self.voice_feedback_enabled:
                self.speak("On-screen keyboard launched")
            return True
        except Exception as e:
            print(f"Error launching on-screen keyboard: {e}")
            if self.voice_feedback_enabled:
                self.speak("Failed to launch on-screen keyboard")
            return False

    def close_system_keyboard(self):
        """Close the Windows on-screen keyboard"""
        try:
            os.system("taskkill /f /im osk.exe")
            if self.voice_feedback_enabled:
                self.speak("On-screen keyboard closed")
            return True
        except Exception as e:
            print(f"Error closing on-screen keyboard: {e}")
            return False

    def calibrate_microphone(self):
        """Calibrate the microphone for ambient noise"""
        print("Starting microphone calibration. Please remain silent...")
        try:
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=3)
            print(f"Calibration complete. Energy threshold: {self.recognizer.energy_threshold}")
            if hasattr(self, 'engine'):
                self.speak("Microphone calibrated.")
        except Exception as e:
            print(f"Calibration error: {e}")

    def speak(self, text):
        if self.voice_feedback_enabled:
            try:
                self.engine.say(text)
                self.engine.runAndWait()
            except RuntimeError:
                # If the engine is busy, stop it and try again
                self.engine.stop()
                try:
                    self.engine = pyttsx3.init()
                    self.engine.say(text)
                    self.engine.runAndWait()
                except:
                    pass  # If still fails, silently ignore to prevent disrupting the main program

    def start_listening(self):
        self.is_listening = True
        self.listener_thread = threading.Thread(target=self._listen_for_commands)
        self.listener_thread.daemon = True
        self.listener_thread.start()
        self.speak(f"Voice commands activated. Say {self.wake_phrases[0]} to start")

    def stop_listening(self):
        self.is_listening = False
        if hasattr(self, 'listener_thread'):
            self.listener_thread.join(timeout=1)
        self.speak("Voice commands deactivated")

    def _reset_wake_word_timer(self):
        """Reset the wake word timeout timer"""
        if self.wake_word_timer:
            self.wake_word_timer.cancel()

        # Set a timer to deactivate wake word after timeout
        self.wake_word_timer = threading.Timer(self.wake_word_timeout, self._deactivate_wake_word)
        self.wake_word_timer.daemon = True
        self.wake_word_timer.start()

    def _deactivate_wake_word(self):
        """Deactivate wake word mode after timeout"""
        if self.wake_word_active:
            self.wake_word_active = False
            print("Wake word deactivated due to timeout")
            if self.voice_feedback_enabled:
                self.speak("Command mode timed out")

    def _check_for_wake_phrase(self, text):
        """Check if any wake phrase is in the text"""
        text = text.lower()
        for phrase in self.wake_phrases:
            # Check for exact match or close match (e.g., "eye control" vs "i control")
            if phrase in text or self._is_similar_to(text, phrase):
                return True
        return False

    def _is_similar_to(self, text, phrase):
        """Check if text is phonetically similar to a phrase"""
        # Simple phonetic similarity checks
        similar_sounds = {
            "eye": ["i", "ai", "aye"],
            "hey": ["hay", "hi", "he"],
            "control": ["controller", "controls", "controll"],
            "computer": ["compute", "commuter", "computing"],
        }

        # Check original text for each word in phrase
        phrase_words = phrase.split()
        text_words = text.split()

        # If lengths are very different, likely not a match
        if abs(len(phrase_words) - len(text_words)) > 1:
            return False

        # Check each word
        matches = 0
        for p_word in phrase_words:
            # Check for direct match
            if p_word in text_words:
                matches += 1
                continue

            # Check for similar sounds
            for t_word in text_words:
                if p_word in similar_sounds and any(sim in t_word for sim in similar_sounds[p_word]):
                    matches += 1
                    break

        # Return true if we matched all words or all but one
        return matches >= max(1, len(phrase_words) - 1)

    def _listen_for_commands(self):
        while self.is_listening:
            try:
                # Set active listening indicator to true
                self.is_actively_listening = True

                with self.microphone as source:
                    # Use a shorter timeout for more responsive wake word detection
                    audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=3)

                # Set active listening indicator to false after getting audio
                self.is_actively_listening = False

                try:
                    text = self.recognizer.recognize_google(audio).lower()
                    self.last_heard_text = text  # Store for debugging
                    print(f"Recognized: {text}")  # Debug output

                    # Check for wake word if not already active
                    if not self.wake_word_active and self._check_for_wake_phrase(text):
                        self.wake_word_active = True
                        self._reset_wake_word_timer()
                        if self.voice_feedback_enabled:
                            self.speak("Command mode activated")
                        continue

                    # Process command if wake word is active
                    if self.wake_word_active:
                        command = self._parse_command(text)
                        if command:
                            self.command_queue.put(command)
                            self._reset_wake_word_timer()  # Reset timeout on successful command
                            self.last_command_time = time.time()
                            if self.voice_feedback_enabled:
                                self.speak(f"Command: {command}")

                    # Special case for typing mode
                    if self.typing_mode:
                        # In typing mode, we still need to check for exit commands
                        if any(exit_cmd in text for exit_cmd in self.command_variations["dont type"]):
                            self.command_queue.put("dont type")

                except sr.UnknownValueError:
                    pass
                except sr.RequestError:
                    if self.voice_feedback_enabled:
                        self.speak("Could not reach speech recognition service")

            except sr.WaitTimeoutError:
                self.is_actively_listening = False
                continue
            except Exception as e:
                self.is_actively_listening = False
                print(f"Error in voice recognition: {e}")
                continue

    def _parse_command(self, text):
        """Parse commands with better matching for variations"""
        # Clean the text
        text = text.lower().strip()

        # Check against all command variations
        for command, variations in self.command_variations.items():
            for variation in variations:
                if variation in text:
                    return command

        # If no direct match, try partial matching for short commands
        words = text.split()
        if len(words) <= 3:  # Only attempt partial matching for short phrases
            for command, variations in self.command_variations.items():
                for variation in variations:
                    # Check if most of the variation words appear in text
                    var_words = variation.split()
                    matches = sum(1 for w in var_words if w in words)
                    if matches >= max(1, len(var_words) - 1):  # Allow one word to be misheard
                        return command

        return None

    def get_command(self):
        try:
            return self.command_queue.get_nowait()
        except Empty:
            return None

    def start_typing_mode(self):
        """Start the typing mode where speech is converted to text input"""
        if self.typing_mode:
            return

        print("Typing mode activated!")  # Debugging
        self.typing_mode = True
        self.stop_typing_event.clear()

        # Launch the on-screen keyboard when typing mode starts
        self.launch_system_keyboard()

        self.typing_thread = threading.Thread(target=self._typing_listener)
        self.typing_thread.daemon = True
        self.typing_thread.start()
        self.speak("Typing mode activated. Speak clearly to type.")

    def stop_typing_mode(self):
        """Stop the typing mode"""
        if not self.typing_mode:
            return

        print("Typing mode deactivated!")  # Debugging
        self.typing_mode = False
        self.stop_typing_event.set()

        # Close the on-screen keyboard when typing mode ends
        self.close_system_keyboard()

        if self.typing_thread:
            self.typing_thread.join(timeout=1)
        self.speak("Typing mode deactivated")

    def _typing_listener(self):
        """Thread function that listens for speech and converts it to typing"""
        typing_recognizer = sr.Recognizer()
        typing_recognizer.energy_threshold = 250  # Lower threshold for typing
        typing_recognizer.dynamic_energy_threshold = True
        typing_recognizer.pause_threshold = 1.2  # Longer pause for complete sentences

        # Create a new microphone instance for typing mode
        typing_microphone = sr.Microphone()

        while self.typing_mode and not self.stop_typing_event.is_set():
            try:
                with typing_microphone as source:
                    if self.voice_feedback_enabled:
                        print("Listening for dictation...")

                    # Longer phrase time limit for dictation
                    audio = typing_recognizer.listen(source, timeout=2, phrase_time_limit=10)

                try:
                    text = typing_recognizer.recognize_google(audio)
                    print(f"Typing recognized: {text}")  # Debug output

                    # Check if the text contains stop command
                    if any(stop_cmd in text.lower() for stop_cmd in self.command_variations["dont type"]):
                        self.command_queue.put("dont type")
                        continue

                    # Type the recognized text
                    if text:
                        if self.voice_feedback_enabled:
                            print(f"Typing: {text}")
                        # Ensure the text field has focus first
                        pyautogui.click()
                        time.sleep(0.1)  # Small delay to ensure click registers
                        pyautogui.write(text + " ")

                except sr.UnknownValueError:
                    print("Speech not recognized")
                except sr.RequestError as e:
                    print(f"Could not request results: {e}")
                    if self.voice_feedback_enabled:
                        self.speak("Could not reach speech recognition service")

            except sr.WaitTimeoutError:
                print("Listen timeout")
                continue
            except Exception as e:
                print(f"Error in typing recognition: {e}")
                continue


def main():
    # Initialize main components
    cam = cv2.VideoCapture(0)
    face_mesh = mp.solutions.face_mesh.FaceMesh(refine_landmarks=True)
    screen_w, screen_h = pyautogui.size()

    # Initialize Pygame
    pygame.init()
    window_w, window_h = 640, 480
    screen = pygame.display.set_mode((window_w, window_h))
    pygame.display.set_caption("Eye Controlled Mouse with On-Screen Keyboard")

    # Colors and Fonts
    RED = (255, 0, 0)
    BLUE = (0, 0, 255)
    WHITE = (255, 255, 255)
    BLACK = (0, 0, 0)
    GREEN = (0, 255, 0)
    YELLOW = (255, 255, 0)
    ORANGE = (255, 165, 0)
    PURPLE = (128, 0, 128)
    font = pygame.font.Font(None, 36)
    small_font = pygame.font.Font(None, 24)

    # Tracking Settings
    BLINK_THRESHOLD = 0.008
    BLINK_DELAY = 0.3
    HOLD_CLICK_THRESHOLD = 0.008
    SCROLL_AMOUNT = 10

    # Initialize on-screen keyboard
    keyboard = OnScreenKeyboard(screen, window_w, window_h)

    # Initialize voice command handler with multiple wake phrases
    WAKE_PHRASES = ["hey computer", "computer", "eye control", "eye commander", "voice control"]
    voice_handler = VoiceCommandHandler(wake_phrases=WAKE_PHRASES)
    voice_handler.start_listening()

    # State variables
    tracking_enabled = True
    holding_click = False
    blink_counter = 0
    blink_detected = False

    # Add calibration button
    calibrate_button_rect = pygame.Rect(window_w - 150, window_h - 40, 140, 30)

    # Pygame main loop
    running = True
    last_debug_update = 0
    debug_info = []  # For storing debug information

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                # Add a key to force activate command mode for testing
                elif event.key == pygame.K_SPACE:
                    voice_handler.wake_word_active = True
                    voice_handler._reset_wake_word_timer()
                    if voice_handler.voice_feedback_enabled:
                        voice_handler.speak("Command mode activated manually")
            elif event.type == pygame.MOUSEBUTTONDOWN:
                # Check if calibrate button was clicked
                if calibrate_button_rect.collidepoint(event.pos):
                    voice_handler.calibrate_microphone()
                # Check if keyboard toggle button was clicked
                elif keyboard.toggle_btn.collidepoint(event.pos):
                    keyboard.toggle()

        # Handle voice commands
        command = voice_handler.get_command()
        if command:
            if command == "track":
                tracking_enabled = True
            elif command == "stop tracking":
                tracking_enabled = False
            elif command == "right click":
                pyautogui.rightClick()
            elif command == "double click":
                pyautogui.doubleClick()
            elif command == "scroll up":
                # Multiple scroll steps for more noticeable scrolling
                for _ in range(3):
                    pyautogui.press('pageup')
                if voice_handler.voice_feedback_enabled:
                    voice_handler.speak("Scrolling up")
            elif command == "scroll down":
                # Multiple scroll steps for more noticeable scrolling
                for _ in range(3):
                    pyautogui.press('pagedown')
                if voice_handler.voice_feedback_enabled:
                    voice_handler.speak("Scrolling down")
            elif command == "enable feedback":
                voice_handler.voice_feedback_enabled = True
                voice_handler.speak("Voice feedback enabled")
            elif command == "disable feedback":
                voice_handler.speak("Voice feedback disabled")
                voice_handler.voice_feedback_enabled = False
            elif command == "start typing":
                voice_handler.start_typing_mode()
            elif command == "dont type":
                voice_handler.stop_typing_mode()
            elif command == "cancel command mode":
                voice_handler.wake_word_active = False
                if voice_handler.voice_feedback_enabled:
                    voice_handler.speak("Command mode deactivated")


            elif command == "launch keyboard":
                voice_handler.launch_system_keyboard()
            elif command == "close keyboard":
                voice_handler.close_system_keyboard()
            elif command == "toggle keyboard":
                if voice_handler.launch_system_keyboard():  # Try to launch
                    pass  # If successful, we're done
                else:
                    voice_handler.close_system_keyboard()
            elif command == "toggle keyboard":
                keyboard_active = keyboard.toggle()
                if voice_handler.voice_feedback_enabled:
                    voice_handler.speak(f"Keyboard {'activated' if keyboard_active else 'deactivated'}")

        # Process eye tracking
        _, frame = cam.read()
        frame = cv2.flip(frame, 1)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        output = face_mesh.process(rgb_frame)
        landmark_points = output.multi_face_landmarks
        frame_h, frame_w, _ = frame.shape

        if landmark_points and tracking_enabled:
            landmarks = landmark_points[0].landmark

            # Move cursor using eye landmarks
            for id, landmark in enumerate(landmarks[474:478]):
                x = int(landmark.x * frame_w)
                y = int(landmark.y * frame_h)
                if id == 1:
                    screen_x = screen_w * landmark.x
                    screen_y = screen_h * landmark.y
                    pyautogui.moveTo(screen_x, screen_y)
                cv2.circle(frame, (x, y), 5, BLUE, -1)

            # Blink detection
            left_eye = [landmarks[145], landmarks[159]]
            right_eye = [landmarks[374], landmarks[386]]

            left_eye_distance = left_eye[0].y - left_eye[1].y
            right_eye_distance = right_eye[0].y - right_eye[1].y

            # Normal Click (Right Eye Blink)
            # In the section where right eye blink is detected (around line 690-700)
            if right_eye_distance < BLINK_THRESHOLD:
                # If keyboard is active and visible, check for key presses
                if keyboard.active:
                    cursor_x, cursor_y = pyautogui.position()
                    key_pressed = keyboard.get_key_at_pos((cursor_x, cursor_y))
                    if key_pressed:
                        text_result = keyboard.process_key(key_pressed)
                        if text_result:
                            # If Enter was pressed, type the text
                            pyautogui.write(text_result)
                            # Add a print statement to debug
                            print(f"Typing text: {text_result}")
                else:
                    # Normal click behavior when keyboard is not active
                    pyautogui.click()

                pyautogui.sleep(BLINK_DELAY)
                blink_detected = True
                blink_counter += 1
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

        # Update display
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame = np.rot90(frame)
        frame = pygame.surfarray.make_surface(frame)
        screen.blit(frame, (0, 0))

        # Display tracking status
        status_text = "Tracking: " + ("Enabled" if tracking_enabled else "Disabled")
        status_surface = font.render(status_text, True, GREEN if tracking_enabled else RED)
        screen.blit(status_surface, (10, 10))

        # Display cursor position
        cursor_x, cursor_y = pyautogui.position()
        cursor_text = font.render(f"Cursor: ({cursor_x}, {cursor_y})", True, WHITE)
        screen.blit(cursor_text, (10, 40))

        # Display blink counter
        blink_text = font.render(f"Blinks: {blink_counter}", True, WHITE)
        screen.blit(blink_text, (10, 70))

        # Display voice feedback status
        feedback_text = font.render(
            f"Voice Feedback: {'On' if voice_handler.voice_feedback_enabled else 'Off'}",
            True,
            GREEN if voice_handler.voice_feedback_enabled else RED
        )
        screen.blit(feedback_text, (10, 100))

        # Display wake word status
        wake_word_text = font.render(
            f"Command Mode: {'Active' if voice_handler.wake_word_active else 'Inactive'}",
            True,
            ORANGE if voice_handler.wake_word_active else WHITE
        )
        screen.blit(wake_word_text, (10, 130))

        # Display hold click indicator
        if holding_click:
            hold_text = font.render("Holding Click", True, RED)
            screen.blit(hold_text, (10, 160))

        # Display typing mode indicator
        typing_status = "Active" if voice_handler.typing_mode else "Inactive"
        typing_color = GREEN if voice_handler.typing_mode else WHITE
        typing_text = font.render(f"Typing Mode: {typing_status}", True, typing_color)
        screen.blit(typing_text, (10, 190))

        # Display keyboard status
        keyboard_status = "Active" if keyboard.active else "Inactive"
        keyboard_color = GREEN if keyboard.active else WHITE
        keyboard_text = font.render(f"Keyboard: {keyboard_status}", True, keyboard_color)
        screen.blit(keyboard_text, (10, 220))

        # Display last heard text for debugging (update every 2 seconds)
        current_time = time.time()
        if current_time - last_debug_update > 2:
            last_debug_update = current_time
            if voice_handler.last_heard_text:
                # Add to debug info list (keep last 3 entries)
                debug_info.append(voice_handler.last_heard_text)
                if len(debug_info) > 3:
                    debug_info.pop(0)
                voice_handler.last_heard_text = ""

        # Display debug info
        debug_y = 250
        debug_text = font.render("Last Heard:", True, PURPLE)
        screen.blit(debug_text, (10, debug_y))

        for i, text in enumerate(debug_info):
            text_surf = small_font.render(text, True, WHITE)
            screen.blit(text_surf, (10, debug_y + 30 + i * 20))

        # Draw microphone listening indicator
        if voice_handler.is_actively_listening:
            pygame.draw.circle(screen, YELLOW, (window_w - 30, 30), 10)
            mic_text = font.render("Listening", True, YELLOW)
            screen.blit(mic_text, (window_w - 120, 20))

        # Draw wake word active indicator
        if voice_handler.wake_word_active:
            pygame.draw.circle(screen, ORANGE, (window_w - 30, 60), 10)
            cmd_text = font.render("Command Mode", True, ORANGE)
            screen.blit(cmd_text, (window_w - 150, 50))

        # Draw typing mode listening indicator
        if voice_handler.typing_mode:
            pygame.draw.circle(screen, GREEN, (window_w - 30, 90), 10)
            typing_ind_text = font.render("Typing Active", True, GREEN)
            screen.blit(typing_ind_text, (window_w - 140, 80))

        # Draw blink indicator
        if blink_detected:
            pygame.draw.circle(screen, RED, (window_w - 30, 120), 10)
            blink_ind_text = font.render("Blink", True, RED)
            screen.blit(blink_ind_text, (window_w - 80, 110))

        # Display wake word instructions with multiple options
        wake_instr = small_font.render("Say any of these to activate: " + ", ".join(WAKE_PHRASES[:3]) + "...", True,
                                       WHITE)
        screen.blit(wake_instr, (window_w // 2 - 180, window_h - 80))

        # Display note about spacebar
        space_instr = small_font.render("Press SPACEBAR to manually activate command mode", True, WHITE)
        screen.blit(space_instr, (window_w // 2 - 180, window_h - 60))

        # Draw calibration button
        pygame.draw.rect(screen, BLUE, calibrate_button_rect)
        calibrate_text = font.render("Calibrate Mic", True, WHITE)
        screen.blit(calibrate_text, (window_w - 145, window_h - 38))

        # Draw the keyboard
        keyboard.draw()

        pygame.display.update()

    # Cleanup
    voice_handler.stop_listening()
    if hasattr(voice_handler, 'typing_mode') and voice_handler.typing_mode:
        voice_handler.stop_typing_mode()
    pygame.quit()
    cam.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
