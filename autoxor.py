# -*- coding: utf-8 -*-

import sys
import os
import re
import time
from datetime import datetime, timedelta
import getopt
import cv2
import numpy as np
import math
import random
import logging
import pyautogui
import pytesseract
from urllib.parse import urlencode
import urllib.request
from glob import glob
from PIL import Image

sys.stdout.reconfigure(encoding='utf-8')
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract'
pyautogui.FAILSAFE = False

TPL_DIR = 'tpl/'
NUM_RETRY = 10
XOR_START_RETRY = 30
CONF_TEXT = 0.65
SMOOTH_MOVE = False
QUEST_NUM_PAGE = 7
QUEST_USE_FLY = True
QUEST_SPECIAL_ACT = False
ARMW_COOLDOWN_AT = (950,1000)
TGID = ('404365704:AAGrNqiPhL_VKk8fdOgQHPwkl3pNbkNFiMQ', 69778997)
# confidence guideline
# <=0.98 for anything in game with solid color background
# <=0.95 for anything in game with fixed background
# <=0.90 for anything in game with variable background

def throwErr(msg):
    logging.error(msg)
    raise Exception(msg)

def sendTelegram(msg):
    params={"chat_id":TGID[1],
             "disable_web_page_preview":1,
             "text":"\n".join(msg)}
    url="https://api.telegram.org/bot{}/sendMessage?{}".format(TGID[0],urlencode(params))
    urllib.request.urlopen(url)
    #except Exception as e:
    #    logging.error(e)

def sendLog(logfile=''):
    if not logfile:
        logfile = r"log/autoxor.YMD.log"
    logfile = logfile.replace('YMD',datetime.now().strftime('%Y%m%d'))
    wanted = []
    with open(logfile, encoding='utf-8') as f:
        for line in f:
            line = re.sub(r'^[\d\-]+ ([\d:]+),\d+', r'\1', line)
            if 'runAllDaily(' in line:
                wanted.append(line)
    sendTelegram(wanted)

def setupLogger(logfile=''):
    if not logfile:
        logfile = r"log/autoxor.YMD.log"
    logFormatter = logging.Formatter("%(asctime)s %(message)s")
    rl = logging.getLogger()
    rl.setLevel(logging.INFO)
    ch = logging.StreamHandler()
    ch.setFormatter(logFormatter)
    rl.addHandler(ch)
    
    if logfile != 'null':
        logfile = logfile.replace('YMD',datetime.now().strftime('%Y%m%d'))
        fh = logging.FileHandler(logfile, 'a', 'utf-8')
        fh.setFormatter(logFormatter)
        rl.addHandler(fh)

def waitMouseFree(cf=1):
    p1 = pyautogui.position()
    vote = 0
    told = False
    while True:
        time.sleep(0.05*cf)
        p2 = pyautogui.position()
        if p1==p2:
            vote += 1
            if vote>=cf:
                return
        else:
            if not told:
                logging.info('  Wait mouse free...')
                told = True
            p1 = p2
            vote = 0

def abMoveTo(x, y=None, t=0, err=7, sm=False, nm=False):
    waitMouseFree()
    if y is None:
        y = x[1]
        x = x[0]
    rn1 = random.randint(-err,err)
    rn2 = random.randint(-err,err)
    if nm:
        y = int((y-35.0)/1.77+35)
        x = int((x-50.0)/1.77)
    if t==0:
        x0, y0 = pyautogui.position()
        t = math.sqrt(abs(y0-y)**2+abs(x0-x)**2)/1500 + random.random()*0.3 
    if SMOOTH_MOVE or sm:
        pyautogui.moveTo(x+rn1, y+rn2, 0.1+t, pyautogui.easeInOutQuad)
    else:
        time.sleep(0.1+t/2)
        try:
            return pyautogui.moveTo(x+rn1, y+rn2)
        except Exception as e:
            #lastE = e
            logging.error(e)
            #raise lastE

def abClick(x=None, y=None, clicks=1):
    if x:
        if y:
            pyautogui.moveTo(x,y)
        else:
            pyautogui.moveTo(x)
    for i in range(clicks):
        time.sleep(random.randint(0,30)/1000)
        pyautogui.mouseDown()
        time.sleep(random.randint(50,80)/1000)
        pyautogui.mouseUp()

def abSleep(t, err=0.1):
    time.sleep(max(t-err,err) + random.random()*err*2)

def fsLocateCenterOnScreen(*args, **kargs):
    lastE = None
    for i in range(NUM_RETRY):
        try:
            return pyautogui.locateCenterOnScreen(TPL_DIR + args[0], *args[1:], **kargs)
        except Exception as e:
            lastE = e
            logging.error(e)
            time.sleep(2)
    raise lastE

def fsScreenshot(*args, **kargs):
    lastE = None
    for i in range(NUM_RETRY):
        try:
            return pyautogui.screenshot(*args, **kargs)
        except Exception as e:
            lastE = e
            logging.error(e)
            time.sleep(2)
    raise lastE

def fsLocateEither(candidates, **kargs):
    im = fsScreenshot() 
    for img in candidates:
        b = pyautogui.locate(TPL_DIR + img+'.png', im, **kargs)
        if b:
            return pyautogui.center(b)

def clickDesktop():
    p = pyautogui.position()
    pyautogui.moveTo(1916,1070)
    pyautogui.click()
    pyautogui.moveTo(p)
    time.sleep(0.1)

def clickIconCenter(img, msg, sleep=0, cf=0.97, offset=None, clicks=1, saveImg=False):
    if isinstance(img, list) or isinstance(img, tuple):
        p = fsLocateEither(img, confidence=cf)
    else:
        p = fsLocateCenterOnScreen(img+'.png', confidence=cf)
    if p:
        if offset is not None:
            p = (p[0]+offset[0], p[1]+offset[1])
        logging.info('   click {} at: {}'.format(msg, p))
        abMoveTo(p)
        abClick(clicks=clicks)
        if sleep:
            abSleep(sleep)
        return True
    else:
        return False

def clickIconInRegion(img, msg, left, top, right, btm, sleep=0, cf=0.98, clicks=1):
    im = fsScreenshot(region=(left,top,right-left,btm-top))
    if isinstance(img, list) or isinstance(img, tuple):
        for i in img:
            b = pyautogui.locate(TPL_DIR + i + '.png', im, confidence=cf)
            if b:
                break
    else:
        b = pyautogui.locate(TPL_DIR + img + '.png', im, confidence=cf)
    if b:
        p = (left+b[0]+b[2]//2, top+b[1]+b[3]//2)
        logging.info('   click {} at: {}'.format(msg, p))
        abMoveTo(p)
        abClick(clicks=clicks)
        if sleep:
            abSleep(sleep)
        return True
    else:
        return False
    
def waitScreen(icn, timeout=60, checkInterval=1, click=False, sleep=0, cf=0.98):
    # timeout is number of checking, not in seconds (or assume check interval=1)
    for i in range(0, timeout):
        if isinstance(icn, list) or isinstance(icn, tuple):
            p = fsLocateEither(icn, confidence=cf)
        else:
            p = fsLocateCenterOnScreen(icn + '.png', confidence=cf)
        if p:
            if click:
                logging.info('   click {} at {}: {}'.format(icn, i, p))
                abMoveTo(p)
                abClick()
            else:
                logging.info('   locate {} success at {}: {}'.format(icn, i, p))
            if sleep:
                abSleep(sleep)
            return True
        time.sleep(checkInterval)
    return False

def waitScreenRegion(icn, left, top, right, btm, timeout=30, checkInterval=1, click=False, sleep=0, cf=0.98):
    for i in range(0, timeout):
        im = fsScreenshot(region=(left,top,right-left,btm-top))
        b = pyautogui.locate(TPL_DIR + icn + '.png',im, confidence=cf)
        if b:
            logging.info('   locate {} success at {}: {}'.format(icn, i, b))
            if click:
                abMoveTo((left+b[0]+b[2]//2, top+b[1]+b[3]//2))
                abClick()
            if sleep:
                abSleep(sleep)
            return True
        time.sleep(checkInterval)
    return False

def waitWhiteScreen(left=300, top=300, right=400, btm=400, timeout=20):
    for i in range(0, timeout):
        im = fsScreenshot(region=(left,top,right-left,btm-top))
        gim = cv2.cvtColor(np.array(im), cv2.COLOR_RGB2GRAY)
        s = np.sum(gim)//255
        #logging.info('   pixel sum at {}: {}'.format(i,s))
        if s==(btm-top)*(right-left):
            logging.info('   white screen found at {}'.format(i))
            return True
        time.sleep(1)
    return False

def waitNonBlackScreen(left=300, top=300, right=400, btm=400, timeout=40):
    for i in range(0, timeout):
        im = fsScreenshot(region=(left,top,right-left,btm-top))
        gim = cv2.cvtColor(np.array(im), cv2.COLOR_RGB2GRAY)
        s = np.sum(gim)//255
        #logging.info('   pixel sum at {}: {}'.format(i,s))
        if s>0:
            logging.info('   non black screen found at {}'.format(i))
            return True
        time.sleep(1)
    return False

def openStk(nomax=False):
    s = pyautogui.size()
    if s != (1920,1080):
        print("Resolution not supported: {}".format(s))
        sys.exit(-1)

    ## bring to FG if not already
    #clickIconCenter('taskbar_bs', 'Taskbar BS icon', 0.2)
    ##if not clickIconCenter('taskbar_bs', 'Taskbar BS icon', 0.2):
    ##    throwErr('BS not started')
    ##    return -1
    for w in pyautogui.getWindowsWithTitle('Command Prompt'):
        w.minimize()
    for w in pyautogui.getWindowsWithTitle('C:\WINDOWS\SYSTEM32\cmd.exe'):
        w.minimize()

    if nomax:
        time.sleep(0.5)
    else:
        clickIconCenter('bs_maximize', 'Maximize BS window', 0.2, 0.95)

        if fsLocateCenterOnScreen('ic_lock.png', confidence=0.95):
            # do not click the lock, click anywhere else
            logging.info('Unlock Screen')
            abMoveTo(960,550)
            abClick()
              

def killRox():
    os.system(r"taskkill /im rox.exe")
    time.sleep(2)
    os.system(r"taskkill /f /im rox.exe")


def killStk(winTitle=''):
    # try to bring to foreground
    if winTitle:
        for w in pyautogui.getWindowsWithTitle('XOR'):
            if w.title.startswith('Close XOR'):
                w.restore()
                w.show()
            elif w.title != winTitle: 
                w.minimize()
        for w in pyautogui.getWindowsWithTitle('XOR'):
            if w.title == winTitle:
                w.restore()
                w.show()
                #w.activate()
                time.sleep(0.2)
                w.close()
                time.sleep(0.5)
                if not clickIconCenter('bs_close', 'BS close prompt', 0.2, 0.85):
                    logging.error('Cannot close BS with title {}'.format(winTitle))
                    return -1
                break

    else:
        clickIconCenter('taskbar_bs', 'Taskbar BS icon', 0.2)
    
        os.system(r"taskkill /im hd-player.exe")
        time.sleep(1)

        if not clickIconCenter('bs_close', 'BS close prompt'):
            os.system("taskkill /f /im hd-player.exe")

    logging.info('Wait 5 second before restarting BS')
    time.sleep(5)
    return 0


def startStk(instance=''):
    s = pyautogui.size()
    if s != (1920,1080):
        print("Resolution not supported: {}".format(s))
        sys.exit(-1)

    logging.info('Trying to start BS, will sleep for 30 secs')
    cmd = r'start c:\"Program Files"\BlueStacks_nxt\HD-Player.exe'
    if instance:
        if os.path.exists(r'C:\ProgramData\Bluestacks_nxt\Engine'):
            if os.path.exists(r'C:\ProgramData\Bluestacks_nxt\Engine\Rvc64_{}'.format(instance)):
                cmd += ' --instance Rvc64_{}'.format(instance)
            elif os.path.exists(r'C:\ProgramData\Bluestacks_nxt\Engine\Tiramisu64_{}'.format(instance)):
                cmd += ' --instance Tiramisu64_{}'.format(instance)
            elif os.path.exists(r'C:\ProgramData\Bluestacks_nxt\Engine\Nougat32_{}'.format(instance)):
                cmd += ' --instance Nougat32_{}'.format(instance)
            else:
                cmd += ' --instance Nougat64_{}'.format(instance)
        else:
            cmd += ' --instance Nougat32_{}'.format(instance)
        
    os.system(cmd)
    time.sleep(30)
    
    if not clickIconCenter('bs_maximize', 'Maximize BS window', 5, 0.95):
        print('  cannot find maximize button at first trial')
        pyautogui.screenshot('log/maximize_{}.jpg'.format(datetime.now().strftime('%Y%m%d')))
        clickIconCenter('bs_maximize', 'Maximize BS window', 5, 0.85)

    clickIconCenter('bs_update_close', 'Close BS update prompt', 0.5, 0.9)

    #close all app
    abClick(1900,1020)  # task button
    time.sleep(0.5)
    if not clickIconCenter('bs_task_clear', 'Task Manager Clear', 0.5, 0.9):
        while fsLocateCenterOnScreen('bs_task_screenshot.png', confidence=0.9):
            abMoveTo(950,600)
            pyautogui.mouseDown()
            time.sleep(0.1)
            abMoveTo(950,70,0.3,sm=True)
            time.sleep(0.1)
            pyautogui.mouseUp()
            time.sleep(0.8)
        abClick(1900,990)   # home button
    time.sleep(10)

def startRox():
    logging.info('Trying to start XOR, will sleep for 6 secs')
    if not clickIconCenter(['bs_rox', 'bs_rox_text'], 'Starting XOR', 6, 0.8):
        logging.error('XOR icon not found, check emulator started properly')
        return False

    #if not waitWhiteScreen():
    #    return False
    if not waitNonBlackScreen():
        return False
    openDos()

    if not waitScreen('btn_welcome_close', click=True, sleep=1, timeout=120, cf=0.97):
        logging.info('Timeout waiting for welcome screen')
        abClick(1630,130)
        abSleep(1)
        
    return True

def startNewRoxWithRetry(instance='',numRetry=XOR_START_RETRY,winTitle='',nonMax=False):
    for i in range(0,numRetry):
        if killStk(winTitle)<0:
            return False
        startStk(instance)
        if startRox():
            if winTitle and nonMax:
                for w in pyautogui.getWindowsWithTitle('ROX'):
                    if w.title == winTitle:
                        w.restore()
            #abSleep(3)
            #logging.info('Press F9')
            #pyautogui.press('f9')
            return True
        else:
            logging.info('XOR failed to start.  Retry {}'.format(i+1))
            continue
    logging.error('Sorry, XOR failed to start after max retry')
    return False

def roxLogin(charID=''):

    serverSelected=False
    if charID and os.path.exists(TPL_DIR + 'nametag{}.png'.format(charID)):
        if not waitScreen('btn_choose_char', click=True, sleep=3, timeout=10, cf=0.98):
            throwErr('RO login cannot find server select button')
            #return -3
        nameImg = 'nametag{}'.format(charID)
        if clickIconCenter(nameImg, nameImg, 3, 0.97):
            serverSelected=True
        else:
            clickIconCenter('btn_welcome_close', 'Char not found', 1, 0.97)

    if not serverSelected and not waitScreenRegion('btn_start_1', 800, 860, 1100, 1000, click=True, sleep=3, timeout=10, cf=0.6):
        # this string will be on a weather-depending bg color...
        throwErr('RO login cannot find default server string')
        #return -2
        #abMoveTo(940,900)
        #abClick()
        #abSleep(3)

    # we have to wait longer before the login screen stablized
    if not waitScreen('btn_start_2', click=True, sleep=15, timeout=10, cf=0.8):
        throwErr('RO login cannot find enter string')
        #return -3
        #abMoveTo(940,930)
        #abClick()
        #abSleep(15)

    # after login, close 2 welcome messages
    waitScreen('btn_welcome_close', click=True, sleep=3, timeout=20, cf=0.95)
    if not clickIconCenter('btn_welcome_close', 'Welcome Msg', 2, 0.95):
        abSleep(2)


def roxLogout():
    clickIconCenter('btn_revive', 'Revive', 10, 0.95)
    time.sleep(0.1)
    clickIconInRegion('ic_left_arrow2', 'Low Menu Switch', 1500, 340, 1900, 600, 1, 0.85)
    if not clickIconInRegion('ic_setting', 'Setting', 1300, 530, 1900, 900, 3, 0.85):
        logging.error('Cannot find setting icon')
        return -1
    if not clickIconInRegion('btn_logout', 'Logout', 1200, 740, 1700, 960, 3, 0.95):
        logging.error('Cannot find logout icon')
        return -2
    clickIconCenter('btn_confirm', 'Confirm', 3, 0.98)

    return 0

def roxSwitchAc(idx=''):
    if not idx:
        return 0
    
    if not waitScreenRegion('ic_switch_ac', 1600, 40, 1900, 450, timeout=20, sleep=1, click=True, cf=0.9):
        logging.error('Cannot find switch ac icon.  are you in login screen?')
        return -1
    # first account xy: 940, 350
    # next account y+100
    # note that the first ac is last used one
    # use the 2nd one to switch between ac
    if idx[0].lower() == 'g':
        clickIconCenter('ic_acc_google', 'Google login', 2, 0.98)
    elif idx[0].lower() == 'f':
        clickIconCenter('ic_acc_facebook', 'Facebook login', 2, 0.98)
    elif idx[0].lower() == 'p':
        clickIconCenter('ic_acc_gplay', 'G-Play login', 2, 0.98)
    elif os.path.exists(TPL_DIR + 'ic_acc_{}.png'.format(idx)):
        clickIconCenter('ic_acc_{}'.format(idx), 'Facebook login', 2, 0.98)
    else:
        if idx.isnumeric():
            i = int(idx)
        else:
            logging.error("Invalid account hint string: {}".format(idx))
            #clickIconCenter('btn_welcome_close', 'Close button', 2, 0.95)
            #will be stuck at un-login status, which is no good
            idx = 1
        abMoveTo(940,350+(i-1)*100)
        abClick()
        abSleep(2)
    return 0
    
def returnHomeCityByMap():
    waitScreen('btn_revive', click=True, timeout=4, sleep=10, checkInterval=0.4, cf=0.9)
    if waitScreenRegion('ic_prontera', 1600, 35, 1800, 90, timeout=2, checkInterval=0.5, cf=0.92):
        return 0
    abMoveTo(1700,200,err=50)
    abClick()
    abSleep(2)
    if clickIconCenter('ic_world_map', 'World Map', 1.5, 0.9):
        if clickIconCenter('ic_map_prontera', 'Prontera', 1.5, 0.9):
            if clickIconCenter('ic_map_xfer', 'W Transfer', 8, 0.9, (-20,-20)):
                return 0
    return -1

def returnHomeCity():
    odinFull = False

    clickIconCenter('btn_quit', 'Quit', 2, 0.9)

    waitScreen('btn_revive', click=True, timeout=4, sleep=10, checkInterval=0.4, cf=0.9)

    abMoveTo(495,110)
    abClick()
    abSleep(0.5)

    # turn off odin
    waitScreen('btn_odin_toggle', click=True, timeout=7, sleep=0.2, checkInterval=0.3, cf=0.92)

    if not clickIconCenter(['btn_get_odin', 'btn_get_odin_limit'], 'Get Odin', 0.2, 0.9):
        logging.error('Get odin button not found in odin page')
        pyautogui.screenshot('log/no_odin_{}.jpg'.format(datetime.now().strftime('%Y%m%d%H%M%S')))
        if not clickIconCenter('btn_welcome_close', 'Close', 0.2, 0.9):
            abMoveTo(1470,150)
            abClick()
            abSleep(0.5)
        return -1

    if waitScreenRegion('ic_odin_full', 960, 600, 1500, 800, timeout=1, cf=0.97):
        odinFull = True

    if not clickIconCenter('btn_home_city', 'Home City', 1):
        logging.error('Return home city button not found')
        return -2

    if waitScreenRegion('ic_prontera', 1600, 35, 1800, 90, timeout=105, checkInterval=2, cf=0.95):
        # can you walk back to city in 3.5 minutes?
        if odinFull:
            logging.info('Detect Odin Full, not waiting')
            return 999
        else:
            return 0
    else:
        # we are not sure if arrived at home city, maybe not wait for odin?
        # probably died when walking
        pyautogui.screenshot('log/no_odin_{}.jpg'.format(datetime.now().strftime('%Y%m%d%H%M%S')))
        logging.info('Detect not in home city, not waiting')
        return 999

def returnCityCenter():
    pyautogui.press('m')
    abSleep(0.5)
    abMoveTo(1455,470)
    abClick()

def waitOdin(n=datetime.now()):
    # assume we are at home city already
    #nextOdinHour = 20 if n.hour>=12 else 12 #TP timezone
    nextOdinHour = 21 if n.hour>=13 else 13 #SEA timezone
    odinTime = n.replace(hour=nextOdinHour,minute=0,second=0)
    odinDiff = (odinTime-n).total_seconds()+1
    spent = (datetime.now()-n).total_seconds()
    ss=min(1800, max(900, odinDiff))-spent
    logging.info('Wait {:02}m{:02}s to get odin'.format(ss//60,ss%60))
    time.sleep(ss)

    if fsLocateCenterOnScreen('ic_lock.png', confidence=0.9):
        # do not click the lock, click anywhere else
        logging.info('Unlock Screen')
        abMoveTo(960,550)
        abClick()
        time.sleep(0.2)

    clickIconCenter('btn_welcome_close', 'Reconnect', 1, 0.92)

def openCarnival(retry=10):
    pyautogui.press('j')
    abSleep(0.5)
    p = fsLocateCenterOnScreen('ic_carnival_close.png', confidence=0.9)
    if p:
        logging.info('   found C_Close button: {}'.format(p))
    else:
        if not waitScreen(['ic_carnival', 'ic_carnival_dot'], sleep=2, click=True, \
                checkInterval=0.5, timeout=retry, cf=0.8):
            if clickIconInRegion('ic_top_menu', 'Top Menu', 1000, 35, 1560, 480, 2, 0.8):
                if not clickIconInRegion(['ic_carnival', 'ic_carnival_dot'], 'Carnival', 
                        1000, 35, 1560, 480, 2, 0.8):
                    logging.error('Carnival button not found on Top Menu')
                    return False
    return True

def takeQuest(submitFinished=False, maxQuest=0, retry=3):
    clickIconCenter('btn_revive', 'Revive', 10, 0.95)

    if clickIconInRegion('ic_line1', 'Line 1', 1700, 35, 1840, 90, 1, 0.95):
        # change away from line 1
        if clickIconInRegion('btn_line2', 'Change line 2', 600, 210, 1300, 550, 3, 0.95):
            #clickIconCenter('btn_confirm', 'Confirm', 1, 0.93)
            waitScreen('btn_confirm', 12, click=True, cf=0.92)
        else: 
            logging.error('Cannot find line 2 button')
            abMoveTo(1250,230)
            abClick()
        abSleep(3)

    error = []
    for ret in range(0,retry):
        p = fsLocateEither(['ic_q_close', 'ic_q_close_sp'], confidence=0.98)
        if p:
            # already opened
            logging.info('   found Q_Close button: {}'.format(p))
            break

        if not openCarnival():
            error.append(-1)
            continue
    
        if not clickIconCenter('ic_questboard', 'Questboard', 2, 0.9):
            logging.error('Quest button not found in carnival')
            error.append(-2)
            continue
    
        clickGoNow = 0
        for ret2 in range(0,retry):
            if clickIconCenter(['ic_go_now', 'ic_go_now2'], 'Go now', 1, 0.9):
                clickGoNow += 1
            elif clickGoNow>0:
                # click go now for multiple times until it goes away
                break

        if not clickGoNow: 
            logging.error('Go now button not found after clicking quest')
            error.append(-3)
            pyautogui.press('esc')
            continue
        clickIconCenter('btn_butterfly_confirm', 'Use butterfly', 1, 0.9)
    
        if waitScreen(['ic_q_daily', 'ic_q_daily_sp'], cf=0.9):
            abSleep(3)
            error = False
            break
        else:
            logging.error('Timeout quest board not arrived')
            error.append(-4)

    if error:
        p = fsLocateEither(['ic_q_close', 'ic_q_close_sp'], confidence=0.98)
        if not p:
            logging.error('Questboard not arrived after retry {}, error:{}'.format(retry,error))
            return error[0]

    if maxQuest>0 or not clickIconCenter('btn_accept_all_q', 'Accept All Q', 1, 0.95):
        qn = 1
        xy = []
        for y in (400,710):
            for x in range(340,1541,300):
                #logging.debug(x,y)
                xy.append((x+20 if y<500 else x-20,y))
        random.shuffle(xy)
        for x,y in xy:
            abMoveTo(x,y)
            abClick()
            abSleep(0.8,err=0.3)
            im = fsScreenshot(region=(800,700,400,200))
            if pyautogui.locate(TPL_DIR + 'btn_q_accept2.png',im,confidence=0.98):
                logging.info('Quest {} accepted'.format(qn))
                abMoveTo(960,820,err=30)
                abClick()
                abSleep(1.1,err=0.5)
            elif pyautogui.locate(TPL_DIR + 'btn_q_submit2.png',im,confidence=0.98):
                logging.info('Quest {} completed'.format(qn))
                if submitFinished:
                    abMoveTo(960,820,err=30)
                    abClick()
                    abSleep(1.1,err=0.5)
                else:
                    abMoveTo(x,70 if y<500 else 980,err=20)
                    abClick()
                    abSleep(0.3)
            else:
                abMoveTo(x,70 if y<500 else 980,err=20)
                abClick()
                abSleep(0.3)
            if maxQuest>0 and qn>=maxQuest:
                break
            qn += 1

    abSleep(0.3)
    clickIconCenter(['ic_q_close', 'ic_q_close_sp'], 'Q_Close', 2, 0.92)

    # leave the quest board
    abMoveTo(345,800)
    pyautogui.mouseDown()
    time.sleep(0.05)
    abMoveTo(345,660,0.6,sm=True)
    abSleep(0.4)
    abMoveTo(480,680,0.6,sm=True)
    abSleep(0.4)
    pyautogui.mouseUp()
    return 0


def refreshTaskList():
    # refresh the task list
    abMoveTo(80,530)
    abClick()
    abMoveTo(80,370)
    abClick()
    abSleep(0.4)


def scrollQuestToTop():
    rx = random.randint(-20,30)

    # scroll quest list to top
    for i in range(0,3):
        abMoveTo(250+rx,350)
        pyautogui.mouseDown()
        time.sleep(0.05)
        abMoveTo(250+rx,900,0.3,sm=True)
        pyautogui.mouseUp()

def inRegion(p,x0,y0,x1,y1):
    return (x0<=p[0]<=x1 and y0<=p[1]<=y1)

def matchTpl(ir,tpl):
    return cv2.matchTemplate(ir,tpl,cv2.TM_CCOEFF_NORMED)

def findNextQuest(filetag='test', reqCommQuest=False, noScroll=False, ignoreY=0, pcVer=False):
    if pcVer:
        logging.info('  pc ver')
        tpl_daily = cv2.imread(TPL_DIR + 'tpl_daily_pc.png',0)
        tpl_qdone = cv2.imread(TPL_DIR + 'tpl_questdone_pc.png',0)
        tpl_qdone2 = cv2.imread(TPL_DIR + 'tpl_questdone2.png',0)
        tpl_qcat = cv2.imread(TPL_DIR + 'tpl_quest_howell_pc.png',0)
        tpl_catskip = None
        tpl_catwant = None
        tpl_comm = cv2.imread(TPL_DIR + 'tpl_commerce_pc.png',0)
    else:
        tpl_daily = cv2.imread(TPL_DIR + 'tpl_daily.png',0)
        tpl_qdone = cv2.imread(TPL_DIR + 'tpl_questdone.png',0)
        tpl_qdone2 = cv2.imread(TPL_DIR + 'tpl_questdone2.png',0)
        tpl_qcat = cv2.imread(TPL_DIR + 'tpl_quest_howell.png',0)
        tpl_catskip = cv2.imread(TPL_DIR + 'tpl_howell_cat.png',0)
        tpl_catwant = cv2.imread(TPL_DIR + 'tpl_howell_want.png',0)
        tpl_comm = cv2.imread(TPL_DIR + 'tpl_commerce.png',0)
        #tpl_skip_title = cv2.imread(TPL_DIR + 'tpl_quest_skip_title.png',0)
        #tpl_skip_place = cv2.imread(TPL_DIR + 'tpl_quest_skip_place.png',0)
    
    rx = random.randint(-20,30)

    for i in range(0,QUEST_NUM_PAGE):
        if inRegion(pyautogui.position(),120,300,430,650):
            abMoveTo(400+rx,250)
            abSleep(0.3)
        im = fsScreenshot(region=(120,300,310,350))
        him = cv2.cvtColor(np.array(im), cv2.COLOR_RGB2HSV)
        
        ir = cv2.inRange(him, (280//2,100,200), (296//2,160,255))
        loc = np.where(matchTpl(ir,tpl_daily) >= CONF_TEXT)
        logging.info('  quest daily {}:'.format(i))
        h,w = tpl_daily.shape
        last_y = -100
        candidate = []
        for x,y in zip(*loc[::-1]):
            #logging.info('    {},{}'.format(x,y))
            if y-last_y > 30 and 5<y<280 and 20<x<28:
                # optimal x should be 24
                # y within 20-30 pixel consider as next line
                candidate.append(y)
            last_y = y

        ### search red text
        ir = cv2.inRange(him, (12//2,160,180), (22//2,220,255))
        loc_hs = np.where(matchTpl(ir,tpl_catskip) >= CONF_TEXT) if tpl_catskip is not None else None
        #loc_sp = np.where(matchTpl(ir,tpl_skip_place) >= CONF_TEXT) if tpl_skip_place is not None else None

        ## search white text
        ir = cv2.inRange(him, (0//2,0,210), (360//2,18,255))
        loc_qb = np.where(matchTpl(ir,tpl_qdone) >= CONF_TEXT)
        loc_qb2 = np.where(matchTpl(ir,tpl_qdone2) >= CONF_TEXT)
        loc_hn = np.where(matchTpl(ir,tpl_qcat) >= CONF_TEXT)
        loc_hy = np.where(matchTpl(ir,tpl_catwant) >= CONF_TEXT) if tpl_catwant is not None else None
        loc_cm = np.where(matchTpl(ir,tpl_comm) >= CONF_TEXT)
        #loc_st = np.where(matchTpl(ir,tpl_skip_title) >= CONF_TEXT) if tpl_skip_title is not None else None

        for y in candidate:
            # y within 20-30 pixel consider as next line
            if [j for j in loc_qb[0] if j>y+20 and j<y+30]:
                logging.info('  quest pg {} y pos {:3d} is finished'.format(i,y))
            elif [j for j in loc_qb2[0] if j>y+20 and j<y+30]:
                logging.info('  quest pg {} y pos {:3d} is finished'.format(i,y))
            elif ignoreY and y==ignoreY:
                logging.info('  quest pg {} y pos {:3d} is ignored'.format(i,y))
            elif loc_hy is not None and [j for j in loc_hy[0] if j>y-3 and j<y+30] and not reqCommQuest:
                logging.info('  quest pg {} y pos {:3d} is *unfinished* by howell'.format(i,y))
                return y
            elif [j for j in loc_hn[0] if j>y-3 and j<y+30]:
                logging.info('  quest pg {} y pos {:3d} is fishing game'.format(i,y))
            elif loc_hs is not None and [j for j in loc_hs[0] if j>y+20 and j<y+30]:
                logging.info('  quest pg {} y pos {:3d} is fishing game'.format(i,y))
            elif [j for j in loc_cm[0] if j>y-3 and j<y+30]:
                logging.info('  quest pg {} y pos {:3d} is commerce req'.format(i,y))
                if reqCommQuest:
                    return y
            #elif loc_st is not None and [j for j in loc_st[0] if j>=y-2 and j<y+30]:
            #    logging.info('  quest pg {} y pos {:3d} is a title to skip'.format(i,y))
            #elif loc_sp is not None and [j for j in loc_sp[0] if j>y+20 and j<y+30]:
            #    logging.info('  quest pg {} y pos {:3d} is a place to skip'.format(i,y))
            elif not reqCommQuest:
                logging.info('  quest pg {} y pos {:3d} is *unfinished*'.format(i,y))
                return y
        if noScroll:
            return -1

        if i<QUEST_NUM_PAGE-1:
            logging.info('  scroll next page {} {}'.format(i,250+rx))
            abMoveTo(250+rx,530)
            pyautogui.mouseDown()
            time.sleep(0.05)
            abMoveTo(250+rx,290,0.8,sm=True)
            abSleep(0.8)
            pyautogui.mouseUp()
            abSleep(1.5)

    #no more quest
    return -1


def skipQuest(qy):
    rx = random.randint(-20,30)

    abMoveTo(250+rx,330+qy)
    pyautogui.mouseDown()
    time.sleep(0.05)
    abMoveTo(250+rx,290,0.8,sm=True)
    time.sleep(0.8)
    pyautogui.mouseUp()
    
    
def scrollMsg(n):
    for i in range(0,n):
        abClick(1180,900)
        abSleep(0.5)
        pyautogui.mouseDown()
        time.sleep(0.05)
        abMoveTo(1180,400,0.6,sm=True)
        time.sleep(0.1)
        pyautogui.mouseUp()
        time.sleep(0.5)
        abClick(1180,900)
        abSleep(0.5)
    
    
def runAllQuests(timeout=0,noFromTop=False,maxQuest=0,pcVer=False):
    deadline = datetime.now()+timedelta(minutes=timeout) if timeout>0 else 0

    refreshTaskList()
    if not noFromTop:
        scrollQuestToTop()

    nq = 0
    lastState = [0,0]   # last quest time and last y position
    while runQuest(deadline, lastState, pcVer):
        logging.info('Quest finished ({}), check more quest...'.format(nq))
        time.sleep(1)
        nq += 1
        if nq>=maxQuest>0:
            break
    if nq==0:
        pyautogui.screenshot('log/noquest_{}.jpg'.format(datetime.now().strftime('%Y%m%d%H%M%S')))
    logging.info('All quests finished or timeout expired')
    return nq


def runQuest(deadline=0, lastState=None, pcVer=False):

    questST = datetime.now()
    filetag = questST.strftime('%Y%m%d%H%M%S')
    logging.info('Find next quest '+filetag)
    if lastState and 0<lastState[0]<5:
        qy = findNextQuest(filetag, ignoreY=lastState[1], pcVer=pcVer)
    else:
        qy = findNextQuest(filetag, pcVer=pcVer)
    logging.info('  result:{}'.format(qy))
    if qy<0:
        return False
    if deadline and datetime.now()>deadline:
        return False
    
    lastState[1] = qy
    if inRegion(pyautogui.position(),120,300,430,650):
        abMoveTo(random.randint(350,900),250,err=30)
        abSleep(0.3)

    im = fsScreenshot(region=(120,300,310,350))
    him = cv2.cvtColor(np.array(im), cv2.COLOR_RGB2HSV)
    ir = cv2.inRange(him, (0//2,0,210), (360//2,18,255))
    ir2 = cv2.inRange(him, (11//2,120,180), (22//2,200,240))
    im_quest_title = (ir+ir2)[qy:qy+50, 24:300]

    ocr = pytesseract.image_to_string(255-im_quest_title, lang='chi_tra')
    logging.info("  1st OCR: {}, until {}".format(re.sub("\s"," ",ocr),deadline))

    im_quest_title = im_quest_title[:,:160]
    #cv2.imwrite('log/qtitle_{}.jpg'.format(filetag),im_quest_title)

    if u'哈威爾的' in ocr or u'神秘道具' in ocr:
        logging.info(' Skip fishing quest!')
        skipQuest(qy)
        abSleep(1)
        return True 

    tpl_skip = cv2.imread(TPL_DIR + 'tpl_skip.png',0)
    tpl_hp = cv2.imread(TPL_DIR + 'ic_hp.png',0)
    tpl_qdone = cv2.imread(TPL_DIR + 'tpl_questdone.png',0)
    tpl_qdone2 = cv2.imread(TPL_DIR + 'tpl_questdone2.png',0)
    tpl_qsubmit = cv2.imread(TPL_DIR + 'tpl_qsubmit.png',0)
    #tpl_qfight = cv2.imread(TPL_DIR + 'tpl_qfight.png',0)
    tpl_qfly = cv2.imread(TPL_DIR + 'tpl_qfly.png',0)
    tpl_hand = cv2.imread(TPL_DIR + 'tpl_hand.png',0)
    tpl_hand2 = cv2.imread(TPL_DIR + 'tpl_hand2.png',0)
    tpl_puzzle = cv2.imread(TPL_DIR + 'tpl_puzzle.png',0)
    tpl_photo = cv2.imread(TPL_DIR + 'tpl_photo.png',0)
    tpl_hear = cv2.imread(TPL_DIR + 'tpl_hear.png',0)
    btn_revive = cv2.imread(TPL_DIR + 'btn_revive.png',0)
    btn_shutter = cv2.imread(TPL_DIR + 'btn_shutter.png',0)
    tpl_close = cv2.imread(TPL_DIR + 'tpl_close.png',0)
    tpl_close_sp = cv2.imread(TPL_DIR + 'tpl_close_sp.png',0) if QUEST_SPECIAL_ACT else None
    tpl_close_sim = cv2.imread(TPL_DIR + 'tpl_close_simple.png',0)
    tpl_af_on = cv2.imread(TPL_DIR + 'tpl_auto_on.png',0)
    tpl_af_off = cv2.imread(TPL_DIR + 'tpl_auto_off.png',0)
    tpl_aim = cv2.imread(TPL_DIR + 'tpl_aim.png',0)

    #res = matchTpl(ir[qy:qy+50, 24:300],tpl_qfight)
    #loc = np.where(res >= CONF_TEXT)
    #logging.info('   Test pattern quest_fight:{}'.format(res.max()))
    #fight_quest = True if loc[0].size>0 else False

    force_refresh = False
    af_count = 0
    af_last = 0
    flyable = True
    hp_last = True
    flied = False
    m = re.search('(\d+)\/(\d+)(\s|$)',ocr)
    if m:
        # fight or collection quest
        af_last = int(m.group(1))

    #if QUEST_USE_FLY and not fight_quest:
    if QUEST_USE_FLY:
        abMoveTo(250,330+qy)
        abClick()
    else:
        abMoveTo(250,330+qy)
        abClick()
        abSleep(0.4)
        abClick()
        abSleep(0.4)
        abClick()
        abSleep(0.4)
        abClick()


    for i in range(0,40):
        # 144 sec = 2.4 min
        if hp_last:
            p0 = pyautogui.position()
            if not inRegion(p0,320,220,930,280):
                abMoveTo(random.randint(350,900),250,err=30)
        abSleep(1.8 if i==0 or force_refresh or flied else 3.6)

        logging.info('  iteration:{}'.format(i))
        im = np.array(fsScreenshot())

        im_chatbtn = im[300:800, 1400:1800]
        him = cv2.cvtColor(im_chatbtn, cv2.COLOR_RGB2HSV)
        ir = cv2.inRange(him, (75//2,50,230), (90//2,100,255))
        byrow = cv2.reduce(ir, 1, cv2.REDUCE_SUM, dtype=cv2.CV_32SC1).T[0]
        mm = byrow.max()//255
        logging.info('   Test pattern submit_btn:{}'.format(mm/400))
        if mm>320:
            ym = byrow.argmax()
            y1 = np.where(byrow[:ym]<300)[0][-1]
            y2 = np.where(byrow[ym:]<300)[0][0]+ym
            ymid = y1+(y2-y1)//2
            logging.info("    y_max:{}, block:{}-{}, mid:{}".format(ym,y1,y2,ymid))

            if y2-y1>60 and y2-y1<75:
                logging.info('  Submit!')
                abMoveTo(1600, 300+ymid)
                abClick()

                abSleep(2)
                if not clickIconCenter('btn_submit_quest_2', 'Submit', 1):
                    logging.info('  Fallback to click submit at 1480,880')
                    abMoveTo(1480,880)
                    abClick()
                    abSleep(1)
                ## submit quest item will finish this quest
                ## cancel the q_submit dialog for new version
                #abMoveTo(550, 550)
                #abClick()
                #lastState[0] = -1
                #return True
                
                ## Campus Story quest have more dialog after submit, cannot return
                force_refresh = True
                af_count = 0
                af_last = 0
                flyable = True
                flied = False
                continue

        #im_topright = im[40:140, 1540:1820]
        im_topright = im[40:200, 1540:1840]
        him = cv2.cvtColor(im_topright, cv2.COLOR_RGB2HSV)
        ir = cv2.inRange(him, (0//2,0,200), (360//2,27,255))
        res = matchTpl(ir,tpl_skip)
        loc = np.where(res >= 0.8)
        logging.info('   Test pattern skip_dialog:{}'.format(res.max()))
        if loc[0].size>0:
            logging.info('  NPC spoken!')
            h,w = tpl_skip.shape
            logging.info('  click at {} {}'.format(1540+loc[1][0]+w//2, 40+loc[0][0]+h//2))
            abMoveTo(1540+loc[1][0]+w//2, 40+loc[0][0]+h//2)
            abClick()

            # click skip should trigger either quest finish or progress
            # force refresh at next iteration
            force_refresh = True
            af_count = 0
            af_last = 0
            flyable = True
            flied = False
            continue

        res = matchTpl(ir,tpl_close)
        loc = np.where(res >= 0.85)
        logging.info('   Test pattern QB close:{}'.format(res.max()))
        if loc[0].size>0:
            # accidentally went to quest board
            h,w = tpl_close.shape
            logging.info('  click at {} {}'.format(1540+loc[1][0]+w//2, 40+loc[0][0]+h//2))
            abMoveTo(1540+loc[1][0]+w//2, 40+loc[0][0]+h//2)
            abClick()
            abSleep(1)
            lastState[0] = -1
            return True

        if tpl_close_sp:
            res = matchTpl(ir,tpl_close_sp)
            loc = np.where(res >= 0.85)
            logging.info('   Test pattern QB closp:{}'.format(res.max()))
            if loc[0].size>0:
                # accidentally went to quest board
                h,w = tpl_close_sp.shape
                logging.info('  click at {} {}'.format(1540+loc[1][0]+w//2, 40+loc[0][0]+h//2))
                abMoveTo(1540+loc[1][0]+w//2, 40+loc[0][0]+h//2)
                abClick()
                abSleep(1)
                lastState[0] = -1
                return True

        im_act_btn = im[330:480,1180:1330]
        him = cv2.cvtColor(im_act_btn, cv2.COLOR_RGB2HSV)
        ir = cv2.inRange(him, (0,0,235), (180,30,255))
        res = matchTpl(ir,tpl_hand)
        loc = np.where(res >= 0.8)
        logging.info('   Test pattern hand:{}'.format(res.max()))
        if loc[0].size>0:
            logging.info('  Action!')
            h,w = tpl_hand.shape
            abMoveTo(1180+loc[1][0]+w//2, 330+loc[0][0]+h//2)
            abClick()
            abSleep(2)
            
            force_refresh = True
            af_count = 0
            af_last = 0
            flyable = True
            flied = False
            continue

        res = matchTpl(ir,tpl_hand2)
        loc = np.where(res >= 0.8)
        logging.info('   Test pattern hand2:{}'.format(res.max()))
        if loc[0].size>0:
            logging.info('  Action2!')
            h,w = tpl_hand.shape
            abMoveTo(1180+loc[1][0]+w//2, 330+loc[0][0]+h//2)
            abClick()
            abSleep(2)
            
            force_refresh = True
            af_count = 0
            af_last = 0
            flyable = True
            flied = False
            continue

        res = matchTpl(ir,tpl_hear)
        loc = np.where(res >= 0.8)
        logging.info('   Test pattern hear:{}'.format(res.max()))
        if loc[0].size>0:
            logging.info('  Listen!')
            h,w = tpl_hear.shape
            logging.info('  click at {} {}'.format(1200+loc[1][0]+w//2, 330+loc[0][0]+h//2+150))
            abMoveTo(1180+loc[1][0]+w//2, 330+loc[0][0]+h//2)
            abClick()
            abSleep(2)

            force_refresh = True
            af_count = 0
            af_last = 0
            flyable = True
            flied = False
            continue

        im_fly = im[330:530, 1200:1420]
        him = cv2.cvtColor(im_fly, cv2.COLOR_RGB2HSV)
        ir = cv2.inRange(him, (0//2,0,200), (360//2,27,255))
        #if QUEST_USE_FLY and flyable and not fight_quest:
        if QUEST_USE_FLY and flyable:
            res = matchTpl(ir,tpl_qfly)
            loc = np.where(res >= 0.8)
            logging.info('   Test pattern fly:{}'.format(res.max()))
            if loc[0].size>0:
                # use fly
                h,w = tpl_qfly.shape
                logging.info('  click at {} {}'.format(1200+loc[1][0]+w//2, 330+loc[0][0]+h//2+150))
                abMoveTo(1200+loc[1][0]+w//2, 330+loc[0][0]+h//2+150)
                abClick()
                flyable = False
                flied = True
                continue
        else:
            res = matchTpl(ir,tpl_close_sim)
            loc = np.where(res >= 0.8)
            logging.info('   Test pattern fly_close:{}'.format(res.max()))
            if loc[0].size>0:
                # do not use fly
                h,w = tpl_close_sim.shape
                logging.info('  click at {} {}'.format(1200+loc[1][0]+w//2, 330+loc[0][0]+h//2))
                abMoveTo(1200+loc[1][0]+w//2, 330+loc[0][0]+h//2)
                abClick()

        res = matchTpl(ir,tpl_puzzle)
        loc = np.where(res >= 0.8)
        logging.info('   Test pattern puzzle:{}'.format(res.max()))
        if loc[0].size>0:
            logging.info('  Do puzzle!')
            h,w = tpl_puzzle.shape
            logging.info('  click at {} {}'.format(1200+loc[1][0]+w//2, 330+loc[0][0]+h//2+150))
            abMoveTo(1200+loc[1][0]+w//2, 330+loc[0][0]+h//2+100)
            abClick()
            abSleep(2)

            force_refresh = True
            af_count = 0
            af_last = 0
            flyable = True
            flied = False
            continue

        res = matchTpl(ir,tpl_photo)
        loc = np.where(res >= 0.8)
        logging.info('   Test pattern photo:{}'.format(res.max()))
        if loc[0].size>0:
            logging.info('  Take photo!')
            h,w = tpl_photo.shape
            logging.info('  click at {} {}'.format(1200+loc[1][0]+w//2, 330+loc[0][0]+h//2+150))
            abMoveTo(1200+loc[1][0]+w//2, 330+loc[0][0]+h//2+100)
            abClick()
            abSleep(2)

            force_refresh = True
            af_count = 0
            af_last = 0
            flyable = True
            flied = False
            continue

        im_botright = im[860:980, 1400:1700]
        him = cv2.cvtColor(im_botright, cv2.COLOR_RGB2GRAY)
        res = matchTpl(him,btn_revive)
        loc = np.where(res >= 0.8)
        logging.info('   Test pattern revive:{}'.format(res.max()))
        if loc[0].size>0:
            logging.info('  Dead!')
            skipQuest(qy)
            abSleep(1)
            abMoveTo(1450+loc[1][0], 885+loc[0][0])
            abClick()
            # map loading time
            abSleep(10)
            lastState[0] = -1
            return True

        res = matchTpl(him,btn_shutter)
        loc = np.where(res >= 0.8)
        logging.info('   Test pattern shutter:{}'.format(res.max()))
        if loc[0].size>0:
            logging.info('  Do shutter!')
            skipQuest(qy)
            abSleep(1)
            abMoveTo(1400+loc[1][0], 860+loc[0][0])
            abClick()
            abSleep(1)
            force_refresh = True
            flyable = True
            flied = False
            continue

        im_topleft = im[40:160, 60:460]
        him = cv2.cvtColor(im_topleft, cv2.COLOR_RGB2GRAY)
        res = matchTpl(him,tpl_hp)
        rmx = res.max()
        logging.info('   Test pattern status_hp:{}'.format(rmx))
        if rmx<0.97:
            # probably loading map etc
            abSleep(2)
            hp_last = False
            flied = False
            continue
        hp_last = True

        im_prompt = im[780:850, 880:1060]
        him = cv2.cvtColor(im_prompt, cv2.COLOR_BGR2HSV)
        ir = cv2.inRange(him, (0//2,0,210), (360//2,18,255))
        res = matchTpl(ir,tpl_qsubmit)
        rmx = res.max()
        logging.info('   Test pattern q_submit:{}'.format(rmx))
        if rmx>=0.76:
            # quest finished
            qtime = datetime.now()-questST
            logging.info('Quest Done! spent:{}'.format(qtime))
            abMoveTo(550, 550)
            abClick()
            abSleep(0.2)
            lastState[0] = qtime.seconds
            return True

        #im_qb = im[300:650, 120:430]
        #im_quest = im_qb[qy:qy+50]
        #im_quest_title = ir[qy:qy+50, 24:444]
        im_quest = im[290+qy:360+qy, 120:430]
        him = cv2.cvtColor(im_quest, cv2.COLOR_RGB2HSV)
        ir = cv2.inRange(him, (0//2,0,210), (360//2,18,255))
        res = matchTpl(ir,tpl_qdone)
        loc = np.where(res >= CONF_TEXT)
        logging.info('   Test pattern quest_done:{}'.format(res.max()))
        if loc[0].size>0:
            # quest finished
            qtime = datetime.now()-questST
            logging.info('Quest Done! spent:{}'.format(qtime))
            lastState[0] = qtime.seconds
            return True
        res = matchTpl(ir,tpl_qdone2)
        loc = np.where(res >= CONF_TEXT)
        logging.info('   Test pattern quest_don2:{}'.format(res.max()))
        if loc[0].size>0:
            # quest finished
            qtime = datetime.now()-questST
            logging.info('Quest Done! spent:{}'.format(qtime))
            lastState[0] = qtime.seconds
            return True
        
        if flied:
            # still no same map after fly but no submit or npc action
            # click the quest title again to turn on AF
            logging.info('  Same map fight quest, try enable AF')
            abMoveTo(250,330+qy)
            abClick()
            flied = False

        ocr = pytesseract.image_to_string(255-ir, lang='chi_tra')
        logging.info("   Quest OCR: {}".format(re.sub("\s"," ",ocr)))
        m = re.search('(\d+)[\/\s]+(\d+)',ocr)
        if m and int(m.group(1)) == af_last:
            im_auto = im[730:860,1130:1260]
            ir_auto = cv2.inRange(cv2.cvtColor(im_auto, cv2.COLOR_RGB2HSV), (0,0,235), (180,45,255))
            res1 = matchTpl(ir_auto,tpl_af_on).max()
            res2 = matchTpl(ir_auto,tpl_af_off).max()
            im_aim = im[920:1020,1500:1600]
            ir_aim = cv2.inRange(cv2.cvtColor(im_aim, cv2.COLOR_RGB2HSV), (0,0,210), (180,55,255))
            res3 = matchTpl(ir_aim,tpl_aim).max()
            logging.info('   Test pattern autofight:{:.2},{:.2},{:2f},{},{}'.format(res1,res2,res3,af_last,af_count))
            if res1>0.8 and res2<0.5 and res3>0.8:
                if af_count >= 4:
                    logging.info('  Atk!')
                    abMoveTo(1670,880)
                    abClick()
                    af_count = 0
                else:
                    af_count += 1
        else:
            af_count = 0

        res = matchTpl(ir,im_quest_title)
        rmx = res.max()
        logging.info('   Test pattern quest_title:{}'.format(rmx))
        if rmx < CONF_TEXT-0.5 or force_refresh:
            # quest text changed
            unfinished = False
            m = re.search('(\d+)\/(\d+)(\s|$)',ocr)
            if m:
                # fight or collection quest
                haveN = int(m.group(1))
                needN = int(m.group(2))
                if haveN != needN:
                    logging.info('  Seems unfinished {}/{}!'.format(haveN,needN))
                    af_last = haveN
                    unfinished = True

            nt = ir[10:60, 24:184]
            quest_text_blank = False if nt.max()>0 else True

            if (not unfinished and not quest_text_blank) or force_refresh:
                logging.info('  Changed!')
                force_refresh = False
                af_last = 0

                #res = matchTpl(ir[10:60, 24:300],tpl_qfight)
                #loc = np.where(res >= CONF_TEXT)
                #logging.info('   Test pattern quest_fight:{}'.format(res.max()))
                #fight_quest = True if loc[0].size>0 else False

                #if QUEST_USE_FLY and not fight_quest:
                if QUEST_USE_FLY:
                    abMoveTo(250,330+qy)
                    abClick()
                else:
                    abMoveTo(250,330+qy)
                    abClick()
                    abSleep(0.4)
                    abClick()
                    abSleep(0.4)
                    abClick()
                    abSleep(0.4)
                    abClick()
                    # even number clicks in case really false detection will not change auto fight

                if not unfinished and not quest_text_blank:
                    # check blank in quest title after crop
                    im_quest_title = nt
                    #cv2.imwrite('log/qtitle_{}_{}.jpg'.format(filetag,i),im_quest_title)
                continue

        if deadline and datetime.now()>deadline:
            logging.info('  Timeout for quests!')
            return False

        force_refresh = False

        
    qtime = datetime.now()-questST
    logging.info('  Too long! spent:{}'.format(qtime))
    skipQuest(qy)
    lastState[0] = -1
    return True


def armwrestling(noSaveName, gotoSeat): 

    def goBackToSeat(im_icons):
        b = pyautogui.locate(TPL_DIR + 'ic_carnival_small.png', im_icons, confidence=0.85)
        if not b:
            bm = pyautogui.locate(TPL_DIR + 'ic_top_menu_small.png', im_icons, confidence=0.85)
            if bm:
                p = (530+bm[0]+bm[2]//2, 30+bm[1]+bm[3]//2)
                logging.info('   click top menu at: {}'.format(p))
                abClick(p)
                abSleep(1.5)
                im_icons = fsScreenshot(region=(530,30,850,260))
                b = pyautogui.locate(TPL_DIR + 'ic_carnival_small.png', im_icons, confidence=0.85)
        if b:
            p = (530+b[0]+b[2]//2, 30+b[1]+b[3]//2)
            logging.info('   click carnival at: {}'.format(p))
            abClick(p)
            abSleep(2)
            clickIconInRegion('ic_armw_carnival', 'Armw', 0, 0, 1000, 600, 1, 0.8)
            clickIconInRegion('ic_armw_move', 'Move', 0, 0, 1000, 600, 4, 0.8)
            return True

    if fsLocateCenterOnScreen('ic_lock_small.png', confidence=0.9):
        # do not click the lock, click anywhere else
        logging.info('Unlock Screen')
        abMoveTo(150,150)
        abClick()

    tpl_minigame = cv2.imread(TPL_DIR + 'tpl_minigame.png',0)
    tpl_lock = cv2.imread(TPL_DIR + 'tpl_lock_small.png',0)
    numGame = 0
    inactCnt = 0
    moveCnt = 0
    waitCnt = 0

    blacklist = []
    for f in glob(TPL_DIR + 'armw_black*.png'):
        blacklist.append(Image.open(f))
    logging.info('Loaded {} blacklist'.format(len(blacklist)))

    if gotoSeat:
        im_icons = fsScreenshot(region=(530,30,850,260))
        if goBackToSeat(im_icons):
            logging.info('Wait 30 secs more...')
            abSleep(30)
        else:
            logging.info('Cannot go back to seat')

    while inactCnt<180:
        im = fsScreenshot(region=(0,0,1000,600))

        #im_accept = im.crop((260,150,400,220))
        im_accept = im.crop((80,150,400,220))
        b = pyautogui.locate(TPL_DIR + 'btn_armw_agree.png', im_accept, confidence=0.8)
        if b:
            blacked = False
            for bl in blacklist:
                if pyautogui.locate(bl, im_accept, confidence=0.9):
                    blacked = True
                    break
            if blacked:
                logging.info('  Reject invitation!')
                abClick(378,160)
                abSleep(2)
                continue
                
            logging.info('  Accept invitation!')
            p = (80+b[0]+b[2]//2, 150+b[1]+b[3]//2)
            abMoveTo(p)
            abClick()
            waitCnt = 0
            numGame = 0
            ocr = pytesseract.image_to_string(im_accept, lang='chi_tra')
            logging.info("  OCR name: {}".format(re.sub("\s+"," ",ocr)))
            if not noSaveName:
                filetag = datetime.now().strftime('%Y%m%d%H%M')
                logfile = 'log/armwrestling_{}.jpg'.format(filetag)
                for seq in range(10):
                    if not os.path.exists(logfile):
                        break
                    logfile = 'log/armwrestling_{}-{}.jpg'.format(filetag,seq)
                im_accept.save(logfile)
            abSleep(5.5)
            continue

        im_armbtn = im.crop((780,250,950,420))
        b = pyautogui.locate(TPL_DIR + 'btn_armw.png', im_armbtn, confidence=0.75)
        if b:
            logging.info('  Choose game!')
            p = (780+b[0]+b[2]//2, 250+b[1]+b[3]//2)
            abMoveTo(p)
            abClick()
            abSleep(3)
            continue

        im_waitlist = im.crop((710,50,800,150))
        if pyautogui.locate(TPL_DIR + 'ic_armw.png', im_waitlist, confidence=0.75):
            if waitCnt == 0:
                logging.info('  Wait for invitation...')
            else:
                print('{}'.format(waitCnt), end="\r", flush=True)
            inactCnt = 0
            numGame = 0
            waitCnt += 1
            abSleep(3)
            continue

        im_getready = im.crop((360,60,640,150))
        if pyautogui.locate(TPL_DIR + 'ic_armw_getready.png', im_getready, confidence=0.8):
            logging.info('  Get ready...')
            inactCnt = 0
            abSleep(1)
            abClick(880,500)
            abSleep(4)
            continue

        #im_winner = im.crop((350,270,650,370))
        #if pyautogui.locate(TPL_DIR + 'ic_armw_winner.png', im_winner, confidence=0.8):
        #    logging.info('  Game finished!')

        im_win_buttons = im.crop((270,470,740,540))
        if numGame<2:
            #print('Detect again button {}'.format(numGame))
            b = pyautogui.locate(TPL_DIR + 'btn_armw_again.png', im_win_buttons, confidence=0.7)
            if b:
                logging.info('  Again!')
                p = (270+b[0]+b[2]//2, 470+b[1]+b[3]//2)
                abMoveTo(p)
                abClick()
                numGame += 1
                abSleep(2)
                continue

        isQuit=False
        for qimg in ('','2','3'):
            b = pyautogui.locate(TPL_DIR + 'btn_armw_quit{}.png'.format(qimg), im_win_buttons, confidence=0.7)
            if b:
                logging.info('  Quit! '+qimg)
                p = (270+b[0]+b[2]//2, 470+b[1]+b[3]//2)
                abMoveTo(p)
                abClick()
                abSleep(7)
                isQuit = True
                break
        if isQuit:
           continue 

        im_gameicon = im.crop((600,290,780,450))
        im1 = cv2.cvtColor(np.array(im_gameicon), cv2.COLOR_BGR2HSV)
        ir = cv2.inRange(im1, (0,0,235), (180,30,255))
        #cv2.imwrite('screencap/tpl_minigame3.png',ir)
        res = matchTpl(ir,tpl_minigame)
        #logging.info('   Test pattern minigame:{}'.format(res.max()))
        loc = np.where(res >= 0.75)
        if loc[0].size>0:
            hmm = int(datetime.now().strftime('%H%M'))
            if ARMW_COOLDOWN_AT[0] <= hmm <= ARMW_COOLDOWN_AT[1]:
                logging.info('  Time reach cooldown period:{}, quit now'.format(hmm))
                break
            logging.info('  Enter game!')
            h,w = tpl_minigame.shape
            abMoveTo(600+loc[1][0]+w//2, 290+loc[0][0]+h//2)
            abClick()
            moveCnt = 0
            waitCnt = 0
            numGame = 0
            abSleep(1)
            continue

        im_lock = im.crop((460,200,550,290))
        im1 = cv2.cvtColor(np.array(im_lock), cv2.COLOR_BGR2HSV)
        ir = cv2.inRange(im1, (240//2,0,50), (330//2,30,170))
        res = matchTpl(ir,tpl_lock)
        #logging.info('   Test pattern lock:{}'.format(res.max()))
        loc = np.where(res >= 0.75)
        if loc[0].size>0:
            logging.info('Unlock Screen')
            abMoveTo(150,150)
            abClick()
            abSleep(1)
            continue

        im_close = im.crop((710,210,790,300))
        if pyautogui.locate(TPL_DIR + 'btn_close_small.png', im_close, confidence=0.8):
            logging.info('Reconnected!')
            abMoveTo(750,250)
            abClick()
            abSleep(1)
            continue

        if moveCnt>20:
            im_icons = im.crop((530,30,850,260))
            if goBackToSeat(im_icons):
                moveCnt = 0
                continue

        im_location = im.crop((850,30,970,80))
        if pyautogui.locate(TPL_DIR + 'ic_armw_barloc.png', im_location, confidence=0.8):
            if inactCnt > 0:
                inactCnt = 0
                logging.info('  Wait for settle...')
                abSleep(3.5)
                continue
            waitMouseFree(5)
            if moveCnt == 0:
                logging.info('  Move slightly!')
            else:
                print('{}'.format(moveCnt), end="\r", flush=True)
            ry = random.randint(-20,30)
            moveX = 15 #+ moveCnt//2*6
            moveY = 20 #+ moveCnt//2*6
            if moveCnt%2 == 0:
                pyautogui.moveTo(165,480+ry)
                pyautogui.mouseDown()
                pyautogui.moveTo(165+moveX,480+moveY+ry,0.5,pyautogui.easeInOutQuad)
                pyautogui.mouseUp()
            else:
                pyautogui.moveTo(165,480+ry)
                pyautogui.mouseDown()
                pyautogui.moveTo(165-moveX,480-moveY+ry,0.5,pyautogui.easeInOutQuad)
                pyautogui.mouseUp()
            inactCnt = 0
            moveCnt += 1
            abSleep(min(2 + moveCnt//4,6))
            continue

        else:
            logging.info('  Inactive ({},{})'.format(numGame,inactCnt))
            inactCnt += 1
            moveCnt = 0
            waitCnt = 0
            abSleep(3)

def imcrop(im,y1,y2,x1,x2,nonMax=False):
    if nonMax:
        y1 = int((y1-35.0)/1.77+35)
        y2 = int((y2-35.0)/1.77+35)
        x1 = int((x1-50.0)/1.77)
        x2 = int((x2-50.0)/1.77)
    return im[y1:y2,x1:x2]


def fishing(maxQuest=200,debug=False,pcVer=False,waitSec=0): 
    def appoxColor(p, c, err=3):
        for i in range(0,3):
            if abs(p[i]-c[i])>err:
                return False
        return True

    if pcVer:
        pready = (1609,708)
        c0 = (247, 233, 222)
        c1 = (237, 224, 213)
        pfish = (1614,714)
        cfish = (214, 234, 156)
        #cfish2 = (221, 240, 161)
        click_x, click_y = 1650,760
    else:
        pready = (1526,711)
        c0 = (249, 233, 224)
        c1 = (214, 200, 192)
        pfish = (1530,714)
        cfish = (212, 242, 146)
        click_x, click_y = 1560,760
    for i in range(0,maxQuest):
        rn1 = random.randint(-10,10)
        hit = (click_x+rn1,click_y+rn1)
        n = 0
        logging.info(f'   {i}: wait for ready')
        while True:
            rgb = pyautogui.pixel(*pready)
            if n==0:
                print(f"   -RGB at {pready}: {rgb}")
                n+=1
            if appoxColor(rgb,c0,1) or appoxColor(rgb,c1,1):
                break
        if waitSec:
            time.sleep(random.random()*waitSec)
        pyautogui.click(hit)
        logging.info(f'   {i}: wait for fish')
        isWhite = False
        while True:
            r,g,b = pyautogui.pixel(*pfish)
            if debug:
                print(f"   +RGB at {pfish}: {r},{g},{b}")
            if appoxColor((r,g,b),cfish,4):
                break
            if not isWhite:
                if r>=g>=b>=210:
                    isWhite = True
            else:
                if g>=r>=210 and b<190:
                    print(f"   *RGB at {pfish}: {r},{g},{b} trigger!")
                    break
        pyautogui.click(hit)
        logging.info(f'   {i}: done')
        time.sleep(4)


def farming(nonMax=False,pcVer=False): 
                               
    if pcVer:
        nonMax = True
        tpl_hand = cv2.imread(TPL_DIR + 'tpl_hand_small.png',0)
        tpl_pick = cv2.imread(TPL_DIR + 'tpl_picking_small_pc.png',0)
        tpl_chal = [
            cv2.imread(TPL_DIR + 'tpl_challenge_small_pc.png',0),
            cv2.imread(TPL_DIR + 'tpl_challenge_small_pc2.png',0)
            ]
        tpl_prefix = cv2.imread(TPL_DIR + 'tpl_2_small.png',0)
        tpl_1x1  = cv2.imread(TPL_DIR + 'tpl_math_1x1_small.png',0)
        tpl_x1   = cv2.imread(TPL_DIR + 'tpl_math_x1_small.png',0)
    elif nonMax:
        tpl_hand = cv2.imread(TPL_DIR + 'tpl_hand_small.png',0)
        tpl_pick = cv2.imread(TPL_DIR + 'tpl_picking_small.png',0)
        tpl_chal = [cv2.imread(TPL_DIR + 'tpl_challenge_small.png',0)]
        tpl_prefix = cv2.imread(TPL_DIR + 'tpl_2_small.png',0)
        tpl_1x1  = cv2.imread(TPL_DIR + 'tpl_math_1x1_small.png',0)
        tpl_x1   = cv2.imread(TPL_DIR + 'tpl_math_x1_small.png',0)
    else:
        tpl_hand = cv2.imread(TPL_DIR + 'tpl_hand.png',0)
        tpl_pick = cv2.imread(TPL_DIR + 'tpl_picking.png',0)
        tpl_chal = [cv2.imread(TPL_DIR + 'tpl_challenge.png',0)]
        tpl_prefix = cv2.imread(TPL_DIR + 'tpl_8.png',0)
        tpl_x1 = None

    last_act = False
    num_pick = 0
    for i in range(0,400):

        logging.info('  farming:{}/{}'.format(num_pick,i))
        im = np.array(fsScreenshot())

        im_act_btn = imcrop(im,370,500,1100,1230,nonMax)
        him = cv2.cvtColor(im_act_btn, cv2.COLOR_RGB2HSV)
        ir = cv2.inRange(him, (0,0,235), (180,30,255))
        res = matchTpl(ir,tpl_hand)
        loc = np.where(res >= 0.84)
        logging.info('   Test pattern hand:{}'.format(res.max()))
        if loc[0].size>0:
            if last_act=='pick':
                logging.info('  Repeated action, probably exhaused or expired')
                break
            logging.info('  Action!')
            num_pick += 1
            h,w = tpl_hand.shape
            abMoveTo(1100+loc[1][0]+w//2, 370+loc[0][0]+h//2, nm=nonMax)
            abClick()
            last_act = 'pick'
            abSleep(1.2)
            continue

        #im_picktxt = im[650:720,900:1000]
        im_picktxt = imcrop(im,650,720,900,1000,nonMax)
        him = cv2.cvtColor(im_picktxt, cv2.COLOR_RGB2HSV)
        ir = cv2.inRange(him, (0//2,0,210), (360//2,18,255))
        res = matchTpl(ir,tpl_pick)
        loc = np.where(res >= 0.78)
        logging.info('   Test pattern pick:{}'.format(res.max()))
        if loc[0].size>0:
            logging.info('  Picking!')
            abSleep(4.5,err=0.4)
            last_act = False
            continue

        #im_challenge = im[420:500,760:1130]
        #im_challenge = imcrop(im,420,500,760,1130,nonMax)
        im_challenge = imcrop(im,390,530,730,1160,nonMax)
        him = cv2.cvtColor(im_challenge, cv2.COLOR_RGB2HSV)
        ir = cv2.inRange(him, (0,0,150), (180,255,255))
        res = []
        for tpl in tpl_chal:
            res.append(matchTpl(ir,tpl).max())
        logging.info('   Test pattern challenge:{}'.format(max(res)))
        if max(res)>0.78:
            questST = datetime.now()
            filetag = questST.strftime('%Y%m%d%H%M%S')
            #im_math = im[500:550,880:1010]
            im_math = imcrop(im,500,550,880,1010,nonMax)
            cv2.imwrite('log/math_{}.jpg'.format(filetag),im_math)
            him = cv2.cvtColor(im_math, cv2.COLOR_RGB2HSV)
            ir = 255-cv2.inRange(him, (0,0,245), (255,5,255))
            h, w = tpl_prefix.shape
            ir[:h,:w] = tpl_prefix
            ocr = pytesseract.image_to_string(ir, lang='eng', 
                    config=r'--psm 6 -c tessedit_char_whitelist=0123456789+-x*').strip()
            logging.info('  Question: {}'.format(ocr))
            ans = None
            if tpl_1x1 is not None:
                rmx_1x1 = matchTpl(ir,tpl_1x1).max()
                if rmx_1x1>0.9:
                    logging.info('  1x1:True {}'.format(rmx_1x1))
                    ans = 1
            if tpl_x1 is not None:
                rmx_x1 = matchTpl(ir,tpl_x1).max()
                if rmx_x1>0.82:
                    logging.info('  x1:True {}'.format(rmx_x1))
                    m = re.match('[82](10|\d)',ocr)
                    if m:
                        ans = int(m.group(1))
            if not ans:
                m = re.match('[82](10|\d)([\+\-\*\/4]){0,2}(\d)$',ocr)
                if not m:
                    cv2.imwrite('log/math_err_{}.jpg'.format(filetag),ir)
                    logging.error('Math Parse Error')
                    break
                x = int(m.group(1))
                y = int(m.group(3))
                if m.group(2) in ('+','4','4+','+4'):
                    ans = x + y
                elif m.group(2) == '-':
                    ans = x - y
                else:
                    ans = x * y
            print('  Answer: {}'.format(ans))
            #abSleep(0.5,err=0.2)
            abMoveTo(940,580, nm=nonMax)
            abClick()
            abSleep(0.2)
            enterNumPad(ans, (35,160), nonMax)
            abSleep(0.1)
            abMoveTo(940,720, nm=nonMax)
            abClick()
            abSleep(0.3)
            last_act = 'math'
            continue

        logging.info('  Waiting!')
        abSleep(1)
        
        #logging.info('  Unknown state, end farming.')
        #break
        last_act = False


def enterNumPad(n, offset=(0,0), nonMax=False):
    numpadXY = [
        [1480,530], #0
        [1180,430], #1
        [1280,430], #2
        [1380,430], #3
        [1180,530], #4
        [1280,530], #5
        [1380,530], #6
        [1180,630], #7
        [1280,630], #8
        [1380,630], #9
        ]
    ok = [1480,630]
    cancel = [1480,430]
    for i in str(n):
        p = numpadXY[int(i)] 
        abMoveTo(p[0]+offset[0], p[1]+offset[1], nm=nonMax)
        abClick()
        abSleep(0.2)
    abMoveTo(ok[0]+offset[0], ok[1]+offset[1], nm=nonMax)
    abClick()

def commQuest(maxQuest=0,buy20=False):
    def openCommQuest(retry=1):
        if not openCarnival(retry):
            return -1
        if not clickIconCenter('btn_commerce', 'Commerce Btn', 0.8, 0.9):
            logging.error('Cannot find commerce in carnival')
            clickIconCenter('ic_carnival_close', 'Close', 0.8, 0.8)
            return -2
        if not clickIconCenter(['ic_go_now', 'ic_go_now2'], 'Go now', 0.8):
            logging.error('Go now button not found after clicking quest')
            clickIconCenter('ic_carnival_close', 'Close', 0.8, 0.8)
            clickIconCenter('ic_carnival_close', 'Close', 0.8, 0.8)
            return -3
        if clickIconCenter('btn_butterfly_confirm', 'Use butterfly', 8):
            # when in non-city map, use fly to arrive NPC
            # click the commerce chamber NPC head
            abMoveTo(950,530)
            abClick()
            abSleep(0.8)
    
    def takeCatChamberQuest():
        #button will appear in range 1380-1800,520-800
        if not waitScreen('btn_comm_tq', click=True, sleep=2, cf=0.95):
            logging.error('Cannot find commerce NPC') 
            pyautogui.screenshot('log/no_commquest_{}.jpg'.format(datetime.now().strftime('%Y%m%d%H%M%S')))
            return -4
        if not fsLocateCenterOnScreen('btn_comm_giveup.png', confidence=0.9):
            if not clickIconInRegion('btn_comm_accept', 'Accept', 1200,700,1600,950, 1, 0.9):
                logging.error('Cannot find cat chamber')
                return -5
        if not clickIconCenter('btn_comm_close', 'Close', 0.8):
            logging.error('Cannot find close btn')
        return 0

    useQuestList = True
    defaultBuy = 20 if buy20 else 15
    if not maxQuest:
        maxQuest = 10
    for cur_q in range(maxQuest):
        opened = False
        if cur_q==0:
            openCommQuest()
            if waitScreen('btn_comm_submit', click=True, timeout=3, sleep=0.8, cf=0.87):
                logging.info(f'Assume Cat Chamber taken')
                opened = True
            else:
                if takeCatChamberQuest()<0:
                    # click anywhere to close NPC dialog
                    abMoveTo(720,120)
                    abClick()
                    return
                refreshTaskList()
                qy = findNextQuest(reqCommQuest=True)
                if qy>0:
                    abMoveTo(250,330+qy)
                    abClick()
                    abSleep(0.5)
                else:
                    useQuestList = False
                    openCommQuest()
        else:
            if useQuestList:
                abSleep(0.4)
                qy = findNextQuest(reqCommQuest=True,noScroll=True)
                if qy>0:
                    abMoveTo(250,330+qy)
                    abClick()
                    abSleep(0.5)
                else:
                    logging.info(f'No more quest: {cur_q}')
                    break
            else:
                openCommQuest()
        if not opened and not clickIconCenter('btn_comm_submit', 'Commerce', 0.8, 0.87):
            logging.error(f'Cannot find submit btn for quest {cur_q}')
            # click anywhere to close NPC dialog
            abMoveTo(720,120)
            abClick()
            clickIconCenter('btn_comm_close', 'Close', 0.8)
            return -6

        #filetag = datetime.now().strftime('%Y%m%d%H%M%S')
        im = np.array(fsScreenshot(region=(1240,292,70,24)))
        #cv2.imwrite('screencap/comm_item_{}.png'.format(filetag),im)
        him = cv2.cvtColor(im, cv2.COLOR_RGB2HSV)
        ir = 255-cv2.inRange(him, (0//2,0,190), (360//2,20,255))
        ocr_config = r'--psm 6 -c tessedit_char_whitelist=0123456789/'
        ocr = pytesseract.image_to_string(ir, lang='eng', config=ocr_config).strip()
        logging.info(" CQ:{} OCR result: {}".format(cur_q,re.sub("\s"," ",ocr)))
        #cv2.imwrite('screencap/comm_item_cnt_tpl.png',ir)
        m = re.search('(\d+)\/(\d+)\s*$',ocr)
        if m:
            haveN = int(m.group(1))
            needN = int(m.group(2))
        else:
            haveN = 0
            needN = defaultBuy
        if haveN < needN and (needN==15 or needN==20):
            buyN = needN - haveN
        else:
            buyN = defaultBuy

        if clickIconCenter('btn_comm_submit2', 'Submit', 1, 0.9):
            if clickIconCenter('btn_comm_takeout2', 'Take Out2', 0.5):
                # try take out
                abMoveTo(960,620)
                abClick()
                abSleep(0.5)
                enterNumPad(buyN,(-390,-180))
                abSleep(0.2)
                clickIconCenter('btn_comm_takeout_ok', 'Confirm', 0.5)
                clickIconCenter('btn_comm_submit2', 'Submit', 1, 0.9)
            if not fsLocateCenterOnScreen('btn_comm_submit2.png', confidence=0.9):
                # submit success
                continue

        logging.info(' Quest {} buy {}'.format(cur_q,buyN))
        if clickIconCenter('btn_comm_takeout', 'Take Out', 0.5):
            # try take out
            abMoveTo(960,620)
            abClick()
            abSleep(0.5)
            enterNumPad(buyN,(-390,-180))
            abSleep(0.2)
            clickIconCenter('btn_comm_takeout_ok', 'Confirm', 0.5)
        elif clickIconCenter('btn_comm_buynow', 'Buy Now', 0.5, 0.9):
            # try buy now
            # number pre-calculated
            #abMoveTo(910,720)
            #abClick()
            #abSleep(0.5)
            #enterNumPad(buyN,(0,+80))
            abSleep(0.2)
            clickIconCenter('btn_comm_buynow_ok', 'Confirm', 0.5)
        else:
            logging.error(f'Cannot find buy btn for quest {cur_q}')
            clickIconCenter('btn_comm_close', 'Close', 0.8)
            return -7
        clickIconCenter('btn_comm_submit2', 'Submit', 0.8, 0.9)

        # in case submit fail, close quest
        if clickIconCenter('btn_comm_close', 'Close', 0.8):
            logging.error(f'Quest not done, probably takeout fail: {cur_q}')
            clickIconCenter('btn_comm_close', 'Close', 0.8)
            return -8
    return cur_q
                

def guildQuest(maxQuest=0):
    def openGuildQuest():
        if waitScreen('ic_guild_close', timeout=2, cf=0.96):
            # already opened
            return 0
        clickIconInRegion('ic_left_arrow2', 'Low Menu Switch', 1500, 340, 1900, 600, 1, 0.9)
        if not clickIconInRegion('ic_guild', 'Quild', 1300, 530, 1900, 900, 1.2, 0.9):
            logging.error('Cannot find guild icon')
            return -1
        #if not clickIconCenter('ic_guild_act', 'Quild Activity', 0.5, 0.94):
            # broadcast msg will cover the button
            #logging.error('Cannot find guild activity')
            #return -2
        abMoveTo(800,200)
        abClick()
        abSleep(0.5)
        if not clickIconCenter('ic_guild_buy', 'Quild Quest', 3, 0.94):
            logging.error('Cannot find guild quest')
            return -3
        return 0

    if openGuildQuest()<0:
        return -1

    qn_help = 0
    qn_buy = 0
    xy = [200,440]

    if not maxQuest:
        maxQuest = 8
    for qn in range(maxQuest):
        #if qn_help>0 and qn_help<=4 and qn_buy==0:
        if qn_help>0 and qn_help<=4:
            xy[0] = 200+255*qn_help
            abMoveTo(xy)
            abClick()
            abSleep(0.8,err=0.3)

        im = fsScreenshot(region=(1400,200,520,880))
        left = 1400
        top = 200
        b = pyautogui.locate(TPL_DIR + 'btn_guild3_submit.png',im,confidence=0.9)
        if not b:
            logging.info(f'No submit button, finish: {qn}')
            break
        p_submit = (left+b[0]+b[2]//2, top+b[1]+b[3]//2)

        b = pyautogui.locate(TPL_DIR + 'btn_guild3_get.png',im,confidence=0.9)
        if b:
            # not enough
            p_get = (left+b[0]+b[2]//2, top+b[1]+b[3]//2)
            b = pyautogui.locate(TPL_DIR + 'btn_guild3_help0_3.png',im,confidence=0.8)
            logging.info(f'Help count({qn_help}): {b}')
            if qn_help<2 and b:
                p_help = (left+b[0]+b[2]//2, top+b[1]+b[3]//2)
                abMoveTo(p_help)
                abClick()
                logging.info(f'Guild quest ask for help({qn_help}): {qn}/{maxQuest}')
                abSleep(3)
                qn_help += 1
                continue
            else:
                abMoveTo(p_get)
                abClick()
                abSleep(0.5)
                clickIconCenter(['btn_guild3_buynow','btn_guild3_buynow_pc'],'Buy Now',0.4)
                clickIconCenter(['btn_guild3_buyok','btn_guild3_buyok_pc'],'Buy OK',0.6)
                clickIconCenter('btn_guild3_buyclose','Buy Close',0.4)
                qn_buy += 1

        abMoveTo(p_submit)
        abClick()
        logging.info(f'Guild quest submit: {qn}/{maxQuest}')
        abSleep(0.5)
        clickIconCenter('btn_guild3_takeoutok','Take Out',0.2)
        abSleep(0.5)
                
    clickIconCenter('ic_guild_close', 'Close Quild', 0.8, 0.95)
    clickIconCenter('ic_guild_close', 'Close Quild', 0.8, 0.95)
    return qn


def buySell(side,maxQuest,item='',pcVer=False):
    pcSfx = '_p' if pcVer else ''
    maxQuest = maxQuest if maxQuest else 34
    if side=='BUY':
        item = item if item else 'bluegem'
        img = 'ic_buy_'+item+pcSfx
    else:
        item = item if item else 'blue999'
        img = 'ic_sell_'+item+pcSfx

    if not os.path.exists(f'{TPL_DIR}{img}.png'):
        logging.info(f'{img} not found')
        return

    for i in range(0,maxQuest):
        if side=='BUY':
            if not clickIconInRegion(img, '{} {}'.format(item,i), 910, 0, 1880, 600, 0.3, 0.95):
                break
            if not clickIconInRegion(f'btn_trade_max{pcSfx}', 'max', 910, 0, 1880, 600, 0.1, 0.8):
                break
            if not clickIconInRegion(f'btn_trade_buy{pcSfx}', 'buy', 910, 0, 1880, 600, 0.5, 0.8):
                break
        elif side=='SELL':
            if not clickIconInRegion(img, 'sell {} {}'.format(item,i), 910, 0, 1880, 600, 0.3, 0.95):
                break
            if not clickIconInRegion(f'btn_trade_max{pcSfx}', 'max', 910, 0, 1880, 600, 0.1, 0.8):
                break
            if not clickIconInRegion(f'btn_trade_sell{pcSfx}', 'sell', 910, 0, 1880, 600, 0.5, 0.8):
                break

def dailyGift():
    done = False
    if waitScreen('ic_welfare', click=True, timeout=3, sleep=1, cf=0.9):
        if clickIconCenter('btn_signpage', 'Sign Page', 1.5, 0.95):
            if clickIconCenter('btn_signin', 'Sign In', 1.5, 0.9):
                done = True
            clickIconCenter('ic_wel_close', 'Q_Close', 1.5, 0.8)
    return done


def touchPet():
    done = False
    clickIconInRegion('ic_left_arrow2', 'Low Menu Switch', 1500, 340, 1900, 600, 1, 0.9)
    if clickIconInRegion('btn_pet', 'Pet Enter', 1280, 500, 1900, 900, 1, 0.9):
        if clickIconCenter('btn_pet_act', 'Pet Act', 1, 0.9):
            if clickIconCenter('btn_pet_pet', 'Pet Pet', 1, 0.9):
                done = True
            clickIconCenter('btn_pet_act_close', 'Pet Act Close', 1, 0.8)
        clickIconCenter('btn_pet_close', 'Pet Close', 1, 0.8)
    return done


def kvm():
    while True:
        clickIconCenter(['btn_kvm_ready1','btn_kvm_ready2'], 'KVM ready', cf=0.8)
        abSleep(3)

def ulimitPvP():
    def locateInPans(needle, hays):
        cand = {}
        for i,pan in enumerate(hays):
            im_pan, x0, y0 = pan
            b = pyautogui.locate(TPL_DIR + needle, im_pan, confidence=0.8)
            if b:
                p = (x0+b[0]+b[2]//2, y0+b[1]+b[3]//2)
                cand[i] = p
        return cand

    def checkBtn(btn):
        cand = locateInPans(f'btn_2x4_{btn}.png', pans)
        if len(cand)>0:
            for i,p in cand.items():
                logging.info(f'  {btn} ({i})!')
                abMoveTo(p)
                abClick()
                abSleep(0.1)
            return True
        return False

    while True:
        #im = fsScreenshot(region=(960,0,1880,500))
        im = fsScreenshot(region=(0,0,1920,570))
        pans = [
            (im.crop((0,0,920,570)), 0, 0),
            (im.crop((960,0,1920,570)), 960, 0)]

        #b = pyautogui.locate(TPL_DIR + 'btn_2x2_ready.png', im, confidence=0.8)
        if checkBtn('ready'):
            abSleep(2)
            continue

        #b = pyautogui.locate(TPL_DIR + 'btn_2x2_ban_m1.png', im, confidence=0.8)
        #b = pyautogui.locate(TPL_DIR + 'btn_2x4_ban_choose.png', im, confidence=0.8)
        if checkBtn('ban_choose'):
            abSleep(3)
            continue

        if checkBtn('mvp'):
            abSleep(2)
            continue

        if checkBtn('confirm'):
            abSleep(3)
            continue

        if checkBtn('cross'):
            abSleep(1)
            continue

        time.sleep(3)


def unlimitPvP(maxRound=0):

    def locateInPans(needle, hays):
        cand = []
        for pan in hays:
            im_pan, x0, y0 = pan
            b = pyautogui.locate(TPL_DIR + needle, im_pan, confidence=0.8)
            if b:
                p = (x0+b[0]+b[2]//2, y0+b[1]+b[3]//2)
                cand.append(p)
        return cand

    n_iter = 0
    n_round = 0
    is_vic = False
    while True:
        n_iter += 1
        im = fsScreenshot()
        pans = [
            (im.crop((0,0,920,500)), 0, 0),
            (im.crop((960,0,1880,500)), 960, 0),
            (im.crop((960,540,1880,1040)), 960, 540)]
        stat = []

        cand = locateInPans('btn_2x2_ready.png', pans)
        stat.append(len(cand))
        if len(cand)==3:
            logging.info('  Ready! {}'.format(n_round))
            for p in cand:
                p = (p[0]+3, p[1])
                #logging.info('Click at {}'.format(p))
                abMoveTo(p)
                abClick()
                abSleep(0.2)
            abSleep(2)
            continue
        cand_ready = cand

        cand = locateInPans('btn_2x2_ban_m1.png', pans)
        stat.append(len(cand))
        if len(cand)>=2:
            logging.info('  Pick ban list!')
            for p in cand:
                #logging.info('Click at {}'.format(p))
                abMoveTo(p)
                abClick()
                abSleep(0.2)
            abSleep(3)
            continue

        # confirm first as quit is still appear on screen in confirm screen
        cand = locateInPans('btn_2x2_confirm.png', pans[:2])
        stat.append(len(cand))
        if len(cand)==2:
            n_round += 1
            logging.info('  Confirm Quit! {}'.format(n_round))
            for p in cand:
                #logging.info('Click at {}'.format(p))
                abMoveTo(p)
                abClick()
                abSleep(0.2)
            #if maxRound and n_round >= maxRound:
            #    break
            abSleep(1)
            continue
        
        cand = locateInPans('btn_2x2_quit.png', pans[:2])
        stat.append(len(cand))
        if len(cand)==2:
            logging.info('  Quit!')
            for p in cand:
                #logging.info('Click at {}'.format(p))
                abMoveTo(p)
                abClick()
                abSleep(0.2)
            abSleep(0.3)
            continue

        # team leader
        if maxRound>0:
            cand = locateInPans('btn_2x2_team.png', pans[2:])
            if len(cand)>0:
                logging.info('  Open Team!')
                p = cand[0]
                #logging.info('Click at {}'.format(p))
                abMoveTo(p)
                abClick()
                abSleep(0.5)
                is_vic = False
                continue

            cand = locateInPans('btn_2x2_start.png', pans[2:])
            if len(cand)>0:
                logging.info('  Start!')
                p = cand[0]
                #logging.info('Click at {}'.format(p))
                abMoveTo(p)
                abClick()
                abSleep(0.5)
                is_vic = False
                continue

            cand = locateInPans('btn_2x2_anno.png', pans[2:])
            if len(cand)>0:
                logging.info('  Close Announcement!')
                p = cand[0]
                p = (p[0]+480, p[1]-14)
                #logging.info('Click at {}'.format(p))
                abMoveTo(p)
                abClick()
                abSleep(0.3)
                continue

            cand = locateInPans('btn_2x2_vic_ok.png', pans[2:])
            if len(cand)>0:
                logging.info('  Victory!')
                p = cand[0]
                #logging.info('Click at {}'.format(p))
                abMoveTo(p)
                abClick()
                abSleep(0.5)
                is_vic = True
                continue
            
            if is_vic:
                cand = locateInPans('btn_2x2_confirm.png', pans[2:])
                if len(cand)>0:
                    logging.info('  Confirm Quit (v)!')
                    p = cand[0]
                    #logging.info('Click at {}'.format(p))
                    abMoveTo(p)
                    abClick()
                    abSleep(0.2)
                    if n_round >= maxRound:
                        break
                    abSleep(3)
                    is_vic = False
                    continue
                
                cand = locateInPans('btn_2x2_quit.png', pans[2:])
                if len(cand)>0:
                    logging.info('  Quit! (v)')
                    p = cand[0]
                    #logging.info('Click at {}'.format(p))
                    abMoveTo(p)
                    abClick()
                    abSleep(0.5)
                    continue

        # remaining ready
        if len(cand_ready)>0:
            logging.info('  Ready (slow)!')
            for p in cand_ready:
                p = (p[0]+3, p[1])
                #logging.info('Click at {}'.format(p))
                abMoveTo(p)
                abClick()
                abSleep(0.2)

        logging.info('Iteration {} stat:{}'.format(n_iter, stat))
        time.sleep(3)


def unlimitPvP2024(maxRound=0, delayQuit=0):

    def locateInPans(needle, hays):
        cand = {}
        for i,pan in enumerate(hays):
            im_pan, x0, y0 = pan
            b = pyautogui.locate(TPL_DIR + needle, im_pan, confidence=0.8)
            if b:
                p = (x0+b[0]+b[2]//2, y0+b[1]+b[3]//2)
                cand[i] = p
        return cand

    def checkBtn(n_iter,st,btn):
        cand = locateInPans(f'btn_2x4_{btn}.png', pans)
        if len(cand)>0:
            for i,p in cand.items():
                logging.info(f'{n_iter}:  {btn} ({i})!')
                if 'quit' in btn and st[0]!='quitting' and delayQuit:
                    abSleep(delayQuit)
                    st[0] = 'quitting'
                abMoveTo(p)
                abClick()
                abSleep(0.1)
                if btn=='cross' and i==0:
                    st[0] = 'home'
            abSleep(1)
            return state
        return None

    n_iter = 0
    n_round = 0
    state = 'home'
    while True:
        n_iter += 1

        if state=='home':
            if clickIconInRegion('btn_2x4_carnival', 'Carnival', 500, 0, 920, 240, 2, 0.9):
                state='carnival'
                abSleep(1)
            else:
                if clickIconInRegion('btn_2x4_dot', 'Top Menu', 500, 0, 920, 240, 2, 0.9):
                    if clickIconInRegion('btn_2x4_carnival', 'Carnival', 500, 0, 920, 240, 2, 0.9):
                        state='carnival'
                        abSleep(1)

        im = fsScreenshot()
        pans = [
            (im.crop((0,0,920,570)), 0, 0),
            (im.crop((960,0,1920,570)), 960, 0),
            (im.crop((960,570,1920,1040)), 960, 570)]
        stat = []

        if state=='carnival':
            btn = 'c_unlimit'
        elif state=='c_unlimit':
            btn = 'unlimit'
        elif state=='unlimit':
            btn = 'freevs'
        elif state=='freevs':
            btn = 'start_match'
        else:
            btn = 'ready'
            
        if btn in ['carnival','c_unlimit','unlimit','freevs','start_match']:
            cand = locateInPans(f'btn_2x4_{btn}.png', [pans[0]])
            if len(cand)>0:
                logging.info(f'{n_iter}:  {btn}! Round:{n_round}')
                p = cand[0]
                abMoveTo(p)
                abClick()
                abSleep(1)
                state = btn
                continue
        else:
            st = [state]
            if checkBtn(n_iter,st,'ready') or \
                checkBtn(n_iter,st,'ban_choose') or \
                checkBtn(n_iter,st,'confirm') or \
                checkBtn(n_iter,st,'quit') or \
                checkBtn(n_iter,st,'quit2') or \
                checkBtn(n_iter,st,'cross'):
                state = st[0]
                if state=='home':
                    n_round += 1
                if maxRound and n_round >= maxRound:
                    break
                continue

        logging.info(f'{n_iter}: state:{state}')
        time.sleep(1)

def openDos():
    if not clickIconCenter('taskbar_dos', 'Taskbar DOS'):
        return -1



def runAllUsers(emuID, accID, charID, allQTimeout, skipOdin, autoSubmit, maxQuest):
    for i in range(0,3):
        if skipOdin:
            # try to logout if not already
            openStk()
            roxLogout()
        else:
            startNewRoxWithRetry(emuID)

        if accID and accID != '1':
            if roxSwitchAc(accID) == 0:
                # swithc ac success
                break
        else:
            break
        logging.info('Switch ac failed, retry {}'.format(i))
        if i==2:
            pyautogui.screenshot('log/switchac_{}.jpg'.format(datetime.now().strftime('%Y%m%d%H%M%S')))
    
    chars = charID.split(',')
    for i,c in enumerate(chars):
        # an empty string will split to single empty string
        onlyOdin=False
        doGuildQuest=False
        doCommQuest=False
        if len(c)>0 and '@' in c:
            onlyOdin=True
            c = c.replace('@','')
        if len(c)>0 and '#' in c:
            doGuildQuest=True
            c = c.replace('#','')
        if len(c)>0 and '$' in c:
            doCommQuest=True
            c = c.replace('$','')
            #logging.info(f'Enable comm quest for acc {accID} char {c}.')
        try:
            roxLogin(c)
        except Exception as e:
            logging.error(e)
            pyautogui.screenshot('log/no_login_{}.jpg'.format(datetime.now().strftime('%Y%m%d%H%M%S')))
            continue

        try:
            if onlyOdin:
                returnHomeCityByMap()
                waitOdin()
            else:
                tag = f'{accID}-{c}'
                runAllDaily(allQTimeout, skipOdin, autoSubmit, maxQuest, doGuildQuest, doCommQuest, tag=tag)
        except Exception as e:
            logging.error(e)

        if i==len(chars)-1:
            returnHomeCityByMap()
        else:
            if roxLogout()<0:
                startNewRoxWithRetry(emuID)


def runAllDaily(allQTimeout, skipOdin, autoSubmit, maxQuest, doGuildQuest, doCommQuest, tag=''):
    if skipOdin:
        r2 = takeQuest(maxQuest=maxQuest)
        logging.info('runAllDaily({}) takeQuest:{}'.format(tag, r2))
        r3 = dailyGift()
        r4 = touchPet()
        r5 = -1
        if doGuildQuest:
            r5 = guildQuest()
        r6 = -1
        if doCommQuest:
            r6 = commQuest()
    else:
        r1 = returnHomeCityByMap()
        if r1<0:
            r1 = returnHomeCity()
        r2 = takeQuest(maxQuest=maxQuest)
        r3 = r4 = r5 = r6 = -1
        logging.info('runAllDaily({}) returnHomeCity:{} takeQuest:{}'.format(tag, r1, r2))
        if r1<0 or r2<0:
            pyautogui.screenshot('log/no_daily_{}.jpg'.format(datetime.now().strftime('%Y%m%d%H%M%S')))
        if r1>=0:
            now = datetime.now()
            r3 = dailyGift()
            r4 = touchPet()
            if doGuildQuest:
                r5 = guildQuest()
            if doCommQuest:
                r6 = commQuest()
            if r1==0:
                returnCityCenter()
                waitOdin(now)
    
    r7 = runAllQuests(allQTimeout)
    if autoSubmit:
        takeQuest(True, maxQuest)
    logging.info('runAllDaily({}) gift:{} pet:{} guild:{} comm:{} quest:{}'.format(tag, r3, r4, r5, r6, r7))

def test():
##    abMoveTo(10,10)
##    tpl0 = cv2.imread(TPL_DIR + 'tpl_daily.png',0)
##    print(tpl0.max())
##    tpl1 = cv2.imread('log/qtitle_202208100137_0.jpg',0)
##    #pure black image always result in 1.0 match 
##    tpl1 = cv2.imread('log/qtitle_20220810235329.jpg',0)
##    print(tpl1.max())
##    tpl2 = cv2.imread('log/qtitle_202208100137_1.jpg',0)
##    res = matchTpl(tpl0,tpl1)
##    print(res.max())
##    loc = np.where(res >= 0.7)
##    print('matched' if loc[0].size>0 else 'not match')
##    res = matchTpl(tpl2,tpl1)
##    loc = np.where(res >= 0.7)
##    print(res.max())
##    print('matched' if loc[0].size>0 else 'not match')
##    for n in range(1,30):
##        f = 'screencap/ro_run_quest{}.png'.format(n)
##        if not os.path.exists(f):
##            continue
##        sam1 = cv2.imread(f,1)
##        him = cv2.cvtColor(np.array(sam1), cv2.COLOR_BGR2HSV)
##        ir = cv2.inRange(him, (0//2,0,210), (360//2,18,255))
##        ir2 = cv2.inRange(him, (11//2,120,180), (22//2,200,240))
##        im_quest_title = (ir+ir2)[:, 24:184]
##
##        cv2.imwrite('screencap/qtitle_{}.jpg'.format(n),im_quest_title)

##    tpl_skip = cv2.imread(TPL_DIR + 'tpl_skip.png',0)    
##    for n in range(1,11):
##        sam1 = cv2.imread('screencap/ro_skip{}.png'.format(n),1)
##        sam1 = sam1[40:120,1560:1800]
##        sam1 = cv2.cvtColor(sam1, cv2.COLOR_BGR2HSV)
##        ir = cv2.inRange(sam1, (0//2,0,200), (360//2,27,255))
##        res = matchTpl(ir,tpl_skip)
##        cv2.imwrite('screencap/tpl_skip{}.png'.format(n), ir)
##        print('   Test ptn {} result:{}'.format(n, res.max()))
##        
##    tpl_hand = cv2.imread(TPL_DIR + 'tpl_hand.png',0)
##    for n in range(1,12):
##        sam1 = cv2.imread('screencap/ro_hand{}.png'.format(n))
##        sam1 = sam1[330:480,1180:1330]
##        sam1 = cv2.cvtColor(sam1, cv2.COLOR_BGR2HSV)
##        #varadj = max(int(sam1[:,:,2].mean()/5)-33,0)
##        #satadj = max(int(sam1[:,:,1].mean()/8)-7,0)
##        #print('{}:{},{}'.format(n,satadj,varadj))
##        #ir = cv2.inRange(sam1, (28//2,130+satadj,170), (50//2,160+satadj,223+varadj))
##        #ir = cv2.inRange(sam1, (28//2,130+satadj,170), (50//2,160+satadj,233))
##        ir = cv2.inRange(sam1, (0,0,235), (180,30,255))
##        res = matchTpl(ir,tpl_hand)
##        print('{}:{}'.format(n,res.max()))
##        #cv2.imwrite('screencap/tpl_hand_w{}.png'.format(n), ir)
##    sam1 = cv2.imread('screencap/minigame/bar-ready.png')
##    sam1 = sam1[300:390,640:730]
##    sam1 = cv2.cvtColor(sam1, cv2.COLOR_BGR2HSV)
##    ir = cv2.inRange(sam1, (0,0,235), (180,30,255))
##    cv2.imwrite('screencap/tpl_minigame.png', ir)

##    sam1 = cv2.imread('screencap/ro_submit_quest3.png')
##    sam1 = sam1[300:800,1400:1800]
##    sam1 = cv2.cvtColor(sam1, cv2.COLOR_BGR2HSV)
##    ir = cv2.inRange(sam1, (75//2,50,230), (90//2,100,255))
##    byrow = cv2.reduce(ir, 1, cv2.REDUCE_SUM, dtype=cv2.CV_32SC1).T[0]
##    y = byrow.argmax()
##    y1 = np.where(byrow[:y]<300)[0][-1]
##    y2 = np.where(byrow[y:]<300)[0][0]+y
##    ymid = y1+(y2-y1)//2
##    print("max:{} at {}, block:{}-{}, mid:{}".format(byrow.max()/255,y,y1,y2,ymid))
##    ir = cv2.inRange(sam1, (75//2,30,220), (90//2,100,255))
##    ir[ymid-16:ymid+16,50:350] = 255
##    cv2.imwrite('screencap/tpl_submit_quest3.png', ir)
        
##    if not waitWhiteScreen():
##        print('White screen not found')
##    logging.info("test logger")

##    #lang = pytesseract.get_languages(config='')
##    #print(lang)
##    im = cv2.imread('log/qtitle_20220816142246.jpg', 0)
##    #print(im)
##    #pim = cv2.cvtColor(im, cv2.COLOR_GRAY2RGB)
##    #ocr = pytesseract.image_to_data(im, lang='chi_tra')
##    ocr = pytesseract.image_to_string(255-im, lang='chi_tra')
##    logging.info("OCR result: {}".format(re.sub("\s"," ",ocr)))
##    #s = u'中文'
##    #s = "here is your checkmark: " + u'\u2713'
##    #logging.info(s)

##    #im = []
##    #im = cv2.imread('screencap/ro_autofight.png')
##    #im = cv2.imread('screencap/ro_picking.png')
##    #im = cv2.imread('screencap/ro_heaven.png')
##    tpl_af_on = cv2.imread(TPL_DIR + 'tpl_auto_on.png',0)
##    tpl_af_off = cv2.imread(TPL_DIR + 'tpl_auto_off.png',0)
##    #for i in range(1,7):
##        #im = cv2.imread('screencap/ro_hand{}.png'.format(i))
##        #im_auto = im[730:860,1130:1260]
##        #him = cv2.cvtColor(im_auto, cv2.COLOR_BGR2HSV)
##
##        #print('image {} result afon:{} afoff:{}'.format(i,res.max(),res2.max()))
##    time.sleep(1)
##    im_auto = np.array(fsScreenshot(region=(1130,730,130,130)))
##    him = cv2.cvtColor(im_auto, cv2.COLOR_RGB2HSV)
##    ir = cv2.inRange(him, (0,0,235), (180,45,255))
##    res = matchTpl(ir,tpl_af_on)
##    res2 = matchTpl(ir,tpl_af_off)
##    cv2.imwrite('log/tpl_auto_off_test.png',ir)
##    print('image result afon:{} afoff:{}'.format(res.max(),res2.max()))

##    abMoveTo(345,800)
##    pyautogui.mouseDown()
##    time.sleep(0.05)
##    abMoveTo(345,650,0.6,True)
##    time.sleep(0.8)
##    pyautogui.mouseUp()
##    im = cv2.imread('screencap/ro_questboard_sp.png')
##    him = cv2.cvtColor(im, cv2.COLOR_RGB2HSV)
##    ir = cv2.inRange(him, (0//2,0,200), (360//2,27,255))
##    cv2.imwrite('screencap/tpl_questboard_sp.jpg',ir)

##    im = cv2.imread('ic_lock_small.png')
##    him = cv2.cvtColor(im, cv2.COLOR_RGB2HSV)
##    ir = cv2.inRange(him, (240//2,0,50), (330//2,30,170))
##    cv2.imwrite('ic_lock_smbw.png',ir)

##    for i in range(3,6):
##        im = cv2.imread('screencap/ro_pick_math{}.png'.format(i))
##        #im_challenge = im[420:500,760:1130]
##        #him = cv2.cvtColor(im_challenge, cv2.COLOR_BGR2HSV)
##        #ir = cv2.inRange(him, (0,0,150), (180,255,255))
##        #cv2.imwrite('screencap/tpl_challenge.png',ir)
##        #ocr = pytesseract.image_to_string(ir, lang='chi_tra', config=r'--psm 6')
##        #logging.info("OCR: {}".format(re.sub("\s","",ocr)))
##        im_math = im[500:550,890:1000]
##        him = cv2.cvtColor(im_math, cv2.COLOR_BGR2HSV)
##        #ir = cv2.inRange(him, (0,0,246), (0,2,255))
##        ir = cv2.inRange(him, (0,0,200), (0,5,255))
##        #ir = cv2.resize(ir, (88,40), interpolation = cv2.INTER_LINEAR)
##        #ir = cv2.resize(ir, (121,55), interpolation = cv2.INTER_AREA)
##        cv2.imwrite('screencap/tpl_math.jpg',255-ir)
##        #ocr_config = ''
##        #ocr_config = r'-c tessedit_char_whitelist=0123456789+-*/'
##        ocr_config = r'--psm 6 -c tessedit_char_whitelist=0123456789+-*/'
##        ocr = pytesseract.image_to_string(ir, lang='eng', config=ocr_config).strip()
##        logging.info("Math: {}".format(ocr))
##    im_text = cv2.imread('screencap/quest_new_{}.png'.format(1))
##    him = cv2.cvtColor(np.array(im_text), cv2.COLOR_BGR2HSV)
##    ir = cv2.inRange(him, (0//2,125,230), (0//2,135,255))
##    cv2.imwrite('screencap/quest_new_{}_ix.jpg'.format(1),ir)
##    ocr_config = r'--psm 6 -c tessedit_char_whitelist=0123456789'
##    ocr = pytesseract.image_to_string(ir, lang='eng', config=r'--psm 6').strip()
##    logging.info("OCR: {}".format(ocr))

##    nonMax=True
##    im = cv2.imread('screencap/ro_hand_small.png') 
##    im_act_btn = imcrop(im,370,480,1100,1220,nonMax)
##    im_act_btn = cv2.cvtColor(im_act_btn, cv2.COLOR_BGR2HSV)
##    ir_act_btn = cv2.inRange(im_act_btn, (0,0,235), (180,30,255))
##    cv2.imwrite('screencap/tpl_hand_small.png',ir_act_btn)
##    im = cv2.imread('screencap/ro_picking_small.png') 
##    im_picktxt = imcrop(im,650,720,900,1000,nonMax)
##    im_picktxt = cv2.cvtColor(im_picktxt, cv2.COLOR_BGR2HSV)
##    ir_picktxt = cv2.inRange(im_picktxt, (0//2,0,210), (360//2,18,255))
##    cv2.imwrite('screencap/tpl_picking_small.png',ir_picktxt)
##    im = cv2.imread('screencap/ro_math_small.png') 
##    im_challenge = imcrop(im,420,500,760,1130,nonMax)
##    im_challenge = cv2.cvtColor(im_challenge, cv2.COLOR_BGR2HSV)
##    ir_challenge = cv2.inRange(im_challenge, (0,0,150), (180,255,255))
##    cv2.imwrite('screencap/tpl_challenge_small.png',ir_challenge)
##    tpl_chal = cv2.imread(TPL_DIR + 'tpl_challenge_small.png',0)
##    im = np.array(fsScreenshot())
##    im_challenge = imcrop(im,390,530,730,1160,nonMax)
##    him = cv2.cvtColor(im_challenge, cv2.COLOR_RGB2HSV)
##    ir = cv2.inRange(him, (0,0,150), (180,255,255))
##    res = matchTpl(ir,tpl_chal)
##    loc = np.where(res >= 0.9)
##    logging.info('   Test pattern challenge:{}'.format(res.max()))
##    cv2.imwrite('screencap/test_challenge_small.png',im_challenge)

##    for f in glob('log/switchac_20*.jpg'):
##        im = cv2.imread(f)
##        im_pil = Image.fromarray(cv2.cvtColor(im, cv2.COLOR_BGR2RGB))
##        b = pyautogui.locate('ic_switch_ac.png',im, confidence=0.85)
##        #if b and b[0]==1741:
##        if b and b[0]==1744:
##            logging.info(' {}: OK'.format(f))
##        else:
##            logging.info(' {}: Failed, {}'.format(f,b))
##        tpl = cv2.imread('ic_switch_ac.png')
##        res = matchTpl(im,tpl)
##        logging.info('   Test pattern Switch AC:{:.2f}'.format(res.max()))
##    pyautogui.screenshot('screencap/test_linecrowded.png')

##    clickIconCenter(['ic_q_close', 'ic_q_close_sp'], 'Q_Close', 2, 0.92)

##    logging.error('Test error log')
##    if not waitScreen(['ic_carnival', 'ic_carnival_dot'], click=True, timeout=2, cf=0.9):
##        logging.info('Carnival failed 1')
##        if clickIconInRegion('ic_top_menu', 'Top Menu', 1000, 35, 1560, 480, 2, 0.9):
##            logging.info('Top menu clicked')
##            if not clickIconInRegion(['ic_carnival', 'ic_carnival_dot'], 'Carnival', 
##                    1000, 35, 1560, 480, 2, 0.9):
##                logging.error('Carnival button not found on Top Menu')
##        else:
##            logging.info('Top menu failed')

##    im = fsScreenshot(region=(0,0,1000,600))
##    im_icons = im.crop((530,30,850,260))
##    #im1 = cv2.cvtColor(np.array(im_icons), cv2.COLOR_RGB2BGR)
##    #cv2.imwrite('log/fix/im_icons.png',im1)
##    b = pyautogui.locate('ic_carnival_small.png', im_icons, confidence=0.85)
##    if b:
##        p = (530+b[0]+b[2]//2, 30+b[1]+b[3]//2)
##        logging.info('   click carnival at: {}'.format(p))
##        abClick(p)
##        abSleep(2)
##        clickIconInRegion('ic_armw_carnival', 'Armw', 0, 0, 1000, 600, 1, 0.8)
##        clickIconInRegion('ic_armw_move', 'Move', 0, 0, 1000, 600, 4, 0.8)

##    im = np.array(fsScreenshot())
##    im = cv2.imread('screencap/ro_questdone.png')
##    him = cv2.cvtColor(im, cv2.COLOR_BGR2HSV)
##    ir = cv2.inRange(him, (0//2,0,210), (360//2,18,255))
##    cv2.imwrite('log/fix/tpl_questdone.png',ir)
##    im = np.array(fsScreenshot())
##    im_prompt = im[780:850, 880:1060]
##    him = cv2.cvtColor(im_prompt, cv2.COLOR_RGB2HSV)
##    ir = cv2.inRange(him, (0//2,0,210), (360//2,18,255))
##    cv2.imwrite('log/fix/tpl_submitprompt.png',ir)

##    tpl_close_sim = cv2.imread(TPL_DIR + 'tpl_close_simple.png',0)
##    im = cv2.imread('screencap/ro_qfly.png')
##    im_fly = im[330:440, 1300:1420]   # close only
##    im_fly = im[330:530, 1200:1420]
##    him = cv2.cvtColor(im_fly, cv2.COLOR_BGR2HSV)
##    ir = cv2.inRange(him, (0//2,0,200), (360//2,27,255))
##    cv2.imwrite('log/fix/tpl_qfly_close.png',ir)
##    res = matchTpl(ir,tpl_close_sim)
##    loc = np.where(res >= 0.95)
##    logging.info('   Test pattern QB close:{}'.format(res.max()))

##    im = np.array(fsScreenshot())
##    im_aim = im[920:1020,1500:1600]
##    ir_aim = cv2.inRange(cv2.cvtColor(im_aim, cv2.COLOR_RGB2HSV), (0,0,210), (180,55,255))
##    cv2.imwrite('log/fix/tpl_aim.png',ir_aim)
##    im = fsScreenshot(region=(120,300,310,350))
##    him = cv2.cvtColor(np.array(im), cv2.COLOR_RGB2HSV)
##    ir = cv2.inRange(him, (0//2,0,210), (360//2,18,255))
##    cv2.imwrite('log/fix/tpl_commerce.png',ir)

##    im = Image.open('screencap/armw-quit.png')
##    im_win_buttons = im.crop((270,470,740,540))
##
##    for qimg in ('','2','3'):
##        b = pyautogui.locate('btn_armw_quit{}.png'.format(qimg), im_win_buttons, confidence=0.65)
##        if b:
##            logging.info('  Quit! '+qimg)
##    #tpl_qsubmit = cv2.imread(TPL_DIR + 'tpl_qsubmit.png',0)
##    tpl_qdone = cv2.imread(TPL_DIR + 'tpl_questdone.png',0)
##    tpl_qdone2 = cv2.imread(TPL_DIR + 'tpl_questdone2.png',0)
##    for f in ('1','2','3'):
##        im_prompt = cv2.imread('screencap/submit-fail-{}.png'.format(f))
##        him = cv2.cvtColor(im_prompt, cv2.COLOR_BGR2HSV)
##        ir = cv2.inRange(him, (0//2,0,210), (360//2,18,255))
##        cv2.imwrite('screencap/tpl_submit_fail-{}.png'.format(f),ir)
##        res = matchTpl(ir,tpl_qdone)
##        loc = np.where(res >= CONF_TEXT)
##        logging.info('   Test pattern quest_done:{}'.format(res.max()))
##        res = matchTpl(ir,tpl_qdone2)
##        loc = np.where(res >= CONF_TEXT)
##        logging.info('   Test pattern quest_don2:{}'.format(res.max()))
##    im = Image.open('screencap/ro_quest_goto_board.png')
##    b = pyautogui.locate('ic_go_now2.png',im, confidence=0.92)
##    if b:
##        logging.info('   locate ic_go_now success at {}'.format(b))
##    tpl_hand2 = cv2.imread(TPL_DIR + 'tpl_hand2.png',0)
##    for f in ('1','2','3'):
##        im = cv2.imread('screencap/quest_search{}.png'.format(f))
##        im_act_btn = im[330:480,1180:1330]
##        him = cv2.cvtColor(im_act_btn, cv2.COLOR_BGR2HSV)
##        ir = cv2.inRange(him, (0,0,235), (180,30,255))
##        #cv2.imwrite('screencap/tpl_hand_search.png',ir)
##        res = matchTpl(ir,tpl_hand2)
##        print(res.max())

##    im = cv2.imread('screencap/quest_puzzle.png')
##    im_fly = im[330:530, 1200:1420]
##    him = cv2.cvtColor(im_fly, cv2.COLOR_BGR2HSV)
##    ir = cv2.inRange(him, (0//2,0,200), (360//2,27,255))
##    cv2.imwrite('screencap/tpl_puzzle.png',ir)
##    #im = cv2.imread('screencap/quest_photo.png')
##    #im_fly = im[330:530, 1200:1420]
##    #him = cv2.cvtColor(im_fly, cv2.COLOR_BGR2HSV)
##    #im = cv2.imread('screencap/quest_photo.png')
##    #im_botright = im[860:980, 1400:1700]
##    #him = cv2.cvtColor(im_botright, cv2.COLOR_RGB2GRAY)
##    #ir = cv2.inRange(him, (0//2,0,200), (360//2,27,255))
##    #cv2.imwrite('screencap/tpl_photo.png',ir)
##
##    im = cv2.imread('screencap/quest_photo2.png')
##    im_botright = im[860:980, 1400:1700]
##    cv2.imwrite('screencap/tpl_shutter.png',im_botright)

##    im = fsScreenshot(region=(1240,292,70,24))
##    him = cv2.cvtColor(np.array(im), cv2.COLOR_RGB2HSV)
##    ir = cv2.inRange(him, (0//2,0,210), (360//2,18,255))
##    ocr_config = r'--psm 6 -c tessedit_char_whitelist=0123456789/'
##    ocr = pytesseract.image_to_string(ir, lang='eng', config=ocr_config).strip()
##    logging.info(" OCR result: {}".format(re.sub("\s"," ",ocr)))
##    cv2.imwrite('screencap/comm_item_cnt.png',ir)
##    #im = cv2.imread('screencap/comm_item_cnt.png')
##    for f in glob('screencap/comm_item_*.png'):
##        if '_bw' in f:
##            continue
##        im = cv2.imread(f)
##        him = cv2.cvtColor(im, cv2.COLOR_RGB2HSV)
##        #ir = 255-cv2.inRange(him, (0//2,0,180), (360//2,20,255))
##        ir = cv2.inRange(him, (0//2,0,190), (360//2,25,255))
##        ocr_config = r'--psm 6 -c tessedit_char_whitelist=0123456789/'
##        ocr = pytesseract.image_to_string(ir, lang='eng', config=ocr_config).strip()
##        logging.info(" {} OCR result: {}".format(f,re.sub("\s"," ",ocr)))
##        outf = f.replace('.png','_bw.png')
##        cv2.imwrite(outf,ir)
##    abClick(200,200)
##    abClick(202,202)
##    abClick(204,204)
##    abClick(206,206)
##    time.sleep(1)
##    print('Check for mouse free')
##    waitMouseFree(cf=3)
##    print('Free now')
##    if waitScreenRegion('btn_start_1', 800, 860, 1100, 1000, click=True, sleep=3, timeout=10, cf=0.6):
##    ##if waitScreen('btn_start_1', click=False, sleep=3, timeout=10, cf=0.6):
##        print('OK')
##    im = np.array(pyautogui.screenshot(region=[1524-12,710-10,24,20]))
##    cid = 710-10
##    for col in im:
##        rid = 1524-12
##        for row in col:
##            r,g,b = row
##            if r>=249 and g>=233:
##                print(f'{rid},{cid}:{r},{g},{b}')
##            rid += 1
##        cid += 1
##    #im = np.array(fsScreenshot())
##    #im_act_btn = im[330:480,1180:1330]
##    #him = cv2.cvtColor(im_act_btn, cv2.COLOR_RGB2HSV)
##    #ir = cv2.inRange(him, (0,0,235), (180,30,255))
##    #cv2.imwrite('screencap/tpl_hear1.png',ir)
##    #im_fly = im[330:530, 1200:1420]
##    #him = cv2.cvtColor(im_fly, cv2.COLOR_RGB2HSV)
##    #ir = cv2.inRange(him, (0//2,0,200), (360//2,27,255))
##    #cv2.imwrite('screencap/tpl_hear2.png',ir)
##
##    #tpl_minigame = cv2.imread(TPL_DIR + 'tpl_minigame.png',0)
##    #im = fsScreenshot(region=(0,0,1000,600))
##    #im_gameicon = im.crop((630,290,740,400))
##    ##im1 = cv2.cvtColor(cim[290:400,630:740], cv2.COLOR_BGR2HSV)
##    #im1 = cv2.cvtColor(np.array(im_gameicon), cv2.COLOR_BGR2HSV)
##    #ir = cv2.inRange(im1, (0,0,235), (180,30,255))
##    #res = matchTpl(ir,tpl_minigame)
##    #logging.info('   Test pattern minigame:{}'.format(res.max()))
##    print(waitScreen('btn_comm_close', click=False, timeout=1, cf=0.98))
##    print(waitScreen('btn_welcome_close', click=False, timeout=1, cf=0.98))
##    #print(waitScreen('btn_guild3_close', click=False, timeout=1, cf=0.95))
##    #print(waitScreen('btn_pet_close', click=False, timeout=1, cf=0.95))
##    print(waitScreen('btn_get_odin', click=False, timeout=1, cf=0.95))
##    im = np.array(fsScreenshot())
##    im_picktxt = imcrop(im,650,720,900,1000,True)
##    him = cv2.cvtColor(im_picktxt, cv2.COLOR_RGB2HSV)
##    ir = cv2.inRange(him, (0//2,0,210), (360//2,18,255))
##    cv2.imwrite('screencap/tpl_picking_small_pc.png',ir)
##    im_challenge = imcrop(im,390,530,730,1160,True)
##    him = cv2.cvtColor(im_challenge, cv2.COLOR_RGB2HSV)
##    ir = cv2.inRange(him, (0,0,150), (180,255,255))
##    cv2.imwrite('screencap/tpl_challenge_small_pc.png',ir)
##    im = fsScreenshot(region=(120,300,310,350))
##    him = cv2.cvtColor(np.array(im), cv2.COLOR_RGB2HSV)
##    #ir = cv2.inRange(him, (280//2,100,200), (296//2,160,255)) #purple
##    ir = cv2.inRange(him, (0//2,0,210), (360//2,18,255))
##    cv2.imwrite('screencap/tpl_quest_whitetext.png',ir)
##    im = cv2.imread('screencap/farm-char-pc2.png')
##    im_challenge = imcrop(im,390,530,730,1160,True)
##    him = cv2.cvtColor(im_challenge, cv2.COLOR_RGB2HSV)
##    ir = cv2.inRange(him, (0,0,150), (180,255,255))
##    tpl_chal = cv2.imread(TPL_DIR + 'tpl_challenge_small_pc2.png',0)
##    print(matchTpl(ir,tpl_chal).max())
##    cv2.imwrite('screencap/tpl_challenge_small_pc3.png',ir)

    im = fsScreenshot(region=(0,0,1000,600))
    im_gameicon = im.crop((630,290,780,400))
    #im1 = cv2.cvtColor(cim[290:400,630:740], cv2.COLOR_BGR2HSV)
    im1 = cv2.cvtColor(np.array(im_gameicon), cv2.COLOR_BGR2HSV)
    ir = cv2.inRange(im1, (0,0,235), (180,30,255))
    cv2.imwrite('screencap/tpl_minigame2.png',ir)

##    pyautogui.moveTo(800,600)
##    pyautogui.mouseDown()
##    time.sleep(0.09)
##    pyautogui.mouseUp()
    ## TESTHERE ##

    pass

def testMath(errorOnly=False,filedate=None):
    tpl_x1   = cv2.imread(TPL_DIR + 'tpl_math_x1_small.png',0)
    if filedate:
        gstr = f'log/math_{filedate}*.jpg'
    else:
        gstr = 'log/math_20*.jpg'

    from glob import glob
    for f in glob(gstr):
        m = re.search('_(\d+)\.jpg',f)
        if m:
            filetag = m.group(1)
        else:
            continue
        if errorOnly and not os.path.exists('log/math_err_{}.jpg'.format(filetag)):
            continue
        im_math = cv2.imread(f,1)
        nonMax = True if im_math.shape[0] < 37 else False
        if nonMax:
            tpl_prefix = cv2.imread(TPL_DIR + 'tpl_2_small.png',0)
        else:
            tpl_prefix = cv2.imread(TPL_DIR + 'tpl_8.png',0)
        him = cv2.cvtColor(im_math, cv2.COLOR_BGR2HSV)
        ir = 255-cv2.inRange(him, (0,0,245), (255,5,255))
        h, w = tpl_prefix.shape
        ir[:h,:w] = tpl_prefix
        #ir[:h,ir.shape[1]-w:] = 255-tpl_prefix
        ocr = pytesseract.image_to_string(ir, lang='eng', 
                config=r'--psm 6 -c tessedit_char_whitelist=0123456789+-x*').strip()
        ans = None
        rmx_x1 = -1
        if nonMax is not None:
            rmx_x1 = matchTpl(ir,tpl_x1).max()
            logging.info('  x1: {} raw:{}'.format(rmx_x1,ocr))
            if rmx_x1>0.82:
                m = re.match('[82](10|\d)',ocr)
                if m:
                    ans = x = int(m.group(1))
                    y = 1
                    op = '@'
        if not ans:
            m = re.match('[82](10|\d)([\+\-\*\/4]){0,2}(\d)$',ocr)
            if m:
                x = int(m.group(1))
                y = int(m.group(3))
                if m.group(2) in ('+','4','4+','+4'):
                    op = '+'
                    ans = x + y
                elif m.group(2) == '-':
                    op = '-'
                    ans = x - y
                else:
                    op = '*'
                    ans = x * y
        if ans:
            logging.info("File {} Math Parse  OK  : {:5} => {}{}{}={}".format(f,ocr,x,op,y,ans))
        else:
            logging.info("File {} Math Parse Error: {:5} {}".format(f,ocr,rmx_x1))
            cv2.imwrite('log/fix/math_err_{}.png'.format(filetag),ir)

def usageAndExit():
    '''
    Usage: python autoxor.py [commands...] -h [-i <instance_number>]
        -e      Instance number passed to emulator, eg: 1 as Nougat_1
                If not specified, no parameter is pass to emulator
        -a      Account Index, default 1 as first ac in list and so on
                First letter 'g' as google, 'f' as facebook.
        -c      Character Index, with nametag#.png file
                Multiple characters eg: 1,2,3 can be passed to runUsers
        -t      Timeout (minutes) for running all quests
                Default 0 for no timeout
        -l      Write to log file name, null to cancel
                Default log/rox_YMD.log
        -f      For runAll/runUsers, do not wait for odin
                and do not restart emulator/game at first run
        -s      For runAll/runUsers, submit all quests when finished
        -m      Max number of quest to take/submit
        -q      Screen capture before start
        -n      For runquest, do not scroll to top of quest list
                For armwrest, do not save name of guest as image
                For farm/fish, do not maximize screen
        -w      Window title for emulator for restarting
                Only support string starts with XOR
        -h      This help message

        commands (case in-sensitive):
            startStk    start emulator only
            startRox    start emulator and XOR with retry
            login       login XOR
            home        return to home city
            takeQuest   take all quests
            waitOdin    wait for odin, typical 30 min
            runQuest    daily questboard quests
            guildQuest  guild purchase orders

            runAll      include: home, takequest, waitodin, runquest
            runUsers    all of the above, for all characters 

            submitQ     submit qll quests
            logout      logout XOR
            switchAc    login using Account Index, default 1
'''

    print(usageAndExit.__doc__)
    sys.exit()

if __name__ == '__main__':

    emuID = ''
    accID = ''
    charID = ''
    allQTimeout = 0
    maxQuest = 0
    useLF = ''
    winTitle = ''
    skipOdin = False
    autoSubmit = False
    noFromTop = False
    captureStart = False
    pcVer = False
    numRetry = XOR_START_RETRY 
    opts, args = getopt.getopt(sys.argv[1:], 'a:c:e:l:m:t:w:z:fnpqsh')
    for o,a in opts:
        if o == '-e':
            emuID = a
        elif o == '-a':
            accID = a
        elif o == '-c':
            charID = a
        elif o == '-l':
            useLF = a
        elif o == '-w':
            winTitle = a
        elif o == '-t':
            allQTimeout = int(a)
        elif o == '-f':
            skipOdin = True
        elif o == '-s':
            autoSubmit = True
        elif o == '-m':
            maxQuest = int(a)
        elif o == '-n':
            noFromTop = True
        elif o == '-p':
            pcVer = True
        elif o == '-q':
            captureStart = True
        elif o == '-z':
            CONF_TEXT = float(a)
        else:
            usageAndExit()

    args = [x.lower() for x in args]

    if not args:
        usageAndExit()

    if 'sendlog' in args:
        sendLog(useLF)
        sys.exit()

    setupLogger(useLF)

    if captureStart:
        abMoveTo(0,0)
        abSleep(3)
        abMoveTo(10,10)
        abSleep(3)
        openStk(True) # not maximize
        pyautogui.screenshot('log/daystart_{}.jpg'.format(datetime.now().strftime('%Y%m%d%H%M%S')))
        
    if 'runusers' in args:
        killRox()
        runAllUsers(emuID, accID, charID, allQTimeout, skipOdin, autoSubmit, maxQuest)
        openDos()
        sys.exit()
    elif 'runall' in args:
        openStk()
        runAllDaily(allQTimeout, skipOdin, autoSubmit, maxQuest, False, False)
        openDos()
        sys.exit()
    elif 'testmath' in args:
        testMath(noFromTop,allQTimeout)
        sys.exit()
    elif 'scroll' in args:
        scrollMsg(maxQuest)
        sys.exit()
    elif 'test' in args:
        test()
        openDos()
        sys.exit()

    if 'startrox' in args:
        startNewRoxWithRetry(emuID,numRetry,winTitle,noFromTop)
    elif 'startstk' in args:
        startStk()
    elif not [i for i in args if i in ['armw','unlimit','ulimit','kvm','buy','sell','farm','fish']]:
        # the commands which support non-maximize window
        openStk()
        
    if 'switchac' in args:
        roxSwitchAc(accID)

    if 'login' in args:
        roxLogin(charID)

    if 'home' in args:
        returnHomeCity()
   
    if 'takequest' in args:
        takeQuest(maxQuest=maxQuest)
    
    if 'waitodin' in args:
        waitOdin()
    
    if 'runquest' in args:
        runAllQuests(allQTimeout,noFromTop,maxQuest,pcVer)

    if 'submitq' in args:
        takeQuest(True, maxQuest)

    if 'guildquest' in args:
        guildQuest()
    
    if 'commquest' in args:
        commQuest(maxQuest,noFromTop)
    
    if 'farm' in args:
        farming(noFromTop,pcVer)

    if 'fish' in args:
        fishing(maxQuest,noFromTop,pcVer,allQTimeout)

    if 'armw' in args:
        armwrestling(noSaveName=noFromTop, gotoSeat=autoSubmit)

    if 'unlimit' in args:
        unlimitPvP2024(maxQuest,allQTimeout)

    if 'ulimit' in args:
        ulimitPvP()

    if 'kvm' in args:
        kvm()

    if 'buy' in args:
        buySell('BUY', maxQuest, accID, pcVer=pcVer)

    if 'sell' in args:
        buySell('SELL', maxQuest, accID, pcVer=pcVer)

    if 'dailygift' in args:
        dailyGift()

    if 'pet' in args:
        touchPet()

    if 'logout' in args:
        roxLogout()

    if 'restorewin' in args and winTitle:
        for w in pyautogui.getWindowsWithTitle('ROX'):
            if w.title == winTitle:
                w.restore()

    openDos()

