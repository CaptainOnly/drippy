#!/usr/bin/python

# Our little live oak gets water from an 8' diameter area. An inch of
# rain on an 8' circle gives 31 gallons. The tree has 8 1GPH drippers
# which take 4 hours to provide the equivalent of an inch of
# rain. Austin gets 34 inches a year on average, so we'll give our
# tree 3/4 of an inch a week (40 for the year) which is 3 hours of
# watering.
#
# When it rains, we'll take that total off the budget at a rate of
# 4hours/inch. So, if it rains 1 inch, we'll run for 4 hours less.

import cherrypy
import HTML
import RPi.GPIO
from datetime import datetime
from cherrypy.process.plugins import Monitor
from datetime import datetime, timedelta

def drip_times(color):
    times = {}

    with open('drippy.log', 'r') as f:
        on_state = False
        on_dtime = None

        for line in f:
            line_color, line_op, line_ctime = line.split(None, 2)
            line_dtime = datetime.strptime(line_ctime, "%a %b %d %H:%M:%S %Y\n")

            if color == line_color:
                if on_state and line_op == 'Off':
                    on_state = False
                    key = line_dtime.strftime("%Y %m")
                    delta = line_dtime - on_dtime
                    times[key] = delta if not key in times else times[key] + delta
                        
                elif not on_state and line_op == 'On':
                    on_state = True
                    on_dtime = line_dtime

        if on_state:
            dtime = datetime.now()
            key = dtime.strftime("%Y %m")
            delta = dtime - on_dtime
            times[key] = delta if not key in times else times[key] + delta

    return times

class Drippy(object):
    # GPIO names
    XX1_GPIO = 11
    XX2_GPIO = 12
    RED_GPIO = 15
    GRN_GPIO = 13

    # Remember if zone is on or off
    GRN_STATE = False

    def __init__(self):
        RPi.GPIO.setmode(RPi.GPIO.BOARD)

        RPi.GPIO.setup(self.XX1_GPIO, RPi.GPIO.OUT)
        RPi.GPIO.setup(self.XX2_GPIO, RPi.GPIO.OUT)
        RPi.GPIO.setup(self.GRN_GPIO, RPi.GPIO.OUT)
        RPi.GPIO.setup(self.RED_GPIO, RPi.GPIO.OUT)

        RPi.GPIO.output(self.XX1_GPIO, RPi.GPIO.LOW)
        RPi.GPIO.output(self.XX2_GPIO, RPi.GPIO.LOW)
        RPi.GPIO.output(self.GRN_GPIO, RPi.GPIO.LOW)
        RPi.GPIO.output(self.RED_GPIO, RPi.GPIO.LOW)

    def __del__(self):
        RPi.GPIO.output(self.XX1_GPIO, RPi.GPIO.LOW)
        RPi.GPIO.output(self.XX2_GPIO, RPi.GPIO.LOW)
        RPi.GPIO.output(self.GRN_GPIO, RPi.GPIO.LOW)
        RPi.GPIO.output(self.RED_GPIO, RPi.GPIO.LOW)
        
    def run(self):
        if self.GRN_STATE is True:
            pass
        if self.GRN_STATE is False:
            pass
        else:
            try:
                if self.GRN_STATE == 0:
                    self.green_control("OFF");
                else:
                    self.GRN_STATE = self.GRN_STATE - 1
            except:
                self.green_control("OFF");

    def green(self):
        if self.GRN_STATE:
            if self.GRN_STATE is True:
                return "On"
            else:
                try:
                    return "On (for %d seconds)" % self.GRN_STATE
                except:
                    self.green_control("OFF");
                    return "Off"
        else:
            return "Off"

    def green_control(self, OnOff=None, OffDelay=None):
        if OnOff=="ON":
            RPi.GPIO.output(self.GRN_GPIO, RPi.GPIO.HIGH)

            with open('drippy.log', 'a') as f:
                f.write("Green On " + datetime.now().ctime() + "\n")

            if not OffDelay:
                self.GRN_STATE = True
            else:
                try:
                    self.GRN_STATE = int(OffDelay)
                except:
                    self.GRN_STATE = 1

        else:
            RPi.GPIO.output(self.GRN_GPIO, RPi.GPIO.LOW)

            with open('drippy.log', 'a') as f:
                f.write("Green Off " + datetime.now().ctime() + "\n")

            self.GRN_STATE = False

    def green_times(self):
        times = drip_times("Green")

        table_data = []

        for k in sorted(times.iterkeys()):
            table_data.append( [k, times[k]] )

        return HTML.table(table_data)

    def index(self):
        f = open("drippy.html")
        drippy_html = f.read()
        f.close
        return drippy_html

    green.exposed = True
    green_control.exposed = True
    green_times.exposed = True
    index.exposed = True


cherrypy.config.update({'server.socket_host': '192.168.62.149',
                        'server.socket_port': 80,
                       })

drippy = Drippy()

# This calls the run() method on drippy once a second. I have no idea
# why this works, but it does.
# 
# http://stackoverflow.com/questions/9207591/cherrypy-with-additional-threads-for-custom-jobs
#
Monitor(cherrypy.engine, drippy.run, frequency=1).subscribe()

cherrypy.quickstart(drippy)

