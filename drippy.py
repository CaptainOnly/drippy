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

# Back end should be a zone id (green), and an on/off routine
# (RPi/GPIO)

import cherrypy
import HTML
import RPi.GPIO
from datetime import datetime
from cherrypy.process.plugins import Monitor
from datetime import date, datetime, timedelta

def time_to_gallons(time):
    # ...at 8gph
    return round(8 * ((time.seconds / 3600.0) + (time.days * 24)), 2)

def time_to_inches(time):
    # ...at 31 gallons per inch
    return round(time_to_gallons(time) / 31, 2)

def inches_to_time(inches):
    # ...at 31 gallons per inch, 8gph
    return timedelta(hours=inches * 31 / 8)

def drip_times(color, daily=False):
    times = {}

    def time_insert(when, how_long):
        key_Y = when.strftime("%Y")
        key_m = when.strftime("%m")
        key_d = when.strftime("%d")

        if not key_Y in times:
            times[key_Y] = {}
            
        if not key_m in times[key_Y]:
            times[key_Y][key_m] = {} if daily else timedelta(0)

        if daily:
            if not key_d in times[key_Y][key_m]:
                times[key_Y][key_m][key_d] = timedelta(0)

            times[key_Y][key_m][key_d] += how_long
        else:
            times[key_Y][key_m] += how_long
            
    with open('drippy.log', 'r') as f:
        on_state = False
        on_dtime = None

        for line in f:
            line_color, line_op, line_ctime = line.split(None, 2)
            line_dtime = datetime.strptime(line_ctime, "%a %b %d %H:%M:%S %Y\n")

            if color == line_color:
                if on_state and line_op == 'Off':
                    time_insert(line_dtime, line_dtime - on_dtime)
                    on_state = False

                elif not on_state and line_op == 'On':
                    on_dtime = line_dtime
                    on_state = True

        if on_state:
            now_dtime = datetime.now().replace(microsecond=0)
            time_insert(now_dtime, now_dtime - on_dtime)

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
        elif self.GRN_STATE is False:
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

    def green_control(self, OnOff=None, OnSelect=None, OnParam=None):
        if OnOff=="ON":
            RPi.GPIO.output(self.GRN_GPIO, RPi.GPIO.HIGH)

            with open('drippy.log', 'a') as f:
                f.write("Green On " + datetime.now().ctime() + "\n")

            if OnSelect=='2':
                self.GRN_STATE = 2 * 3600
            elif OnSelect=='4':
                self.GRN_STATE = 4 * 3600
            elif OnSelect=='x':
                self.GRN_STATE = int(float(OnParam) * 3600)
            else:
                days_to_go, inches, time = self.history()
                self.GRN_STATE = inches_to_time(0.75 - inches).seconds

        else:
            RPi.GPIO.output(self.GRN_GPIO, RPi.GPIO.LOW)

            with open('drippy.log', 'a') as f:
                f.write("Green Off " + datetime.now().ctime() + "\n")

            self.GRN_STATE = False

    def green_table(self):

        times = drip_times("Green")

        table_data = [['year', 'month', 'h:mm:ss', 'gallons (@ 8GPH)', "inches (over 8' circle)"]]

        for Y in sorted(times.iterkeys(), reverse=True):
            for m in sorted(times[Y].iterkeys(), reverse=True):
                time = times[Y][m]
                gallons = time_to_gallons(time)
                inches  = time_to_inches(time)
                table_data.append( [Y, m, time, gallons, inches] )

        return HTML.table(table_data)

    def history(self):
        # Update the schedule
        #
        # Each week, catch up on any deficit for the previous
        # month. That requires looking at the log, and determining how
        # many inches we need to be at target. It useful to see what's
        # coming, so this is written to make a prediction.

        # Our watering day is Thursday (3). How many days to go until thursday?
        
        days_to_go = { 0: 3, 1: 2, 2: 1, 3: 0, 4: 6, 5: 5, 6: 4 }[date.today().weekday()]

        # How much water has been lain over 30 previous days to next
        # scheduled date?

        times = drip_times("Green", daily=True)

        total_time = timedelta(0)

        for day in range(30):
            when = date.today() + timedelta(days = days_to_go) - timedelta(days = day)
            Y = when.strftime("%Y")
            m = when.strftime("%m")
            d = when.strftime("%d")
            
            if Y in times:
                if m in times[Y]:
                    if d in times[Y][m]:
                        total_time += times[Y][m][d]

        return (days_to_go, round(time_to_inches(total_time), 2), total_time)

    def green_schedule(self):
        days_to_go, inches, time = self.history()

        result = ""

        if days_to_go > 0:
            result += "In %d days, the previous 30 days will total " % days_to_go
        else:
            result += "The previous 30 days total "

        return result + "%f inches (%s). The deficit will be %f." % (inches, time, 3.0 - inches)

    def index(self):
        f = open("drippy.html")
        drippy_html = f.read()
        f.close
        return drippy_html

    green.exposed = True
    green_control.exposed = True
    green_table.exposed = True
    green_schedule.exposed = True
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

