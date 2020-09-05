from time import time

import RPi.GPIO as GPIO
import sys
from subprocess import check_output

# KY-022 Sensor GND to Raspbery Pi GND
# KY-022 Sensor Vcc+ to Raspberry Pi PIN 2
# KY-022 Sensor Signal to Raspberry Pi PIN 11

DATA_PIN = 11

# TS-12+AL remote codes:
TS12_INPUT = 0x2fdf00f
TS12_POWER = 0x2fd48b7
TS12_SLEEP = 0x2fda857
TS12_FREEZE = 0x2fd32cd
TS12_PIC_MODE = 0x2fdb44b
TS12_1 = 0x2fd807f
TS12_2 = 0x2fd40bf
TS12_3 = 0x2fdc03f
TS12_4 = 0x2fd20df
TS12_5 = 0x2fda05f
TS12_6 = 0x2fd609f
TS12_7 = 0x2fde01f
TS12_8 = 0x2fd10ef
TS12_9 = 0x2fd906f
TS12_0 = 0x2fd00ff
TS12_100 = 0x2fd50af
TS12_FAV = 0x2fdba45
TS12_VOL_UP = 0x2fd58a7
TS12_VOL_DOWN = 0x2fd7887
TS12_RECALL = 0x2fd38c7
TS12_MUTE = 0x2fd08f7
TS12_CCAPTION = 0x2fdea15
TS12_CHN_UP = 0x2fdd827
TS12_CHN_DOWN = 0x2fdf807
TS12_CH_RTN = 0x2fde817
TS12_MENU = 0x2fd01fe
TS12_INFO = 0x2fd21de
TS12_EXIT = 0x2fd1ae5
TS12_UP = 0x2fd41be
TS12_LEFT = 0x2fdb847
TS12_RIGHT = 0x2fd9867
TS12_DOWN = 0x2fdc13e
TS12_ENTER = 0x2fd916e
TS12_EJECT = 0x2fd916e
TS12_PAUSE = 0x2fdac53
TS12_PLAY = 0x2fd0cf3
TS12_STOP = 0x2fd8c73
TS12_SKIP_BACKW = 0x2fdec13
TS12_REWIND = 0x2fd2cd3
TS12_FF = 0x2fdcc33
TS12_SKIP_FORW = 0x2fd6c93

COMMANDS = {
    TS12_LEFT: "ssh Hive cmus-remote --prev",
    TS12_SKIP_BACKW: "ssh Hive cmus-remote --prev",
    TS12_RIGHT: "ssh Hive cmus-remote --next",
    TS12_SKIP_FORW: "ssh Hive cmus-remote --next",
    TS12_ENTER: "ssh Hive cmus-remote --pause",
    TS12_CCAPTION: "ssh Hive cmus-remote --shuffle",
    TS12_DOWN: "ssh Hive cmus-remote --volume -10%",
    TS12_VOL_DOWN: "ssh Hive cmus-remote --volume -10%",
    TS12_VOL_UP: "ssh Hive cmus-remote --volume +10%",
    TS12_UP: "ssh Hive cmus-remote --volume +10%",
    TS12_REWIND: "ssh Hive cmus-remote --seek -25",
    TS12_FF: "ssh Hive cmus-remote --seek +25",
    TS12_POWER: "ssh Hive bash /home/simon/scripts/hv_layout_off",
    TS12_INPUT: "ssh Hive bash /home/simon/scripts/hv_layout",
}


def execute_command(code):
    if code not in COMMANDS:
        print("Unknown code: %d" % code)
        return

    try:
        cmd = COMMANDS[code]
        out = check_output(["bash", "-c", cmd])
        print(out)
    except:
        pass


def setup():
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(DATA_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)


def binary_aquire(pin, duration):
    t0 = time()
    results = []
    while (time() - t0) < duration:
        results.append(GPIO.input(pin))
    return results


def on_ir_receive(pin_no, bounce_time=75):
    # when edge detect is called (which requires less CPU than constant
    # data acquisition), we acquire data as quickly as possible
    data = binary_aquire(pin_no, bounce_time / 1000.0)
    if len(data) < bounce_time:
        return None
    rate = len(data) / (bounce_time / 1000.0)
    pulses = []
    i_break = 0
    # detect run lengths using the acquisition rate to turn the times in to microseconds
    for i in range(1, len(data)):
        if not pulses and data[i] == 1:
            continue
        if (data[i] != data[i - 1]) or (i == len(data) - 1):
            pulses.append((data[i - 1], int((i - i_break) / rate * 1e6)))
            i_break = i
    # decode ( < 1 ms "1" pulse is a 1, > 1 ms "1" pulse is a 1, longer than 2 ms pulse is something else)
    # does not decode channel, which may be a piece of the information after the long 1 pulse in the middle
    out_bin = ""
    for val, us in pulses:
        if val != 1:
            continue
        if out_bin and us > 2000:
            break
        elif us < 1000:
            out_bin += "0"
        elif 1000 < us < 2000:
            out_bin += "1"
    try:
        if len(out_bin) != 32:
            return None
        return int(out_bin, 2)
    except ValueError as e:
        # probably an empty code
        return None


if __name__ == "__main__":
    setup()
    try:
        print("Starting IR Listener")
        while True:
            GPIO.wait_for_edge(DATA_PIN, GPIO.FALLING)
            code = on_ir_receive(DATA_PIN)
            if code:
                print(hex(code))

                execute_command(code)
    except KeyboardInterrupt:
        pass
    except RuntimeError:
        pass

    GPIO.cleanup()

