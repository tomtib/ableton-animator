#You will need to download loop midi and create a midi port

import mido
from mido import Message
import time
from collections import deque
import random
import msvcrt
import re
import numpy as np
import os

CHANNEL_NUMBER = 1

TEMPO = 140
BEATS_PER_BAR = 4
BAR_LENGTH = 60/TEMPO*BEATS_PER_BAR
MIDI_INPUT_PORT = 'humanizer 1'
MIDI_OUTPUT_PORT = 'loopMIDI Port 1'
SECTION_CONTROL_LIST = [1, 4, 7, 10, 13, 16, 19, 22]

#Program initialise functions

def open_midi_ports(MIDI_INPUT_PORT, MIDI_OUTPUT_PORT):
    print('\n')
    print('INPUT PORTS: ')
    print (mido.get_input_names()) # To list the input ports
    print('\n')
    print('OUTPUT PORTS: ')
    print (mido.get_output_names()) # To list the output ports
    inport = mido.open_input(MIDI_INPUT_PORT)
    outport = mido.open_output(MIDI_OUTPUT_PORT)
    print(f'Connected input to {MIDI_INPUT_PORT}')
    print(f'Connected output to {MIDI_OUTPUT_PORT}')
    return inport, outport

def sync_song(SECTION_CONTROL_LIST, outport):
    CONTROL_NUMBER = 0
    SECTION_NUMBER = 1
    ALL_SECTIONS_ARRAY = []
    section_control_list = []
    MAIN_MESSAGE = ''
    while MAIN_MESSAGE != 'q':
        print(f'\nSection {SECTION_NUMBER}')
        ALL_TRACKS_ARRAY, CONTROL_NUMBER = assign_section(MAIN_MESSAGE, CONTROL_NUMBER, CHANNEL_NUMBER, outport)
        ALL_SECTIONS_ARRAY.append(ALL_TRACKS_ARRAY)
        section_control_list.append(SECTION_CONTROL_LIST[SECTION_NUMBER - 1])
        SECTION_NUMBER = SECTION_NUMBER + 1
        MAIN_MESSAGE = input("Enter for next section or 'q' to finish sync : ")
    return ALL_SECTIONS_ARRAY, section_control_list

def assign_section(MAIN_MESSAGE, CONTROL_NUMBER, CHANNEL_NUMBER, outport):
    ALL_TRACKS_ARRAY = []
    TRACK_NUMBER = 1
    while MAIN_MESSAGE != 'q':
        print(f'Track {TRACK_NUMBER}')
        TRACK_ARRAY, CONTROL_NUMBER = assign_clips_to_channels(CHANNEL_NUMBER, CONTROL_NUMBER, outport)
        ALL_TRACKS_ARRAY.append(TRACK_ARRAY)
        TRACK_NUMBER = TRACK_NUMBER + 1
        MAIN_MESSAGE = input("Enter for next track or 'q' to finish sync/next section : ")
        print('\n')
    return ALL_TRACKS_ARRAY, CONTROL_NUMBER
    
def assign_clips_to_channels(CHANNEL_NUMBER, CONTROL_NUMBER, outport):
    time.sleep(2)
    clips_message = 'n'
    counter = 0
    while clips_message == 'r' or clips_message == 'n' :
        TRACK_ARRAY = []
        if clips_message == 'r':
            CONTROL_NUMBER = CONTROL_NUMBER - counter 
            counter = 0
        while 1:
            print (f'...CC {CONTROL_NUMBER}')
            msg = mido.Message('control_change', channel=CHANNEL_NUMBER, control=CONTROL_NUMBER)
            outport.send(msg)
            time.sleep(2)
            TRACK_ARRAY.append(CONTROL_NUMBER)
            CONTROL_NUMBER = CONTROL_NUMBER + 1
            counter = counter + 1
            if msvcrt.kbhit():
                if ord(msvcrt.getch()) == 27 :
                    break
        clips_message = input("Press enter for next track/finish or 'r' to redo : ")
    return TRACK_ARRAY, CONTROL_NUMBER

def load_sync_file(SECTION_CONTROL_LIST):
    section_control_list = []
    filepath = input('Please enter filepath : ')
    sync_file_obj = open(filepath, 'r')
    for line in sync_file_obj:
        sync_file = eval(line)
    for SECTION_NUMBER in range(len(sync_file)) :
        section_control_list.append(SECTION_CONTROL_LIST[SECTION_NUMBER])
    print(section_control_list)
    return sync_file, section_control_list

def write_sync_file(ALL_SECTIONS_ARRAY):
    song_name = input('Please enter the name of the song: ')
    filepath = input('Please enter file name: ')
    if not os.path.isdir(song_name):
        os.mkdir(song_name)
    with open(f"{song_name}/{filepath}", "w") as txt_file:
        txt_file.write(str(ALL_SECTIONS_ARRAY))
    return song_name
    
#Program run functions

def track_change():
    number = random.randint(0,5)
    if number > 2 :
        return True
    return False

def get_control_number(track):
    random_index = random.randint(0, len(track)-1)
    return track[random_index]

def send_midi_message(control_number, outport):
    msg = mido.Message('control_change', channel=CHANNEL_NUMBER, control=control_number, value=127)
    outport.send(msg)
    return

def run_section(BAR_LENGTH, ALL_TRACKS_ARRAY, outport):
    t0 = time.time()
    for track in ALL_TRACKS_ARRAY:
        if track_change():
            control_number = get_control_number(track)
            send_midi_message(control_number, outport)
        else :
            control_number = track[0]
            send_midi_message(control_number, outport)
    t1 = time.time()
    sleep_time = BAR_LENGTH - (t0-t1)
    time.sleep(sleep_time)
    return
    
def read_midi_messages(inport, control_message_dict):
    for msg in inport.iter_pending() :
        print(msg)        
        control_message_dict = check_control_message(msg, control_message_dict)
    return control_message_dict

def check_control_message(msg, control_message_dict):
    msg_str = str(msg)
    channel = int(re.search(r'channel=(.*?) ', msg_str).group(1))
    if channel == 1 :
        return control_message_dict
    if channel == 0 :
        controller = int(re.search(r'note=(.*?) velocity', msg_str).group(1))
        if controller in section_control_list :
            control_message = {'section':section_control_list.index(controller)}
            control_message_dict.update(control_message)
            return control_message_dict
    if channel == 2 :
        return control_message_dict
    else :
        return control_message_dict
    
if __name__ == "__main__":
    inport, outport = open_midi_ports(MIDI_INPUT_PORT, MIDI_OUTPUT_PORT)
    if input('Load sync file? y/n : ') == 'y' :
        ALL_SECTIONS_ARRAY, section_control_list = load_sync_file(SECTION_CONTROL_LIST)
    else :
        print('Manual sync...')
        input("Press enter to start sync")
        print('\n')
        ALL_SECTIONS_ARRAY, section_control_list = sync_song(SECTION_CONTROL_LIST)
        print('Sync finished.')
        if input('Write to file? y/n : ') == 'y' :
            write_sync_file(ALL_SECTIONS_ARRAY)           
    print(ALL_SECTIONS_ARRAY)
    print(section_control_list)
    while 1:
        print('\n')
        section = int(input('Select section number to play first : ')) - 1
        input('Press enter to start program')
        print('Running program...')   
        ALL_TRACKS_ARRAY = ALL_SECTIONS_ARRAY[section]
        control_message_dict = {'section':section}
        while 1:
            if inport.poll():
                control_message_dict = read_midi_messages(inport, control_message_dict)
            if section != control_message_dict.get('section'):
                section = control_message_dict.get('section')
                section_string = section + 1
                print(f'Now playing section {section_string}')
                ALL_TRACKS_ARRAY = ALL_SECTIONS_ARRAY[section]
                run_section(BAR_LENGTH, ALL_TRACKS_ARRAY)
            else:
                run_section(BAR_LENGTH, ALL_TRACKS_ARRAY)
            if msvcrt.kbhit():
                if ord(msvcrt.getch()) == 27 :
                    break
        
        

        
        
        
        
        
        
        
            
    
    
        
    
        


