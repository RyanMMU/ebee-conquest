import pygame
import sys

pygame.init()

import ctypes
ctypes.windll.user32.SetProcessDPIAware()


pygame.display.set_caption('settings') 


class volume_bar:
    def __init__(self, x, y, w, h=8):
        self.rect = pygame.Rect(x, y, w, h)
        self.circle_radius = 10
        self.percentage = 0.5  
        self.is_dragging = False
      

    def handle_event(self, event):
        mouse_pos = pygame.mouse.get_pos()
        
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.inflate(0, 20).collidepoint(mouse_pos):
                self.is_dragging = True
        elif event.type == pygame.MOUSEBUTTONUP:
            self.is_dragging = False
            
        if self.is_dragging:
            new_x = max(self.rect.left, min(mouse_pos[0], self.rect.right))
            self.percentage = (new_x - self.rect.x) / self.rect.width

    def draw(self, surface):
        pygame.draw.rect(surface,(60, 63, 65), self.rect, border_radius=4)
        
        fill_w = int(self.rect.width * self.percentage)
        fill_rect = pygame.Rect(self.rect.x, self.rect.y, fill_w, self.rect.height)
        pygame.draw.rect(surface, (0, 255,0) , fill_rect, border_radius=4)

        knob_x = self.rect.x + fill_w
        pygame.draw.circle(surface, (255, 255, 255), (knob_x, self.rect.centery), self.circle_radius)

screen = pygame.display.set_mode((600, 400))
clock = pygame.time.Clock()

bar = volume_bar(150, 200, 300)

while True:
    screen.fill((20,22,24))

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        
        bar.handle_event(event)

    bar.draw(screen)

    font = pygame.font.SysFont('Verdana', 24)

    title = font.render('           SETTINGS', True, (255, 255, 255))

    
    screen.blit(title, (150, 50))
    volume = font.render(f'Volume: {int(bar.percentage * 100)}%', True,(255,255,255))
    screen.blit(volume, (150, 160))

    pygame.display.flip()
    clock.tick(360)