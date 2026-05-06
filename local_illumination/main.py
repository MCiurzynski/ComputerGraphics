import pygame
from src.phong import Camera
from tkinter import Tk
from tkinter.filedialog import askopenfilename

WIDTH = 800
HEIGHT = 800

def control_handler(camera):
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            return False
    keys = pygame.key.get_pressed()

    mouse_buttons = pygame.mouse.get_pressed()
    if mouse_buttons[0]:
        (x, y) = pygame.mouse.get_pos()
        camera.light[0] = x
        camera.light[1] = y

    if keys[pygame.K_w]:
        camera.translate_z(5)
    if keys[pygame.K_s]:
        camera.translate_z(-5)
    if keys[pygame.K_a]:
        camera.translate_x(-5)
    if keys[pygame.K_d]:
        camera.translate_x(5)
    if keys[pygame.K_SPACE]:
        camera.translate_y(-5)
    if keys[pygame.K_LSHIFT]:
        camera.translate_y(5)
    if keys[pygame.K_ESCAPE]:
        return False
    return True

def main():
    Tk().withdraw()
    filename = askopenfilename()
    if filename == '':
        print('File not selected')
        return
    
    camera = Camera(WIDTH, HEIGHT, filename)
    screen = pygame.display.set_mode((WIDTH, HEIGHT))

    clock = pygame.time.Clock()
    
    running = True
    while running:
        running = control_handler(camera)

        image = camera.draw()
        pygame.surfarray.blit_array(screen, image)
        pygame.display.flip()
        fps = str(int(clock.get_fps()))
        pygame.display.set_caption(f"FPS: {fps}")
        clock.tick(60)

    pygame.quit()

if __name__ == "__main__":
    main()
