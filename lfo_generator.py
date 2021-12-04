import mido
from mido import Message
import time
#from collections import deque
import numpy as np
import re

LFO_CHANNEL_NO = 15
BPM = 140
BEATS_PER_BAR = 4
BEAT_TIME = 60/BPM
SIXTEENTH_NOTE_TIME = BEAT_TIME / 4
BAR_TIME = BEAT_TIME * BEATS_PER_BAR
MIDI_INPUT_PORT = 'humanizer 2'
MIDI_OUTPUT_PORT = 'loopMIDI Port 2'

#Program initialise functions

def open_midi_ports(MIDI_INPUT_PORT, MIDI_OUTPUT_PORT):
    print('\n')
    print('INPUT PORTS: ')
    print (mido.get_input_names())
    print('\n')
    print('OUTPUT PORTS: ')
    print (mido.get_output_names())
    inport = mido.open_input(MIDI_INPUT_PORT)
    outport = mido.open_output(MIDI_OUTPUT_PORT)
    print(f'Connected input to {MIDI_INPUT_PORT}')
    print(f'Connected output to {MIDI_OUTPUT_PORT}')
    return inport, outport

def send_midi_message(value):
    msg = mido.Message('control_change', channel=CHANNEL_NUMBER, control=1, value=value)
    outport.send(msg)
    return

def count_in():
    #Count in to sync program with ableton
    counter = 0
    bars = int(input('Enter number of count in bars: '))
    total_beats = bars * 16 + 1
    for msg in inport:
        msg_str = str(msg)
        channel = int(re.search(r'channel=(.*?) ', msg_str).group(1))
        if channel == 0 and bool(re.search(r'note_on', msg_str)):
            counter = counter + 1
            if counter % 4 == 0:
                print((((total_beats - counter)-1)/4)+1)
        if counter >= total_beats:
            return

def lfo_sync(CHANNEL_NUMBER, lfo_list):
    message = ''
    print('Press esc for next lfo')
    for lfo in lfo_list:
        control_number = 0
        print (f'...CC {control_number}')
        msg = mido.Message('control_change', channel=CHANNEL_NUMBER, control=control_number)
        while 1:
            time.sleep(2)
            outport.send(msg)
            if msvcrt.kbhit():
                if ord(msvcrt.getch()) == 27 :
                    break
        control_number += 1
    return
    
    
    

class Lfo:

    def __init__(self, control_number, frequency, offset):
        self.control_number = control_number
        self.frequency = frequency
        self.offset = offset / 360 * 2 * np.pi

    def check_time(self, T0):
        current_time = time.time() - T0
        return current_time

    def get_beat_number(self, T0):
        #Return current 16th note beat number
        beat_number = -1
        bar_time_passed = self.check_time(T0) - BAR_TIME * self.get_bar_number(T0)
        while bar_time_passed > 0:
            bar_time_passed = bar_time_passed - SIXTEENTH_NOTE_TIME
            beat_number = beat_number + 1
        return beat_number

    def get_bar_number(self, T0):
        #Return current bar number
        bar_number = -1
        track_time_passed = self.check_time(T0)
        while track_time_passed > 0:
            track_time_passed = track_time_passed - BAR_TIME
            bar_number = bar_number + 1
        return bar_number

    def get_beats_passed_time(self, T0):
        #Return length of bar passed so far
        beats_passed_time = (self.get_beat_number(T0))*SIXTEENTH_NOTE_TIME
        return beats_passed_time

    def get_bars_passed_time(self, T0):
        #Return bar time passed so far
        bars_passed_time = self.get_bar_number(T0)*BAR_TIME
        return bars_passed_time

    def get_control_value(self, T0):
        radians = ((self.get_beats_passed_time(T0) / BAR_TIME) * 2 * np.pi + self.offset) * self.frequency 
        amplitude = np.sin(radians)
        control_value = int(round((amplitude + 1) / 2 * 127))
        #print(control_value)
        #print(radians / (2 * np.pi) * 360)
        msg = mido.Message('control_change', channel=LFO_CHANNEL_NO, control=self.control_number, value=127)
        return msg

    def map_midi(self):

        outport.send(msg)
        return
    

if __name__ == "__main__":
    inport, outport = open_midi_ports(MIDI_INPUT_PORT, MIDI_OUTPUT_PORT)
    lfo_1 = Lfo(1, 1.5, 180)
    lfo_2 = Lfo(2, 2, 0)
    lfo_3 = Lfo(3, 0.75, 180)
    lfo_4 = Lfo(4, 0.4, 0)
    lfo_5 = Lfo(5, 3, 180)
    input('Press enter to start sync...')
    #lfo_1.map_midi()
    #lfo_2.map_midi()
    #lfo_3.map_midi()
    #lfo_4.map_midi()
    lfo_5.map_midi()
    count_in()
    T0 = time.time()
    while 1:
        control_value = lfo_1.get_control_value(T0)
        send_midi_message(control_value)
        control_value = lfo_2.get_control_value(T0)
        send_midi_message(control_value)
        control_value = lfo_3.get_control_value(T0)
        send_midi_message(control_value)
        control_value = lfo_4.get_control_value(T0)
        send_midi_message(control_value)
        time.sleep(SIXTEENTH_NOTE_TIME)
    
