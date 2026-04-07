from src.camera import VirtualCamera
import numpy as np
import pygame

def main():    
    camera = VirtualCamera()
    camera.load_objects('../assets/rubik2x2x2.txt')
    
    (width, height) = (800, 800)
    screen = pygame.display.set_mode((width, height))
    
    clock = pygame.time.Clock()
    
    pygame.mouse.get_rel()
    
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                
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
            camera.rotateZ(np.pi / 90)
        if keys[pygame.K_q]:
            camera.rotateZ(-np.pi / 90)

        mouse_dx, mouse_dy = pygame.mouse.get_rel()
        
        if pygame.mouse.get_pressed()[0]:
            sensitivity = 0.005
            camera.rotateY(mouse_dx * sensitivity)
            camera.rotateX(mouse_dy * sensitivity)

        casted = camera.cast()
        
        screen.fill((200, 200, 200)) 

        for line in casted:
            pygame.draw.line(screen, (0, 0, 0), line.start.coords[:2], line.end.coords[:2], 1)

        pygame.display.flip()
        
        clock.tick(60)

    pygame.quit()

if __name__ == "__main__":
    main()