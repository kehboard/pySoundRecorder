#!/usr/bin/env python3
import soundcard as sc
import threading
import time
import argparse
import numpy as np
import wavio as wv


class RecordThread(threading.Thread):
    def __init__(self, use_mic, use_speaker, filename, stop_event):
        threading.Thread.__init__(self)
        self.use_mic = use_mic
        self.use_speaker = use_speaker
        self.stop_event = stop_event

    def run(self):
        recorded_data = np.empty((0, 2), np.float32)
        with self.use_mic.recorder(samplerate=48000) as mic, \
                self.use_speaker.player(samplerate=48000) as sp:
            start_record_time = time.time()
            while time.time() - start_record_time < 60:
                data = mic.record()
                recorded_data = np.append(recorded_data, data)
                sp.play(data)
                if stop_event.isSet() and time.time() - start_record_time >= 5:
                    break
        recorded_data *= 2
        recorded_data = self.float2pcm(recorded_data)
        wv.write(filename, recorded_data, 96000)

    def float2pcm(self, sig, dtype='int16'):
        sig = np.asarray(sig)
        if sig.dtype.kind != 'f':
            raise TypeError("'sig' must be a float array")
        dtype = np.dtype(dtype)
        if dtype.kind not in 'iu':
            raise TypeError("'dtype' must be an integer type")

        i = np.iinfo(dtype)
        abs_max = 2 ** (i.bits - 1)
        offset = i.min + abs_max
        return (sig * abs_max + offset).clip(i.min, i.max).astype(dtype)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Record audio to wav file')
    parser.add_argument('-p', action='store',
                        help='path to file .wav')
    args = parser.parse_args()
    filename = ""
    if args.p:
        filename = args.p
    else:
        parser.print_help()
        exit()
    default_speaker = sc.default_speaker()
    default_mic = sc.default_microphone()
    stop_event = threading.Event()
    t = RecordThread(default_mic, default_speaker, filename, stop_event)
    print("file: {0}".format(filename))
    stime = time.time()
    input("Press Enter to start recording")
    t.start()
    input("Press Enter to stop recording")
    stop_event.set()
    print("Stopping record...", end="")
    print("Recorded time {0}".format(time.time() - stime))


# #time.sleep(5)
