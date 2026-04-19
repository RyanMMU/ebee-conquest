import pygame
import sys



class panel:
    def __init__(self, x, y, w, h, color=(40,40,40)):
        self.rect = pygame.Rect(x, y, w, h)
        self.color = color

    def draw(self, surface):
        pygame.draw.rect(surface, self.color, self.rect)
        pygame.draw.rect(surface, (25,25,25), self.rect, 1)

class sidebar:


    def __init__(self, x, y, w, h):
            self.rect = pygame.Rect(x, y, w, h)
            self.items = []


    def word(self, name):
        self.items.append(name)

    def draw(self, surface, font):
        mouse = pygame.mouse.get_pos()

    

        pygame.draw.rect(surface, (50, 50, 50), self.rect)
        
        for i, item in enumerate(self.items):
          
            x = self.rect.x + 10
            y = self.rect.y + 60 + (i * 50)
            w = self.rect.width - 20
            h = 40

            rect = pygame.Rect(x, y, w, h)

            if rect.collidepoint(mouse):
                color = (0, 200, 0)
            else:
                color = (30, 30, 30)

            pygame.draw.rect(surface, color, rect)

            text = font.render(item, True, (255, 255, 255))
            surface.blit(text, (x + 10, y + 10))

class page:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((1280, 720))
        
        self.title_font = pygame.font.SysFont('Verdana', 16,bold= True)
        self.font = pygame.font.SysFont('Verdana', 14)
        
        self.sidebar = sidebar(0, 0, 250, 720)
        self.sidebar.word('URGENT')
        self.sidebar.word('LOGISTICS')
        self.sidebar.word('COMBAT')
        self.sidebar.word('INTEL')
        self.topbar = panel(0, 0, 1280, 50, (35,35,35))
        self.rightbar = panel(1030, 50, 250, 620, (0,0,0))
        self.bottombar = panel(0, 670, 1280, 50, (35,35,35))

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
          
   
if __name__ == '__main__':
    page().run()

   