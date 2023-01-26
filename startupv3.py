#region Notes
#Ian Huff
#startupv3.py
#Changes from v2:
#  Moved game 3 (defend) -> game 4
#  game 3 is now CS-Code
#  finished implementing playSound()
#  removed instances of keypad.registerKeyPressHandler(dummy_keypad_nop) in cleanup sections
#NEEDS TESTING - are keypad press handlers ever deregistered??? (unless it is done manually)
#endregion Notes

#region Imports
import time
import board
import busio
import os
import digitalio
from threading import Thread
import sys
from multiprocessing import Process
import random

import neopixel
import adafruit_character_lcd.character_lcd_i2c as character_lcd
import RPi.GPIO as GPIO
from pad4pi import rpi_gpio
#endregion Imports

#region Variables
#region Variables - Hardware
numLeds = 5    #number of leds on the strip
lcd_cols = 16  #number of chars per row on LCD
lcd_rows = 2   #number of rows on LCD
buttonRed = 23 #red button gpio pin
buttonBlu = 24 #blu button gpio pin
#endregion Variables - Hardware
#region Variables - Menu
menu_modeSelected = 0 #current game mode selected
menu_numModes = 4
menu_modes = ( #make sure these are 16 chars long
    "1: KotH         ",
    "2: CS-Mini      ",
    "3: CS-Code      ",
    "4: Defend       "
    )
    #endregion Variables - Menu
#region Variables - Game 1
game1_timerSelected = 0 #current timer duration selected
game1_numTimers = 3     #number of available timer durations
game1_timerVals = (1, 30, 60, 120, 180)
game1_timers = (        #available timer durations
    "1: Instant (1s) ", #a team must control the point for
    "2: 30 seconds   ", #this long to win
    "3: 1 minute     ",
    "4: 2 minutes    ",
    "5: 3 minutes    "
    )
game1_currentTeam = 0      #the team currently holding the point 0=neutral, 1=red, 2=blu
game1_timeRemainingRed = 0 #red team's remeining time until victory
game1_timeRemainingBlu = 0 #blu team's remaining time until victory
game1_gameDone = False     #set to true when a team's timer hits 0
#endregion Variables - Game 1
#region Variables - Game 2
game2_timerSelected = 0 #current timer duration selected
game2_numTimers = 5     #number of available timer durations
game2_timerVals = (60, 120, 180, 240, 300)
game2_timers = (        #available game timer durations
    "1: 1 minute     ", #the game will end after this long,
    "2: 2 minutes    ", #regardless of anything else
    "3: 3 minutes    ",
    "4: 4 minutes    ",
    "5: 5 minutes    "
    )
game2_fuseSelected = 0  #current fuse duration selected
game2_numFuses = 7      #number of available fuse durations
game2_fuseVals = (1, 30, 40, 45, 60, 90, 120)
game2_fuses = (         #available fuse durations
    "1: Instant (1s) ", #the bomb will detonate after this long
    "2: 30 seconds   ", #after it is armed
    "3: 40 seconds   ",
    "4: 45 seconds   ",
    "5: 1 minute     ",
    "6: 1.5 minutes  ",
    "7: 2 minutes    "
    )
game2_timeRemaining = 0 #time remaining in the round
game2_defuseRemaining = 0 #time remining in current defuse attempt
game2_bombPlanted = False
game2_bombDefused = False
game2_endManual = 0 #0=detonated or defused, 1=T win by elim, 2=CT win by elim
game2_gameDone = False
#endregion Variables - Game 2
#region Variables - Game 3
game3_timerSelected = 0 #current timer duration selected
game3_numTimers = 5     #number of available timer durations
game3_timerVals = (60, 120, 180, 240, 300)
game3_timers = (        #available game timer durations
    "1: 1 minute     ", #the game will end after this long,
    "2: 2 minutes    ", #regardless of anything else
    "3: 3 minutes    ",
    "4: 4 minutes    ",
    "5: 5 minutes    "
    )
game3_fuseSelected = 0  #current fuse duration selected
game3_numFuses = 7      #number of available fuse durations
game3_fuseVals = (1, 30, 40, 45, 60, 90, 120)
game3_fuses = (         #available fuse durations
    "1: Instant (1s) ", #the bomb will detonate after this long
    "2: 30 seconds   ", #after it is armed
    "3: 40 seconds   ",
    "4: 45 seconds   ",
    "5: 1 minute     ",
    "6: 1.5 minutes  ",
    "7: 2 minutes    "
    )
game3_digitsSelected = 0 #current no. of digits selected
game3_nextDigit = 0 #next digit in the code sequence
game3_digitsEntered = 0 #number of digits entered thus far
game3_timeRemaining = 0 #time remaining in the round
game3_defuseRemaining = 0 #time remining in current defuse attempt
game3_bombPlanted = False
game3_bombDefused = False
game3_endManual = 0 #0=detonated or defused, 1=T win by elim, 2=CT win by elim
game3_gameDone = False
#endregion Variables - Game 3
#region Variables - Game 4
game4_timerSelected = 0 #current timer duration selected
game4_numTimers = 8     #number of available timer durations
game4_timerVals = (60, 120, 180, 240, 300, 480, 600, 900)
game4_timers = (        #available game timer durations
    "1: 1 minute     ", #the game will end after this long
    "2: 2 minutes    ",
    "3: 3 minutes    ",
    "4: 4 minutes    ",
    "5: 5 minutes    ",
    "6: 8 minutes    ",
    "7: 10 minutes   ",
    "8: 15 minutes   "
    )
game4_timeRemaining = 0
game4_gameDone = False
#endregion Variables - Game 4
#endregion Variables

#region Hardware Setup
#GPIO cleanup - in case system was not shut down correctly
GPIO.cleanup()
#LEDs
leds = neopixel.NeoPixel(board.D12, numLeds)
#LCD
i2c = board.I2C()
lcd = character_lcd.Character_LCD_I2C(i2c, lcd_cols, lcd_rows)
lcd.backlight = True
#buttons
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(buttonRed, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(buttonBlu, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
#keypad
KEYPAD = [[1, 2, 3], [4, 5, 6], [7, 8, 9], ["*", 0, "#"]]
COL_PINS = [5, 13, 27]
ROW_PINS = [6, 4, 17, 22]
factory = rpi_gpio.KeypadFactory()
keypad = factory.create_keypad(keypad=KEYPAD, row_pins=ROW_PINS, col_pins=COL_PINS)
#endregion Hardware Setup

#region Functions
#region Functions - Dummy
def dummy_button_nop(channel):
    print("Button " + str(channel) + " was pressed!")
def dummy_keypad_nop(key):
    print("Key " + str(key) + " was pressed!")
#endregion Functions - Dummy
#region Functions - Menu
def menu_keypad_modeSel(key):
    global menu_modeSelected
    if(key != '*' and key != '#'):
        menu_modeSelected = key
    else:
        menu_modeSelected = 0
#endregion Functions - Menu
#region Functions - Game 1
#region Functions - Game 1 - Setup
def game1_keypad_timerSel(key):
    global game1_timerSelected

    if(key != '*' and key != '#'):
        game1_timerSelected = key
    else:
        game1_timerSelected = 0
#endregion Functions - Game 1 - Setup
#region Functions - Game 1 - Buttons
def game1_button_capture(channel):
    global buttonRed
    global game1_currentTeam

    if(game1_gameDone == True):
        return

    if(channel == buttonRed and game1_currentTeam != 1):
        game1_currentTeam = 1
        allLeds(200, 0, 0) #red
        playSound("game1_capture")
    if(channel == buttonBlu and game1_currentTeam != 2):
        game1_currentTeam = 2
        allLeds(0, 0, 200) #blue
        playSound("game1_capture")
#endregion Functions - Game 1 - Buttons
#region Functions - Game 1 - Timers
def game1_printTimers():
    global game1_timeRemainingRed
    global game1_timeRemainingBlu
    global game1_currentTeam
    
    printString = " RED   "
    if(game1_currentTeam == 0):
        printString += "--"
    elif(game1_currentTeam == 1):
        printString += "<<"
    else:
        printString += ">>"
    printString += "   BLU \n " + str(game1_timeRemainingRed) + "        "
    if(game1_timeRemainingRed < 100):
        printString += " "
    if(game1_timeRemainingRed < 10):
        printString += " "
    printString += str(game1_timeRemainingBlu) + " "
    if(game1_timeRemainingBlu < 100):
        printString += " "
    if(game1_timeRemainingBlu < 10):
        printString += " "
    
    lcd.message = printString
#endregion Functions - Game 1 - Timers
#endregion Functions - Game 1
#region Functions - Game 2
#region Functions - Game 2 - Setup
def game2_keypad_timerSel(key):
    global game2_timerSelected

    if(key != '*' and key != '#'):
        game2_timerSelected = key
    else:
        game2_timerSelected = 0

def game2_keypad_fuseSel(key):
    global game2_fuseSelected

    if(key != '*' and key != '#'):
        game2_fuseSelected = key
    else:
        game2_fuseSelected = 0

#endregion Functions - Game 2 - Setup
#region Functions - Game 2 - Timers
def game2_printTimer():
    global game2_timeRemaining
    
    if(game2_bombPlanted == False):
        printString = "Time: "
    else:
        printString = "Fuse: "
        playSound("game2_beep")
    printString += str(game2_timeRemaining)
    printString += "       "
    if(game2_timeRemaining < 100):
        printString += " "
    if(game2_timeRemaining < 10):
        printString += " "
    printString += "\n*:T Win #:CT Win"
    lcd.message = printString
#endregion Functions - Game 2 - Timers
#region Functions - Game 2 - Input
def game2_button_plant(channel):
    global game2_bombPlanted
    global game2_timeRemaining
    global game2_fuseVals
    global game2_fuseSelected

    if(game2_bombPlanted == False):
        game2_bombPlanted = True
        game2_timeRemaining = game2_fuseVals[game2_fuseSelected - 1]
        allLeds(200, 0, 0) #red
        playSound("game2_bombplanted")


def game2_button_defuse(channel):
    global game2_bombDefused
    global game2_bombPlanted

    if(game2_bombPlanted == True and game2_bombDefused == False):
        game2_bombDefused = True
        allLeds(0, 0, 200) #blue
        playSound("game2_bombdefused")

def game2_keypad_victory(key):
    global game2_gameDone
    global game2_endManual

    if(key == '*'):
        game2_endManual = 1
        game2_gameDone = True
    elif(key == '#'):
        game2_endManual = 2
        game2_gameDone = True

#endregion Functions - Game 2 - Input
#endregion Functions - Game 2
#region Functions - Game 3
#region Functions - Game 3 - Setup
def game3_keypad_timerSel(key):
    global game3_timerSelected

    if(key != '*' and key != '#'):
        game3_timerSelected = key
    else:
        game3_timerSelected = 0

def game3_keypad_fuseSel(key):
    global game3_fuseSelected

    if(key != '*' and key != '#'):
        game3_fuseSelected = key
    else:
        game3_fuseSelected = 0

def game3_keypad_digitSel(key):
    global game3_digitsSelected

    if(key != '*' and key != '#'):
        game3_digitsSelected = key
    else:
        game3_fuseSelected = 0
#endregion Functions - Game 3 - Setup
#region Functions - Game 3 - Timers
def game3_printTimer():
    global game3_timeRemaining
    
    if(game3_bombPlanted == False):
        printString = "Time: "
    else:
        printString = "Fuse: "
        playSound("game2_beep")

    printString += str(game3_timeRemaining)
    if(game3_timeRemaining < 100):
        printString += " "
    if(game3_timeRemaining < 10):
        printString += " "

    if(game3_bombPlanted == True):
        printString += " Next:" + str(game3_nextDigit)
    else:
        printString += "       "

    printString += "\n*:T Win #:CT Win"
    lcd.message = printString
#endregion Functions - Game 3 - Timers
#region Functions - Game 3 - Input
def game3_button_plant(channel):
    global game3_bombPlanted
    global game3_timeRemaining
    global game3_fuseVals
    global game3_fuseSelected

    if(game3_bombPlanted == False):
        game3_bombPlanted = True
        game3_timeRemaining = game3_fuseVals[game3_fuseSelected - 1]
        allLeds(200, 0, 0) #red
        playSound("game2_bombplanted")

def game3_keypad_victory(key):
    global game3_gameDone
    global game3_endManual
    global game3_nextDigit
    global game3_digitsEntered
    global game3_digitsSelected
    global game3_bombDefused

    if(key == '*'):
        game3_endManual = 1
        game3_gameDone = True
    elif(key == '#'):
        game3_endManual = 2
        game3_gameDone = True
    elif(key == game3_nextDigit):
        playSound("game1_capture")
        game3_nextDigit = random.randint(0, 9)
        leds[game3_digitsEntered] = (0, 200, 0)
        game3_digitsEntered += 1
        if(game3_digitsEntered == game3_digitsSelected):
            game3_bombDefused = True
            game3_gameDone = True

#endregion Functions - Game 3 - Input
#endregion Functions - Game 3
#region Functions - Game 4
#region Functions - Game 4 - Setup
def game4_keypad_timerSel(key):
    global game4_timerSelected

    if(key != '*' and key != '#'):
        game4_timerSelected = key
    else:
        game4_timerSelected = 0
#endregion Functions - Game 4 - Setup
#region Functions - Game 4 - Button
def game4_button_pressed(channel):
    global game4_gameDone

    game4_gameDone = True
#endregion Functions - Game 4 - Button
#region Functions - Game 4 - Timer
def game4_printTimer():
    global game4_timeRemaining

    printString = "Time Remaining: \n" + str(game4_timeRemaining)+ "             "
    if(game4_timeRemaining < 100):
        printString += " "
    if(game4_timeRemaining < 10):
        printString += " "
    lcd.message = printString
#endregion Functions - Game 4 - Timer
#endregion Functions - Game 4
#region Functions - Other
def countdown():
    lcd.clear()
    lcd.message = "Game Begins in\n10 Seconds!"
    time.sleep(6)
    playSound("universal_countdowntick")
    time.sleep(1)
    playSound("universal_countdowntick")
    time.sleep(1)
    playSound("universal_countdowntick")
    time.sleep(1)
    playSound("universal_countdowngo")

def allLeds(r, g, b):
    for i in range(0, numLeds):
        leds[i] = (r, g, b)

def playSound(filename):
    command = "aplay /boot/" + filename + ".wav"
    os.system(command)
#endregion Functions - Other
#endregion Functions

#region Main
#region Main - Startup
lcd.clear()
lcd.message = "Game System\nStarting Up..."
time.sleep(1)
#endregion Main - Startup

while(True):
    #region Main - Menu
    GPIO.remove_event_detect(buttonRed)
    GPIO.remove_event_detect(buttonBlu)
    keypad.registerKeyPressHandler(menu_keypad_modeSel)
    menu_modeSelected = 0
    i = 0
    while(menu_modeSelected == 0 or menu_modeSelected > menu_numModes):
        lcd.message = "Choose game mode\n" + menu_modes[i]
        i = i + 1
        if(i == menu_numModes):
            i = 0
    playSound("menu_select")

    #display selection
    lcd.clear()
    lcd.message = "Selected:\n" + menu_modes[menu_modeSelected - 1]
    time.sleep(1)
    lcd.clear()
    #endregion Main - Menu
    #region Main - Game 1
    if(menu_modeSelected == 1):
        #region Main - Game 1 - Setup
        #select timer duration
        keypad.registerKeyPressHandler(game1_keypad_timerSel)
        game1_timerSelected = 0
        i = 0
        while(game1_timerSelected == 0 or game1_timerSelected > game1_numTimers):
            lcd.message = "Choose timer dur\n" + game1_timers[i]
            i += 1
            if(i == game1_numTimers):
                i = 0
        playSound("menu_select")
        
        #endregion Main - Game 1 - Setup
        #region Main - Game 1 - Operation
        #set events for the buttons
        GPIO.add_event_detect(buttonRed, GPIO.RISING, callback=game1_button_capture)
        GPIO.add_event_detect(buttonBlu, GPIO.RISING, callback=game1_button_capture)
        
        #set initial variable values
        game1_gameDone = False
        game1_currentTeam = 0
        game1_timeRemainingRed = game1_timerVals[game1_timerSelected - 1]
        game1_timeRemainingBlu = game1_timerVals[game1_timerSelected - 1]
        
        #game start
        countdown()
        allLeds(0, 200, 0) #green

        #main loop - wait for game to end
        while(game1_gameDone == False):
            if(game1_currentTeam == 1):
                game1_timeRemainingRed -= 1
            elif(game1_currentTeam == 2):
                game1_timeRemainingBlu -= 1
            game1_printTimers()
            time.sleep(1)
            if(game1_timeRemainingRed == 0 or game1_timeRemainingBlu == 0):
                game1_gameDone = True

        #announce winner
        lcd.clear()
        playSound("universal_timeup")
        if(game1_timeRemainingRed == 0):
            lcd.message = " Red Team Wins! "
        else:
            lcd.message = " Blu Team Wins! "

        time.sleep(3)
        allLeds(0, 0, 0)
        
        #cleanup
        GPIO.remove_event_detect(buttonRed)
        GPIO.remove_event_detect(buttonBlu)
        #endregion - Main - Game 1 - Operation
    #endregion Main - Game 1
    #region Main - Game 2
    elif(menu_modeSelected == 2):
        #region Main - Game 2 - Setup
        #select game timer duration
        keypad.registerKeyPressHandler(game2_keypad_timerSel)
        game2_timerSelected = 0
        i = 0
        while(game2_timerSelected == 0 or game2_timerSelected > game2_numTimers):
            lcd.message = "Choose timer dur\n" + game2_timers[i]
            i += 1
            if(i == game2_numTimers):
                i = 0
        playSound("menu_select")

        #select fuse timer
        keypad.registerKeyPressHandler(game2_keypad_fuseSel)
        game2_fuseSelected = 0
        i = 0
        while(game2_fuseSelected == 0 or game2_fuseSelected > game2_numFuses):
            lcd.message = "Choose fuse dur \n" + game2_fuses[i]
            i += 1
            if(i == game2_numFuses):
                i = 0
        playSound("menu_select")
        #endregion Main - Game 2 - Setup
        #region Main - Game 2 - Operation
        #red button - plant bomb        blue button - defuse bomb
        GPIO.add_event_detect(buttonRed, GPIO.RISING, callback=game2_button_plant)
        GPIO.add_event_detect(buttonBlu, GPIO.BOTH,   callback=game2_button_defuse)

        #keypad - press # for T victory, * for CT
        keypad.registerKeyPressHandler(game2_keypad_victory)

        #set initial variable values
        game2_bombPlanted = False
        game2_defusing    = False
        game2_bombDefused = False
        game2_endManual   = 0
        game2_gameDone    = False
        game2_timeRemaining = game2_timerVals[game2_timerSelected - 1]
        game2_fuseRemaining = game2_fuseVals[game2_fuseSelected - 1]

        #game start
        countdown()

        #wait for game to end
        while(game2_gameDone == False):
            game2_timeRemaining -= 1
            game2_printTimer()
            time.sleep(1)
            if(game2_timeRemaining == 0 or game2_bombDefused == True):
                game2_gameDone = True

        #announce winner
        lcd.clear()
        if(game2_endManual == 1):
            lcd.message = "Terrorists Win! \n                "
            playSound("universal_timeup")
        elif(game2_endManual == 2):
            lcd.message = "Counter-        \nTerrorists Win! "
            playSound("universal_timeup")
        elif(game2_bombPlanted == True and game2_bombDefused == False):
            lcd.message = "Terrorists Win! \n                "
            playSound("game2_explosion")
        else:
            lcd.message = "Counter-        \nTerrorists Win! "
            playSound("universal_timeup")

        time.sleep(3)
        allLeds(0, 0, 0)

        #cleanup
        GPIO.remove_event_detect(buttonRed)
        GPIO.remove_event_detect(buttonBlu)
        #endregion Main - Game 2 - Operation
    #endregion Main - Game 2
    #region Main - Game 3
    elif(menu_modeSelected == 3):
        #region Main - Game 3 - Setup
        #select game timer duration
        keypad.registerKeyPressHandler(game3_keypad_timerSel)
        game3_timerSelected = 0
        i = 0
        while(game3_timerSelected == 0 or game3_timerSelected > game3_numTimers):
            lcd.message = "Choose timer dur\n" + game3_timers[i]
            i += 1
            if(i == game3_numTimers):
                i = 0
        playSound("menu_select")

        #select fuse timer
        keypad.registerKeyPressHandler(game3_keypad_fuseSel)
        game3_fuseSelected = 0
        i = 0
        while(game3_fuseSelected == 0 or game3_fuseSelected > game3_numFuses):
            lcd.message = "Choose fuse dur \n" + game3_fuses[i]
            i += 1
            if(i == game3_numFuses):
                i = 0
        playSound("menu_select")

        #select number of digits
        keypad.registerKeyPressHandler(game3_keypad_digitSel)
        game3_digitsSelected = 0
        while(game3_fuseSelected == 0 or game3_fuseSelected > 5):
            lcd.message = "Choose code     \nlength (max 5)  "
        playSound("menu_select")
        #endregion Main - Game 3 - Setup
        #region Main - Game 3 - Operation
        #red button - plant bomb        blue button - defuse bomb
        GPIO.add_event_detect(buttonRed, GPIO.RISING, callback=game3_button_plant)

        #keypad - press # for T victory, * for CT
        keypad.registerKeyPressHandler(game3_keypad_victory)

        #set initial variable values
        game3_bombPlanted = False
        game3_defusing    = False
        game3_bombDefused = False
        game3_endManual   = 0
        game3_gameDone    = False
        game3_digitsEntered = 0
        game3_nextDigit = random.randint(0, 9)
        game3_timeRemaining = game3_timerVals[game3_timerSelected - 1]
        game3_fuseRemaining = game3_fuseVals[game3_fuseSelected - 1]

        #game start
        countdown()

        #wait for game to end
        while(game3_gameDone == False):
            game3_timeRemaining -= 1
            game3_printTimer()
            time.sleep(1)
            if(game3_timeRemaining == 0 or game3_bombDefused == True):
                game3_gameDone = True

        #announce winner
        lcd.clear()
        if(game3_endManual == 1):
            lcd.message = "Terrorists Win! \n                "
            playSound("universal_timeup")
        elif(game3_endManual == 2):
            lcd.message = "Counter-        \nTerrorists Win! "
            playSound("universal_timeup")
        elif(game3_bombPlanted == True and game3_bombDefused == False):
            lcd.message = "Terrorists Win! \n                "
            playSound("game2_explosion")
        else:
            lcd.message = "Counter-        \nTerrorists Win! "
            playSound("universal_timeup")

        time.sleep(3)
        allLeds(0, 0, 0)

        #cleanup
        GPIO.remove_event_detect(buttonRed)
        GPIO.remove_event_detect(buttonBlu)
        #endregion Main - Game 3 - Operation
    #endregion Main - Game 3
    #region Main - Game 4
    elif(menu_modeSelected == 3):
        #region Main - Game 4 - Setup
        #select game timer duration
        keypad.registerKeyPressHandler(game4_keypad_timerSel)
        game4_timerSelected = 0
        i = 0
        while(game4_timerSelected == 0 or game4_timerSelected > game4_numTimers):
            lcd.message = "Choose timer dur\n" + game4_timers[i]
            i += 1
            if(i == game4_numTimers):
                i = 0
        playSound("menu_select")
        #endregion Main - Game 4 - Setup
        #region Main - Game 4 - Operation
        #red button - arms bomb instantly        blue button - starts defuse timer (hold)
        GPIO.add_event_detect(buttonRed, GPIO.RISING,  callback=game4_button_pressed)
        GPIO.add_event_detect(buttonBlu, GPIO.RISING,  callback=game4_button_pressed)

        #set initial variable values
        game4_gameDone = False
        game4_timeRemaining = game4_timerVals[game4_timerSelected - 1]

        #game start
        countdown()

        #wait for game to end
        while(game4_gameDone == False):
            game4_timeRemaining -= 1
            game4_printTimer()
            time.sleep(1)
            if(game4_timeRemaining == 0):
                game4_gameDone = True

        #announce winner
        lcd.clear()
        playSound("universal_timeup")
        if(game4_timeRemaining <= 0):
            lcd.message = "Time Up!"
        else:
            lcd.message = "Game!"
        time.sleep(1.5)
        lcd.clear()

        #cleanup
        GPIO.remove_event_detect(buttonRed)
        GPIO.remove_event_detect(buttonBlu)
        #endregion Main - Game 4 - Operation
    #endregion Main - Game 4
#endregion Main

#region End
lcd.clear()
lcd.message = "Goodbye"
time.sleep(1.5)
lcd.clear()
lcd.backlight = False
GPIO.cleanup()
#endregion End
