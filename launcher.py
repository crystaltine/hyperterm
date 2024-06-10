import time
from time import sleep
from draw_utils import *
from blessed import Terminal
import os
import sys
import subprocess


term=Terminal()



def print_text(text):
    #words=f'{fcode(fcode_color)}{text}{'\033[0m'}'
    for char in text:
        sleep(0.055)
        print(char, end='', flush=True)

def draw_loading_animation(time_limit):
    animation = "|/-\\"
    start_time = time.time()
    while True:
        for i in range(4):
            time.sleep(0.2)  # Feel free to experiment with the speed here
            sys.stdout.write("\r " + animation[i % len(animation)])
            sys.stdout.flush()
        if time.time() - start_time > time_limit:  # The animation will last for 10 seconds
            sys.stdout.write(' ')
            sys.stdout.flush()
            break

def main():
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    os.system('cls')

    print_text(f'{fcode('#12A1ED')}Welcome to {fcode('#ED125F')}Terminal Suite, {fcode('#12A1ED')}a collection of popular apps recreated in the terminal!{STYLE_CODES['reset']}'+'\n \n')
    
    print_text(f'{fcode('#12A1ED')}To run {fcode('#2FEF15')}Viscord, {fcode('#12A1ED')}please type {fcode('#2FEF15')}"run viscord".{STYLE_CODES['reset']} \n \n')
    print_text(f'{fcode('#12A1ED')}To run {fcode('#F98C10')}Veometry Dash, {fcode('#12A1ED')}please type {fcode('#F98C10')}"run veometry_dash".{STYLE_CODES['reset']} \n \n')

    print_text(f'{fcode('#F15FDD')}...Awaiting command... \n \n')
    command=input(f'{fcode('#0953FC')}')
    print('\n')
    command=command.lower()

    while command!='run viscord' and command!='run veometry_dash' and command !='q' and command!='exit' and command!='quit':

        print_text(f'{fcode('#FA2C03')}You entered an invalid command. Please try again... \n \n')
        command=input(f'{fcode('#0953FC')}')
        print('\n')
        command=command.lower()

    
    if command=='run viscord':
       
        print_text(f'{fcode('#12A1ED')}Launching Viscord... \n \n {fcode('#ED125F')}')
        draw_loading_animation(4)
        print_text(f'{fcode('#12A1ED')} \n \nDone... \n \n')
        time.sleep(1)
        
        os.chdir('./viscord/client')
        os.system('python main.py')

    elif command=='run veometry_dash':
        
        print_text(f'{fcode('#12A1ED')}Launching Veometry Dash... \n \n {fcode('#ED125F')}')
        draw_loading_animation(4)
        print_text(f'{fcode('#12A1ED')} \n \nDone... \n \n')
        time.sleep(1)
                
        os.chdir('./gd')
        os.system('python main.py')
    
    elif command=='exit' or command=='q' or command=='quit':

        print_text(f'{fcode('#FA2C03')}Exiting... \n \n {STYLE_CODES['reset']}')
        time.sleep(2)
        sys.exit()


main()


