# ANIP - Analog subscriber at the IP network
# (C) 2014 - Norbert Huffschmid

import RPi.GPIO as GPIO
import potsbliz.tone_generator as tone_generator
from datetime import datetime
from threading import Timer
from potsbliz.logger import Logger

GPIO_CHANNEL_HOOK = 8
GPIO_CHANNEL_DIALER = 10
GPIO_CHANNEL_GROUND_KEY = 12

ROTATION_TIMER = 0.3
HOOKFLASH_DOWN_TIMER = 0.5
HOOKFLASH_UP_TIMER = 0.5


class Anip(object):
    
    TOPIC_ONHOOK = 'topic_onhook'
    TOPIC_OFFHOOK = 'topic_offhook'
    TOPIC_DIGIT_DIALED = 'topic_digit_dialed'
    

    def __init__(self, pub):
        with Logger(__name__ + '.__init__'):
            self._pub = pub


    def __enter__(self):
        with Logger(__name__ + '.__enter__'):
            
            GPIO.setmode(GPIO.BOARD)
            GPIO.setup(GPIO_CHANNEL_HOOK, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.setup(GPIO_CHANNEL_DIALER, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.setup(GPIO_CHANNEL_GROUND_KEY, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.add_event_detect(GPIO_CHANNEL_HOOK, GPIO.BOTH, bouncetime=50)
            GPIO.add_event_detect(GPIO_CHANNEL_DIALER, GPIO.RISING, bouncetime=80)
            GPIO.add_event_detect(GPIO_CHANNEL_GROUND_KEY, GPIO.BOTH, bouncetime=20)
            GPIO.add_event_callback(GPIO_CHANNEL_HOOK, self._hook)
            GPIO.add_event_callback(GPIO_CHANNEL_DIALER, self._dialpulse)
            GPIO.add_event_callback(GPIO_CHANNEL_GROUND_KEY, self._ground_key)
            
            self._pulse_counter = 0
            self._hookflash_counter = 0
            
            self._rotation_timer = Timer(ROTATION_TIMER, self._end_of_rotation)
            self._hookflash_down_timer = Timer(HOOKFLASH_DOWN_TIMER, self._hookflash_down_timeout)
            self._hookflash_up_timer = Timer(HOOKFLASH_UP_TIMER, self._hookflash_up_timeout)
            
            if (not GPIO.input(GPIO_CHANNEL_HOOK)):
                self._hook(GPIO_CHANNEL_HOOK)
                

    def __exit__(self, type, value, traceback):
        with Logger(__name__ + '.__exit__'):
            self.stop_dialtone()


    def start_dialtone(self):
        with Logger(__name__ + '.start_dialtone'):
            tone_generator.start_dialtone()


    def stop_dialtone(self):
        with Logger(__name__ + '.stop_dialtone'):
            tone_generator.stop_dialtone()


    def play_ok_tone(self):
        with Logger(__name__ + '.play_ok_tone'):
            tone_generator.play_ok_tone()
            

    def play_error_tone(self):
        with Logger(__name__ + '.play_error_tone'):
            tone_generator.play_error_tone()


    def ring_bell(self):
        pass # not supported yet


    def stop_bell(self):
        pass # not supported yet


    def _hook(self, channel):
        with Logger(__name__ + '._hook'):
            if (GPIO.input(channel) == 0):
                self._offhook()
            else:    
                self._onhook()


    def _dialpulse(self, channel):
        with Logger(__name__ + '._dialpulse') as log:

            log.debug('Dialpulse detected')
            self._pulse_counter += 1
            self._rotation_timer.cancel()
            self._rotation_timer = Timer(ROTATION_TIMER, self._end_of_rotation)
            self._rotation_timer.start()


    def _ground_key(self, channel):
        with Logger(__name__ + '._ground_key') as log:

            if (GPIO.input(channel) == 0):
                log.debug('Ground key pressed.')
                self._onhook()
            else:
                log.debug('Ground key released.')
                self._offhook()


    def _onhook(self):
        with Logger(__name__ + '._onhook') as log:
            self._hookflash_counter += 1
            self._rotation_timer.cancel()
            self._hookflash_down_timer.cancel()
            log.debug('Starting hookflash_down timer ...')
            self._hookflash_down_timer = Timer(HOOKFLASH_DOWN_TIMER, self._hookflash_down_timeout)
            self._hookflash_down_timer.start()


    def _offhook(self):
        with Logger(__name__ + '._offhook') as log:

            if (self._hookflash_counter == 0):
                self._pub.sendMessage(self.TOPIC_OFFHOOK)
                self._pulse_counter = 0
            else:
                self._hookflash_down_timer.cancel()
                self._hookflash_up_timer.cancel()
                log.debug('Starting hookflash_up timer ...')
                self._hookflash_up_timer = Timer(HOOKFLASH_UP_TIMER, self._hookflash_up_timeout)
                self._hookflash_up_timer.start()
    
    
    def _end_of_rotation(self):
        with Logger(__name__ + '._end_of_rotation'):

            if (self._pulse_counter == 10):
                self._pulse_counter = 0 # 10 -> 0

            self._pub.sendMessage(self.TOPIC_DIGIT_DIALED, digit=str(self._pulse_counter))
            
            self._pulse_counter = 0


    def _hookflash_down_timeout(self):
        with Logger(__name__ + '._hookflash_down_timeout'):        
            
            self._hookflash_up_timer.cancel()
            self._hookflash_counter = 0
            
            self._pub.sendMessage(self.TOPIC_ONHOOK)
        

    def _hookflash_up_timeout(self):
        with Logger(__name__ + '._hookflash_up_timeout') as log:        

            log.debug(str(self._hookflash_counter) + ' hookflashs detected')
            
            if (self._hookflash_counter == 1):
                self._pub.sendMessage(self.TOPIC_DIGIT_DIALED, digit='#')
            elif (self._hookflash_counter == 2):
                self._pub.sendMessage(self.TOPIC_DIGIT_DIALED, digit='*')
            else:
                log.debug('Hookflashs ignored')
                
            self._hookflash_counter = 0
