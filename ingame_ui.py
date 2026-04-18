import pygame
import sys



class Panel:
    def __init__(self, x, y, w, h, color=(40,40,40)):
        self.rect = pygame.Rect(x, y, w, h)
        self.color = color

    def draw(self, surface):
        pygame.draw.rect(surface, self.color, self.rect)
        pygame.draw.rect(surface, (25,25,25), self.rect, 1)

class Sidebar:
    def __init__(self, x, y, w, h):
        self.rect = pygame.Rect(x, y, w, h)
        self.items = []

    def word(self, name):
        self.items.append(name)


    def draw(self, surface, font):
        mouse = pygame.mouse.get_pos()

        pygame.draw.rect(surface,(50,50,50), self.rect)
        
        
        for i, item in enumerate(self.items):
                text_rect = font.render(item, False, (128, 128, 128)).get_rect(topleft=(self.rect.x + 20, self.rect.y + 60 + (i * 40)))
                color = (255, 255, 255) if text_rect.collidepoint(mouse) else (128, 128, 128)
                text = font.render(item, False, color)
               
                surface.blit(text, (self.rect.x + 20, self.rect.y + 60 + (i * 40)))



class page:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((1280, 720))
        
        self.title_font = pygame.font.SysFont('Verdana', 16,bold= True)
        self.font = pygame.font.SysFont('Verdana', 14)
        
        self.sidebar = Sidebar(0, 0, 250, 720)
        self.sidebar.word('URGENT')
        self.sidebar.word('LOGISTICS')
        self.sidebar.word('COMBAT')
        self.sidebar.word('INTEL')
        self.topbar = Panel(0, 0, 1280, 50, (35,35,35))
        self.rightbar = Panel(1030, 50, 250, 620, (0,0,0))
        self.bottombar = Panel(0, 670, 1280, 50, (35,35,35))

    def run(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

            self.screen.fill((10,10,10))
            
            self.topbar.draw(self.screen)
            self.sidebar.draw(self.screen, self.font)
            self.rightbar.draw(self.screen)
            self.bottombar.draw(self.screen)
            title = self.title_font.render('OPERATIONAL COMMAND', True, (200, 170, 80))
            self.screen.blit(title, (20, 15))
            
            
            pygame.display.flip()
          
    pygame.quit() 
if __name__ == '__main__':
    page().run()

   