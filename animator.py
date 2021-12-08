import humanizer as hum
import lfo_generator as lfo_gen
import random_scene_generator as rsg

import time
import mido
import numpy as np
from scipy.stats import truncnorm
import multiprocessing
import threading
from multiprocessing import Queue
from multiprocessing.managers import SyncManager
import re
import math
import glob
import msvcrt


BPM = 140
BEATS_PER_BAR = 4
BEAT_TIME = 60/BPM
BAR_TIME = BEAT_TIME * BEATS_PER_BAR
SIXTEENTH_NOTE_TIME = BEAT_TIME / 4
MIDI_INPUT_PORT = 'humanizer 2'
MIDI_OUTPUT_PORT = 'loopMIDI Port 4'
SECTION_CONTROL_LIST = [1, 4, 7, 10, 13, 16, 19, 22]
RSG_CHANNEL_NO = 1
LFO_CHANNEL_NO = 2
MAX_MAIN_WORKERS = 40
MAX_OUTPUT_WORKERS = 8
#Input queue must be global for callback
in_queue = Queue()

def load_sync_file(file_dir, extension):
    file = glob.glob(file_dir + '/' + '*' + extension)
    if len(file) != 1:
        raise ValueError(f'should be one {extension} file in the current directory')
    file_obj = open(file[0], 'r')
    for line in file_obj:
        sync_file = eval(line)
    if extension == '.rsg':
        return rsg_sync_file(sync_file)
    else:
        return alternative_sync(extension, sync_file)
        
def rsg_sync_file(sync_file):
    section_control_list = []
    for SECTION_NUMBER in range(len(sync_file)) :
        section_control_list.append(SECTION_CONTROL_LIST[SECTION_NUMBER])
    return sync_file, section_control_list

def alternative_sync(extension, sync_file):
    obj_list = []
    if extension == '.lfo':
        for obj in sync_file:
            obj_list.append(lfo_gen.Lfo(obj[0], obj[1], obj[2]))
    else:
        for obj in sync_file:
            obj_list.append(hum.Cpu(obj[0], obj[1], obj[2]))
    return obj_list


class Worker:

    def __init__(self):
        pass
    
    def send_midi_message(self, message, outport):
        outport.send(message)   
        return 

    def add_to_send_queue(self, message, out_queue):
        out_queue.put(message, block=False)
        return
        
    def read_midi_message(self, msg, metronome_1, human_1, lfo_list, cpu_list, T0, timing_array, previous_beat, metronome_error, out_queue, metronome_timestamp):
        #Sort message and call relevant functions
        t1 = time.time()
        msg_type = msg.type
        channel = msg.channel
        msg_str = str(msg)
        if channel == 1 :
            if msg_type == 'note_on' and msg.velocity > 10:
                self.add_to_send_queue(msg, out_queue)
                human_1.record_timing(timing_array, T0)
                print('added timing')
                return
            if msg_type == 'note_off' :
                self.add_to_send_queue(msg, out_queue)
                return
        if msg_type == 'note_on' :
            if channel == 0 :
                metronome_error.value = metronome_1.beat_error(T0)
                metronome_timestamp.value = time.time()
                for lfo in lfo_list:
                    msg = lfo.get_control_value(T0, LFO_CHANNEL_NO)
                    self.add_to_send_queue(msg, out_queue)
                return
            if channel == 16 :
                controller = int(re.search(r'note=(.*?) velocity', msg_str).group(1))
                if controller in section_control_list :
                    control_message = {'section':section_control_list.index(controller)}
                    control_message_dict.update(control_message)
                    return control_message_dict
            else:
                timing = cpu_list[channel-2].allocate_timing(timing_array, previous_beat, T0)
                cpu_list[channel-2].time_message(timing, t1, metronome_error, metronome_timestamp)
                self.add_to_send_queue(msg, out_queue)
                return


    def multiprocess_init(self, lfo_list, cpu_list, T0, timing_array, previous_beat, metronome_error, metronome_timestamp, in_queue, out_queue, outport):
        #Initialise multiprocessing for main workers and message publishers
        for _ in range(MAX_MAIN_WORKERS):
            p = multiprocessing.Process(target=self.worker_main, args=(lfo_list, cpu_list, T0, timing_array, previous_beat, metronome_error, metronome_timestamp, in_queue, out_queue,))
            p.start()
        for _ in range(MAX_OUTPUT_WORKERS):
            q = threading.Thread(target=self.output_worker, args=(out_queue, outport))
            q.start()
        return 

    def worker_main(self, lfo_list, cpu_list, T0, timing_array, previous_beat, metronome_error, metronome_timestamp, in_queue, out_queue,):
        #Main worker initialisation and loop
        metronome_1 = hum.Metronome(0)
        human_1 = hum.Human(1)
        while 1:
            msg = in_queue.get()
            self.read_midi_message(msg, metronome_1, human_1, lfo_list, cpu_list, T0, timing_array, previous_beat, metronome_error, out_queue, metronome_timestamp)
    
    def output_worker(self, out_queue, outport):
        #Publish output messages from main workers
        while 1:
                msg = out_queue.get()
                self.send_midi_message(msg, outport)
                
    def input_worker(self, msg):
        #Called when message arrives in midi input port
        in_queue.put(msg, block=False)
        return
    
    

if __name__=='__main__':
    print("\n--Program Setup--\n")
    inport, outport = rsg.open_midi_ports(MIDI_INPUT_PORT, MIDI_OUTPUT_PORT)
    if input('Load sync files? y/n : ') == 'y' :
        file_dir = input('Please enter file directory : ')
        file_extension = '.rsg'
        ALL_SECTIONS_ARRAY, section_control_list = load_sync_file(file_dir, file_extension)
        file_extension = '.lfo'
        lfo_list = load_sync_file(file_dir, file_extension)
        file_extension = '.hum'
        cpu_list = load_sync_file(file_dir, file_extension)    
    else :
        print('proceeding with manual sync...')
        msg = input("\nPress enter to start scene_gen sync or 'q' to skip: ")
        if msg != 'q':
            ALL_SECTIONS_ARRAY, section_control_list = rsg.sync_song(SECTION_CONTROL_LIST, outport)
            print('Sync finished.')
            file_dir = rsg.write_sync_file(ALL_SECTIONS_ARRAY)
        else:
            file_dir = input('Please enter file directory: ')
        input("\nPress enter to start lfo sync.")
        file_extension = '.lfo'
        lfo_list = load_sync_file(file_dir, file_extension)
        lfo_gen.lfo_sync(LFO_CHANNEL_NO, lfo_list, outport)
        file_extension = '.hum'
        cpu_list = load_sync_file(file_dir, file_extension)
    print('Initialising class instances...')
    metronome_1 = hum.Metronome(0)
    worker = Worker()
    out_queue = Queue()
    print('Setting up process manager...')
    manager = SyncManager()
    manager.start()
    scalar_timing_array = np.ndarray.tolist(np.zeros((16,5)))
    timing_array = manager.list(scalar_timing_array)
    previous_beat_array = [0,0]
    previous_beat = manager.list(previous_beat_array)
    metronome_error = manager.Value('f', 0)
    T0 = manager.Value('f', time.time())
    metronome_timestamp = manager.Value('f', 0)
    section = 0
    control_message_dict = {'section':section}
    control_dict = manager.dict(control_message_dict)
    print('Initialising multiprocessing...')
    worker.multiprocess_init(lfo_list, cpu_list, T0, timing_array, previous_beat, metronome_error, metronome_timestamp, in_queue, out_queue, outport)
    input_port_set = False
    while 1:
        if input_port_set:
            port.callback = None
        metronome_1.count_in(inport)
        inport.callback = worker.input_worker
        ALL_TRACKS_ARRAY = ALL_SECTIONS_ARRAY[section]
        print('program starting...')
        while 1:
            if section != control_dict.get('section'):
                section = control_dict.get('section')
                section_string = section + 1
                print(f'Now playing section {section_string}')
                ALL_TRACKS_ARRAY = ALL_SECTIONS_ARRAY[section]
                rsg.run_section(BAR_TIME, ALL_TRACKS_ARRAY, outport)
            else:
                rsg.run_section(BAR_TIME, ALL_TRACKS_ARRAY, outport)
            if msvcrt.kbhit():
                if ord(msvcrt.getch()) == 27 :
                    input_port_set = True
                    break
