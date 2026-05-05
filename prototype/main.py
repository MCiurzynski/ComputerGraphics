from src.camera import VirtualCamera
import numpy as np
import pygame


def main():
    camera = VirtualCamera()
    camera.load_objects("../assets/rubik3x3x3.obj")

    (width, height) = (800, 800)
    screen = pygame.display.set_mode((width, height))

    clock = pygame.time.Clock()

    pygame.mouse.get_rel()

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 4:
                    camera.change_focal_length(10)
                if event.button == 5:
                    camera.change_focal_length(-10)
        keys = pygame.key.get_pressed()

        if keys[pygame.K_w]:
            camera.translateZ(5)
        if keys[pygame.K_s]:
            camera.translateZ(-5)
        if keys[pygame.K_a]:
            camera.translateX(-5)
        if keys[pygame.K_d]:
            camera.translateX(5)
        if keys[pygame.K_SPACE]:
            camera.translateY(-5)
        if keys[pygame.K_LSHIFT]:
            camera.translateY(5)
        if keys[pygame.K_e]:
            camera.rotateZ(-np.pi / 90)
        if keys[pygame.K_q]:
            camera.rotateZ(np.pi / 90)
        if keys[pygame.K_UP]:
            camera.rotateX(np.pi / 90)
        if keys[pygame.K_DOWN]:
            camera.rotateX(-np.pi / 90)
        if keys[pygame.K_RIGHT]:
            camera.rotateY(-np.pi / 90)
        if keys[pygame.K_LEFT]:
            camera.rotateY(np.pi / 90)

        casted = camera.cast()

        screen.fill((200, 200, 200))

        for polygon in casted:
            color = polygon.color
            points_2d = [(p.coords[0], p.coords[1]) for p in polygon.points]

            if len(points_2d) >= 3:
                pygame.draw.polygon(screen, color, points_2d, 0)
                pygame.draw.polygon(screen, (0, 0, 0), points_2d, 4)

        pygame.display.flip()

        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()
