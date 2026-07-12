from __future__ import print_function
from __future__ import absolute_import
from future import standard_library
import glob
import random
from pygame import mixer  # Load the required library
import os
import datetime
import time


class AudioLibrary(object):

    def __init__(self, sounds_dir, volume):
        self.audio_available = False
        if __debug__:
            print("Initiating audio")
        try:
            mixer.init()
            mixer.music.set_volume(float(volume))
            self.audio_available = True
        except Exception as e:
            print(f"WARNING: Audio mixer could not be initialized: {e}")
            print("Server will run without local audio support.")

    def TriggerSound(self, data):
        if not self.audio_available:
            if __debug__:
                print("MOCK AUDIO: Playing %s" % data)
            return
            
        if __debug__:
            print("Playing %s" % data)
        audio_file = "./sounds/" + data + ".mp3"
        # mixer.init()
        if __debug__:
            print("Init mixer")
        mixer.music.load(audio_file)  # % (audio_dir, data))
        if __debug__:
            print("%s Loaded" % audio_file)
        mixer.music.play()
        if __debug__:
            print("Play")

    def ListSounds(self):
        files = ', '.join(glob.glob("./sounds/*.mp3"))
        files = files.replace("./sounds/", "", -1)
        files = files.replace(".mp3", "", -1)
        return files

    def ShowVolume(self):
        if not self.audio_available:
            return "0.0 (Audio Disabled)"
        cur_vol = str(mixer.music.get_volume())
        return cur_vol

    def SetVolume(self, level):
        if not self.audio_available:
            return "Ok (Audio Disabled)"
            
        if level == "up":
            if __debug__:
                print("Increasing volume")
            new_level = mixer.music.get_volume() + 0.025
        elif level == "down":
            if __debug__:
                print("Decreasing volume")
            new_level = mixer.music.get_volume() - 0.025
        else:
            if __debug__:
                print("Volume level explicitly states")
            new_level = level
        if new_level < 0:
            new_level = 0
        if __debug__:
            print("Setting volume to: %s" % new_level)
        mixer.music.set_volume(float(new_level))
        return "Ok"
