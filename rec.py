#!/usr/bin/env python3
import soundcard as sc
import sounddevice as sd
import threading
import time
import argparse
import numpy as np
import wavio as wv
import os
import signal


class RecordThread(threading.Thread):
    # конструктор класса
    def __init__(self, use_mic, use_speaker, filename, stop_event):
        threading.Thread.__init__(self)
        self.use_mic = use_mic
        self.use_speaker = use_speaker
        self.stop_event = stop_event
        self.filename = filename

    def run(self):
        recorded_data = []
        # recorded_data = np.empty((0, 2), np.float32)  # создаем массив в котором будет хранится запись с микрофона
        with self.use_mic.recorder(samplerate=48000,blocksize=1) as mic, \
                self.use_speaker.player(
                    samplerate=48000,blocksize=1) as sp:  # получаем объекты Recorder и Player для записи и проигывания аудио
            start_record_time = time.time()  # получаем время когда начали запись
            while time.time() - start_record_time < 60:
                data = mic.record(numframes=None)  # получаем те данные которые есть сейчас без буфферизации
                sp.play(data)  # проигрываем записанные данные в динамик
                mic.flush()
                # recorded_data = np.append(recorded_data, data)  # дописываем данные в массив
                recorded_data += np.ndarray.tolist(data)
                self.dur = time.time() - start_record_time
                if stop_event.isSet() and self.dur >= 5:  # если пользователь прервал запись
                    self.save(filename, recorded_data)
                    return # и время записи больше чем 5 секунд то прерываем цикл
        self.save(filename, recorded_data)
        # шлем SIGINT чтобы сбросить input()
        os.kill(os.getpid(), signal.SIGINT)

    def save(self, fname, data):
        data = self.convert2numpy(data)  # конвертируем в массив numpy т.к. wavio принимает на вход
        data *= 2  # усиливаем записанное аудио в 2 раза
        # т.к библиотека soundcard пишет в float32 а некоторые плееры не умеют воспроизводить .wav
        # записанный в таком формате нам надо преобразовать float32 в int16
        data = self.float2pcm(data)
        # сохраняем в файл
        wv.write(fname, data, 48000)

    # Функция для преобразования float32 в pcm массив numpy.
    # Взята с https://github.com/mgeier/python-audio/blob/master/audio-files/utility.py
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

    # конвертируем список в массив numpy
    def convert2numpy(self, data):
        np_array = np.array(data)
        return np_array.astype(np.float32)

    # переопределяем метод join чтобы он возвращал длинну записи
    def join(self, *args):
        threading.Thread.join(self, *args)
        return self.dur


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

    default_speaker = sc.default_speaker()  # Получаем текущие динамики по умолчанию в системе
    default_mic = sc.default_microphone()  # Получаем текущий микрофон по умолчанию в системе
    stop_event = threading.Event()  # Event для того чтобы остановить поток который записывает аудио

    print("file: {0}".format(filename))
    input("Press Enter to start recording")
    try:
        t = RecordThread(default_mic, default_speaker, filename, stop_event)
        t.start()  # запускаем поток для начала записи
        input("Press Enter to stop recording")
        stop_event.set()  # отдаем команду остановки записи
        print("Stopping record...")
        duration = t.join()  # получаем длительность записи
        print("Recorded time {0} sec".format(duration))
        time.sleep(1)
    except:
        print("\nStopped by timeout. Recorded time 60 sec")
