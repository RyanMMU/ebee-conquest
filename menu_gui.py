import pygame
import sys

pygame.init()

screen = pygame.display.set_mode((1000, 600))
pygame.display.set_caption('game menu') 

black = (10,10,10)      
dark_gray = (40,40,40)
green = (0,255,0)   
bright_green = (0,200,0)
white= (255,255,255)
button_color = dark_gray
hover_color = green
text_color = green
main_font = pygame.font.SysFont('consolas', 30)
big_font = pygame.font.SysFont('consolas', 50)

menu = 'main' 
run = True

while run:
    mouse = pygame.mouse.get_pos()
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            run = False
            
     
        if event.type == pygame.MOUSEBUTTONDOWN:

            
            if menu== 'main':
            
                
                
                if 400 < mouse[0] < 600 and 150 < mouse[1] < 210:
                    print('starting the game....')
               
                if 400 < mouse[0] < 600 and 250 < mouse[1] < 310:
                    menu = 'settings'
                
                if 400 < mouse[0] < 600 and 350 < mouse[1] < 410:
                    run = False
            
            elif menu == 'settings':

                
                
       
                if 400 < mouse[0] < 600 and 450 < mouse[1] < 510:
                    menu = 'main'

        screen.fill(black)
        if pygame.draw.rect(screen, bright_green, (400,450,200,60)):
    
            
            txt4 = main_font.render('BACK',True,black)
            screen.blit(txt4,(465,460))

    

    if menu == 'main':
       
        t = big_font.render('EBEE CONQUEST',True,white)
        screen.blit(t, (300,50))
        
       
        if 400 < mouse[0] < 600 and 150 < mouse[1] < 210:
            pygame.draw.rect(screen, bright_green, (400,150,200,60))
        else:
            pygame.draw.rect(screen,green, (400,150,200,60))
        txt1 = main_font.render('START', True, black)
        screen.blit(txt1, (450,160))

      
        if 400 < mouse[0] < 600 and 250 < mouse[1] < 310:
            pygame.draw.rect(screen, bright_green, (400,250,200,60))
        else:
            pygame.draw.rect(screen, green, (400,250,200,60))
        txt2 = main_font.render('SETTINGS', True, black)
        screen.blit(txt2, (415,260))

       
        if 400 < mouse[0] < 600 and 350 < mouse[1] < 410:
            pygame.draw.rect(screen, bright_green, (400, 350, 200, 60))
        else:
            pygame.draw.rect(screen, green, (400,350,200,60))
        txt3 = main_font.render('QUIT', True, black)
        screen.blit(txt3, (460,360))

    elif menu == 'settings':
        t2 = big_font.render('SETTINGS', True, black)
        screen.blit(t2,(350,50))
        
       
    pygame.draw.rect(screen, bright_green, (400,450,200,60))
    txt4 = main_font.render('BACK', True, black)
    screen.blit(txt4, (465,460))

    
    pygame.display.flip()


pygame.quit()
sys.exit()