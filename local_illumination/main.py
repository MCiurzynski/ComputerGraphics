import os
from pathlib import Path
import tkinter as tk
from tkinter.filedialog import askopenfilename

import pygame

from src.phong import Camera
import torch

WIDTH = 800
HEIGHT = 800
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800


def control_handler(camera, pressed_keys):
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            return False
    keys = pygame.key.get_pressed()

    def is_pressed(pygame_key, tk_key):
        return keys[pygame_key] or tk_key in pressed_keys

    if is_pressed(pygame.K_w, "w"):
        camera.translate_z(5)
    if is_pressed(pygame.K_s, "s"):
        camera.translate_z(-5)
    if is_pressed(pygame.K_a, "a"):
        camera.translate_x(-5)
    if is_pressed(pygame.K_d, "d"):
        camera.translate_x(5)
    if is_pressed(pygame.K_SPACE, "space"):
        camera.translate_y(-5)
    if (
        keys[pygame.K_LSHIFT]
        or keys[pygame.K_RSHIFT]
        or "shift_l" in pressed_keys
        or "shift_r" in pressed_keys
    ):
        camera.translate_y(5)

    if is_pressed(pygame.K_ESCAPE, "escape"):
        return False
    return True


def main():
    # Initialize Tkinter interface
    root = tk.Tk()
    root.title("Local illumination Visualization")
    root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
    root.minsize(WINDOW_WIDTH, WINDOW_HEIGHT)
    root.maxsize(WINDOW_WIDTH, WINDOW_HEIGHT)
    root.resizable(False, False)

    # Initialize pygame frame
    pygame_frame = tk.Frame(root, width=WIDTH, height=HEIGHT)
    pygame_frame.pack(side=tk.LEFT, fill=tk.NONE, expand=False)
    pygame_frame.pack_propagate(False)

    control_panel = tk.Frame(
        root, width=WINDOW_WIDTH - WIDTH, height=WINDOW_HEIGHT, bg="#2c2c2c"
    )
    control_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

    tk.Label(control_panel, text="Ustawienia Phonga", fg="white", bg="#2c2c2c").pack(
        pady=20
    )

    # Necessary for proper pygame frame nesting
    root.update_idletasks()
    os.environ["SDL_WINDOWID"] = str(pygame_frame.winfo_id())
    if os.name != "nt":
        os.environ["SDL_VIDEODRIVER"] = "x11"

    current_file = Path(__file__).resolve()
    project_root = current_file.parent.parent
    assets_path = project_root / "assets" / "local illumination"

    filename = askopenfilename(initialdir=assets_path, parent=root)
    if filename == "":
        print("File not selected")
        root.destroy()
        return

    pygame.init()
    pygame.font.init()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    camera = Camera(WIDTH, HEIGHT, filename, device=device)
    screen = pygame.display.set_mode((WIDTH, HEIGHT))

    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 24)

    def update_light_position(event):
        if 0 <= event.x < WIDTH and 0 <= event.y < HEIGHT:
            camera.light[0] = event.x
            camera.light[1] = event.y

    pygame_frame.bind("<Button-1>", update_light_position)
    pygame_frame.bind("<B1-Motion>", update_light_position)

    pressed_keys = set()

    def on_key_press(event):
        pressed_keys.add(event.keysym.lower())

    def on_key_release(event):
        pressed_keys.discard(event.keysym.lower())

    root.bind_all("<KeyPress>", on_key_press)
    root.bind_all("<KeyRelease>", on_key_release)

    def update_fov(event):
        if event.num == 4:  # Scroll up
            pass
        elif event.num == 5:  # Scroll down
            pass
        if event.delta != 0:
            pass

    pygame_frame.bind("<Button-4>", update_fov)
    pygame_frame.bind("<Button-5>", update_fov)
    pygame_frame.bind("<MouseWheel>", update_fov)

    running = True

    def close_app():
        nonlocal running
        if not running:
            return
        running = False
        root.unbind_all("<KeyPress>")
        root.unbind_all("<KeyRelease>")
        if pygame.get_init():
            pygame.quit()
        root.destroy()

    def run_loop():
        if not running:
            return
        if not control_handler(camera, pressed_keys):
            close_app()
            return

        image = camera.draw()
        pygame.surfarray.blit_array(screen, image)
        fps = str(int(clock.get_fps()))
        fps_surface = font.render(f"FPS: {fps}", True, (0, 255, 0))
        screen.blit(fps_surface, (WIDTH - fps_surface.get_width() - 10, 10))
        pygame.display.flip()

        clock.tick(60)
        root.after(1, run_loop)

    root.protocol("WM_DELETE_WINDOW", close_app)
    root.after(100, run_loop)
    root.mainloop()


if __name__ == "__main__":
    main()
