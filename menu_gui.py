import pygame
import sys

pygame.init()

WIDTH,HEIGHT = 1280,720

screen = pygame.display.set_mode((WIDTH, HEIGHT))

pygame.display.set_caption('game menu') 

dark_blue = (15,25,45)

text= (255, 244, 200)




main_font = pygame.font.Font('./fonts/Inter_18pt-Medium.ttf', 18)
big_font = pygame.font.Font('./fonts/Inter_18pt-Medium.ttf', 18)

menu = 'main' 
run = True


button_width = 330
button_height = 55
button_m=(WIDTH // 2) - (button_width // 2)

bg_image = pygame.image.load('Game Menu UI Design (1).png').convert()
bg_image = pygame.transform.smoothscale(bg_image,(WIDTH, HEIGHT))

def glow(screen,x,y,w,h):
    for i in range(1,6):
        lighting = pygame.Surface((w + i*10, h + i*10), pygame.SRCALPHA)
        glow_color =(255,190,0,15)
        pygame.draw.rect(lighting, glow_color, (0, 0, w + i*10, h + i*10))
        
        screen.blit(lighting, (x - i*5, y - i*5))


def button(screen,x,y,w,h):
    button_surf = pygame.Surface((w, h),pygame.SRCALPHA)
    button_color = (10,10,60,200)  
    pygame.draw.rect(button_surf, button_color, (0,0,w,h))
    pygame.draw.rect(button_surf,(255, 120, 0, 255),(0,0,w,h),width=2)
    screen.blit(button_surf, (x, y))

while run:
    mouse = pygame.mouse.get_pos()
    screen.blit(bg_image, (0, 0))
    
    for event in pygame.event.get():
         
        if event.type == pygame.QUIT:
            run = False


        if event.type == pygame.MOUSEBUTTONDOWN:

            if menu== 'main':
            
                
                if button_m < mouse[0] < button_m + button_width and 170 < mouse[1] < 230:
                        print('starting the game....')
               
                elif button_m < mouse[0] < button_m+button_width and 345 < mouse[1] < 390:
                        menu = 'settings'
                
                elif button_m < mouse[0] < button_m + button_width and 430 < mouse[1] < 490:
                            run = False

                elif button_m < mouse[0] < button_m + button_width and 255 < mouse[1] < 345:
                        print('loading game....')
            
            elif menu == 'settings':

                
                
       
                if button_m < mouse[0] < button_m + button_width and 430 < mouse[1] < 490:
                    menu = 'main'
                    
    if menu == 'main':
        
        hover = button_m < mouse[0] < button_m + button_width and 170 < mouse[1] < 230
        if hover:
            glow(screen, button_m, 170, button_width, button_height)
        button(screen, button_m, 170, button_width, button_height)

        txt1 = main_font.render('NEW GAME',True,text)
        txt1_rect = txt1.get_rect(center=(button_m + button_width // 2, 170 + button_height // 2))
        screen.blit(txt1, txt1_rect)

        hover = button_m < mouse[0] < button_m + button_width and 345 < mouse[1] < 390
        if hover:
            glow(screen, button_m, 345, button_width, button_height)
        button(screen, button_m, 345, button_width, button_height)

        txt2 = main_font.render('SETTINGS',True,text)
        txt2_rect = txt2.get_rect(center=(button_m + button_width // 2, 345 + button_height // 2))
        screen.blit(txt2, txt2_rect)

        
        hover = button_m < mouse[0] < button_m + button_width and 430 < mouse[1] < 490
        if hover:
            glow(screen, button_m, 430, button_width, button_height)
        button(screen, button_m, 430, button_width, button_height)

        txt3 = main_font.render('QUIT', True, text)
        txt3_rect = txt3.get_rect(center=(button_m + button_width // 2, 430 + button_height // 2))
        screen.blit(txt3, txt3_rect)

        hover = button_m < mouse[0] < button_m + button_width and 255 < mouse[1] < 345
        if hover:
            glow(screen, button_m, 255, button_width, button_height)
        button(screen, button_m, 255, button_width, button_height)

        txt5 = main_font.render('LOAD GAME', True, text)
        txt5_rect = txt5.get_rect(center=(button_m + button_width // 2, 255 + button_height // 2))
        screen.blit(txt5, txt5_rect)


    elif menu == 'settings':
        t2 = big_font.render('SETTINGS',True,text)
        title_x2 = (WIDTH // 2) - (t2.get_width() // 2)
        screen.blit(t2, (title_x2,50))

        hover = button_m < mouse[0] < button_m + button_width and 430 < mouse[1] < 490
        if hover:
            glow(screen,button_m,430,button_width,button_height)
        button(screen,button_m,430,button_width,button_height)

        txt4 = main_font.render('BACK',True,text)
        txt4_rect = txt4.get_rect(center=(button_m + button_width // 2, 430 + button_height // 2))
        screen.blit(txt4,txt4_rect)



    pygame.display.flip()


    
    
pygame.quit()           
sys.exit()