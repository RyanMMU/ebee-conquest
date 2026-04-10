import pygame
import sys

pygame.init()

WIDTH,HEIGHT = 1280,720

screen = pygame.display.set_mode((WIDTH, HEIGHT))

pygame.display.set_caption('game menu') 

dark_blue = (15,25,45)

text= (255, 215, 0)




main_font = pygame.font.Font('./fonts/Inter_18pt-Medium.ttf', 25)
big_font = pygame.font.Font('./fonts/Inter_18pt-Medium.ttf', 25)

menu = 'main' 
run = True

percentchange = 0.8
button_width = int(400 * percentchange)
button_height = int(80 * percentchange)
button_m=(WIDTH // 2) - (button_width // 2)

bg_image = pygame.image.load('Group 1.png').convert()
bg_image = pygame.transform.scale(bg_image,(WIDTH, HEIGHT))

def glow(screen,x,y,w,h):
    for i in range(1,6):
        glow_surf = pygame.Surface((w + i*10, h + i*10), pygame.SRCALPHA)
        glow_color =(255,190,0,15)
        pygame.draw.rect(glow_surf, glow_color, (0, 0, w + i*10, h + i*10), border_radius=12)
        
        screen.blit(glow_surf, (x - i*5, y - i*5))


def button(screen,x,y,w,h):
    button_surf = pygame.Surface((w, h),pygame.SRCALPHA)
    button_color = (0,0,200,110)  
    pygame.draw.rect(button_surf, button_color, (0,0,w,h),border_radius=12)
    pygame.draw.rect(button_surf, (255,200,120,180),(0,0,w,h),width=2,border_radius=12)

    screen.blit(button_surf, (x, y))

while run:
    mouse = pygame.mouse.get_pos()
    screen.blit(bg_image, (0, 0))
    
    for event in pygame.event.get():
         
        if event.type == pygame.QUIT:
            run = False


        if event.type == pygame.MOUSEBUTTONDOWN:

            if menu== 'main':
            
                
                if button_m < mouse[0] < button_m + button_width and 150 < mouse[1] < 210:
                        print('starting the game....')
               
                elif button_m < mouse[0] < button_m+button_width and 250 < mouse[1] < 310:
                        menu = 'settings'
                
                elif button_m < mouse[0] < button_m + button_width and 350 < mouse[1] < 410:
                            run = False
            
            elif menu == 'settings':

                
                
       
                if button_m < mouse[0] < button_m + button_width and 450 < mouse[1] < 510:
                    menu = 'main'
                    
    if menu == 'main':
        
        hover = button_m < mouse[0] < button_m + button_width and 150 < mouse[1] < 210
        if hover:
            glow(screen, button_m, 150, button_width, button_height)
        button(screen, button_m, 150, button_width, button_height)

        txt1 = main_font.render('NEW GAME',True,text)
        txt1_rect = txt1.get_rect(center=(button_m + button_width // 2, 150 + button_height // 2))
        screen.blit(txt1, txt1_rect)

        hover = button_m < mouse[0] < button_m + button_width and 250 < mouse[1] < 310
        if hover:
            glow(screen, button_m, 250, button_width, button_height)
        button(screen, button_m, 250, button_width, button_height)

        txt2 = main_font.render('SETTINGS',True,text)
        txt2_rect = txt2.get_rect(center=(button_m + button_width // 2, 250 + button_height // 2))
        screen.blit(txt2, txt2_rect)

        
        hover = button_m < mouse[0] < button_m + button_width and 350 < mouse[1] < 410
        if hover:
            glow(screen, button_m, 350, button_width, button_height)
        button(screen, button_m, 350, button_width, button_height)

        txt3 = main_font.render('QUIT', True, text)
        txt3_rect = txt3.get_rect(center=(button_m + button_width // 2, 350 + button_height // 2))
        screen.blit(txt3, txt3_rect)

    elif menu == 'settings':
        t2 = big_font.render('SETTINGS',True,text)
        title_x2 = (WIDTH // 2) - (t2.get_width() // 2)
        screen.blit(t2, (title_x2,50))

        hover = button_m < mouse[0] < button_m + button_width and 450 < mouse[1] < 510
        if hover:
            glow(screen,button_m,450,button_width,button_height)
        button(screen,button_m,450,button_width,button_height)

        txt4 = main_font.render('BACK',True,text)
        txt4_rect = txt4.get_rect(center=(button_m + button_width // 2, 450 + button_height // 2))
        screen.blit(txt4,txt4_rect)



    pygame.display.flip()


    
    
pygame.quit()           
sys.exit()