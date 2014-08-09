#!/usr/bin/python

# MOVE THE LOGGING TO main class. Have main class reload drip times each time log written. 

import os
import HTML
import json
import RPi.GPIO
import cherrypy
from cherrypy.process.plugins import Monitor
from cherrypy.lib.static import serve_file
from datetime import datetime, date, timedelta

def drip_times(f, id, daily=False):
    """From file f, return a table of drip times for zone with supplied id"""
 
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
            
    on_state = False
    on_dtime = None
    
    for line in f:
        line_id, line_op, line_ctime = line.split(None, 2)
        line_dtime = datetime.strptime(line_ctime, "%a %b %d %H:%M:%S %Y\n")

        if id == line_id:
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

class DripZone(object):
    # Drippy draws a webpage for a set of DripZones, and allows them
    # to be controlled directly. It also logs events on zones and uses
    # that information to automate them. The DripZone class is all the
    # zone specific methods that drippy needs to accomplish that.

    def __init__(self):
        RPi.GPIO.setup(self.zone_gpio(), RPi.GPIO.OUT)
        self.off()

    def __del__(self):
        self.off()

    # The zone state is number of seconds to be on for.
    STATE = 0
    
    def on(self, seconds):
        
        if not (seconds > 0):
            raise ValueError("On() expects a positive number of seconds")

        log_message = "%s On  %s\n" % (self.zone_id(), datetime.now().ctime())

        try:
            with open('drippy.log', 'a') as f:
                f.write(log_message)
        except:
            cherrypy.log("Couldn't write on time to log file: %s" % log_message)

        else:
            self.STATE = int(seconds)

            RPi.GPIO.output(self.zone_gpio(), RPi.GPIO.HIGH)

    def off(self):
        RPi.GPIO.output(self.zone_gpio(), RPi.GPIO.LOW)

        log_message = "%s Off %s\n" % (self.zone_id(), datetime.now().ctime())

        try:
            with open('drippy.log', 'a') as f:
                f.write(log_message)
        except:
            cherrypy.log("Couldn't write off time to log file: %s" % log_message)

        finally:
            self.STATE = 0

    def run(self):
        # Drippy calls this method for each zone once per
        # second. Zones use this to automate their execution

        if self.STATE > 0:
            self.STATE -= 1
            
            if self.STATE == 0:
                self.off()

        elif self.STATE == 0:
            on_time = self.zone_check_schedule()

            if on_time > 0:
                self.on(on_time)

    def state(self):
        if self.STATE > 0:
            return "on (for %d seconds more)" % self.STATE

        elif self.STATE == 0:
            return "off"

        else:
            return "xx %s" % self.STATE

    def table(self):

        table_data = [['year', 'month', 'h:mm:ss', 'gallons', "inches"]]
            
        with open('drippy.log', 'r') as f:
            times = drip_times(f, self.zone_id())

            for Y in sorted(times.iterkeys(), reverse=True):
                for m in sorted(times[Y].iterkeys(), reverse=True):
                    time = times[Y][m]
                    gallons = self.time_to_gallons(time)
                    inches  = self.time_to_inches(time)
                    table_data.append( [Y, m, time, gallons, inches] )

        return HTML.table(table_data)

    def history(self):
        # How much water has been lain over 30 previous days?

        with open('drippy.log', 'r') as f:
            times = drip_times(f, self.zone_id(), daily=True)

        total_time = timedelta(0)

        for day in range(30):
            when = date.today() - timedelta(days = day)
            Y = when.strftime("%Y")
            m = when.strftime("%m")
            d = when.strftime("%d")
            
            if Y in times:
                if m in times[Y]:
                    if d in times[Y][m]:
                        total_time += times[Y][m][d]

        inches, time = round(self.time_to_inches(total_time), 2), total_time

        result = "The previous 30 days total %f inches (%s)." % (inches, time)

        next_time = self.zone_next_schedule()

        if next_time:
            result += " Next drip time is %s." % (next_time.ctime())

        return result

class Green(DripZone):
    # Our little live oak gets water from an 8' diameter area. An inch of
    # rain on an 8' circle gives 31 gallons. The tree has 8 1GPH drippers
    # which take 4 hours to provide the equivalent of an inch of
    # rain. Austin gets 34 inches a year on average, so we'll give our
    # tree 3/4 of an inch a week (40 for the year) which is 3 hours of
    # watering.
    #
    # When it rains, we'll take that total off the budget at a rate of
    # 4hours/inch. So, if it rains 1 inch, we'll run for 4 hours less.
    
    def zone_id(self):
        return "Green"

    def zone_name(self):
        return "Landscape"

    def zone_gpio(self):
        return 13

    def zone_next_schedule(self):
        # Our watering day is Thursday (3). We water at 5am.

        # How many days to go until thursday?
        days_to_go = { 0: 3, 1: 2, 2: 1, 3: 0, 4: 6, 5: 5, 6: 4 }[date.today().weekday()]

        now = datetime.now().replace(microsecond = 0)

        next_schedule = datetime.now().replace(hour = 5, minute = 0, second = 0, microsecond = 0) + timedelta(days = days_to_go)
        
        if days_to_go == 0 and now > next_schedule:
            next_schedule += timedelta(days = 7)

        return next_schedule
        #return 0

    def zone_check_schedule(self):
        # We water for 3 hours

        now = datetime.now().replace(microsecond = 0)
        then = self.zone_next_schedule()

        if now == then:
            return 3 * 3600
        else:
            return 0

    def zone_gph(self):
        # gallons per hour while running
        return 8

    def zone_gpi(self):
        # number of gallons for the equivalent of an inch of rain
        #
        # this is based on 8 1gph drippers on an 8' circumerence
        # circle which is what we put on the small live oak we planted
        return 31

    def time_to_gallons(self, time):
        # Drippy works in time. This method turns time into gallons of
        # water dripped for this zone.
        return round(self.zone_gph() * ((time.seconds / 3600.0) + (time.days * 24)), 2)

    def time_to_inches(self, time):
        # Drippy works in time. This method turns time into equivalent
        # inches of rain for this zone.
        return round(self.time_to_gallons(time) / self.zone_gpi(), 2)


class Red(DripZone):
    
    def zone_id(self):
        return "Red"

    def zone_name(self):
        return "Garden"

    def zone_gpio(self):
        return 15

    def zone_next_schedule(self):
        # We water every day at 5am.

        next_schedule = datetime.now().replace(hour = 5, minute = 0, second = 0, microsecond = 0)

        if datetime.now() > next_schedule:
            next_schedule += timedelta(days = 1)

        return next_schedule

    def zone_check_schedule(self):
        if datetime.now().replace(microsecond = 0) == self.zone_next_schedule():
            return 0
        else:
            return 0

    def zone_gph(self):
        # gallons per hour while running
        return 8

    def zone_gpi(self):
        # number of gallons for the equivalnet of an inch of rain
        return 31

    def time_to_gallons(self, time):
        # Drippy works in time. This method turns time into gallons of
        # water dripped for this zone.
        return round(self.zone_gph() * ((time.seconds / 3600.0) + (time.days * 24)), 2)

    def time_to_inches(self, time):
        # Drippy works in time. This method turns time into equivalent
        # inches of rain for this zone.
        return round(self.time_to_gallons(time) / self.zone_gpi(), 2)

class XX1(DripZone):
    
    def zone_id(self):
        return "XX1"

    def zone_name(self):
        return "XX1"

    def zone_gpio(self):
        return 11

class XX2(DripZone):
    
    def zone_id(self):
        return "XX2"

    def zone_name(self):
        return "XX2"

    def zone_gpio(self):
        return 12

class Drippy(object):
    # This is the main class for the web UI.

    def __init__(self, zones):
        self.zones = { }

        for z in zones:
            self.zones[ z.zone_id() ] = z;

    def index(self):
        return serve_file(os.path.abspath("drippy.html"))

    def main_script(self):
        return serve_file(os.path.abspath("drippy.js"), "application/javascript")

    def run(self):
        # Call the run method on each zone, passing them the information they need
        for k in self.zones.keys():
            self.zones[k].run()

    def zone_list(self):
        # Return a list of zone names that can be passed to the other methods
        zl = []

        for k in self.zones.keys():
            zl.append({ 'ID' : k, 'Name' : self.zones[k].zone_name() })

        return json.dumps(zl)

    def zone_state(self, ID):
        # Get the state of the zone as a string
        return self.zones[ID].state()

    def zone_control(self, ID, OnOff=None, OnSelect=None, OnParam=None):

        if OnOff=="ON":

            on_seconds = 0

            if OnSelect=='2':
                on_seconds = 2 * 3600
            elif OnSelect=='4':
                on_seconds = 4 * 3600
            elif OnSelect=='x':
                on_seconds = int(float(OnParam) * 3600)

            self.zones[ID].on(on_seconds)

        else:
            self.zones[ID].off()

    def zone_table(self, ID):
        return self.zones[ID].table()

    def zone_history(self, ID):
        return self.zones[ID].history()

    index.exposed = True
    main_script.exposed = True
    zone_list.exposed = True
    zone_state.exposed = True
    zone_control.exposed = True
    zone_table.exposed = True
    zone_history.exposed = True


# Have to use stptime to ensure it's available in threads
datetime.strptime("Sun Aug 31 20:44:50 2012", "%a %b %d %H:%M:%S %Y")

# GPIO on the RaspberryPy can be addressed as board resources or
# something else
RPi.GPIO.setmode(RPi.GPIO.BOARD) 
    
# Not sure why I need this
cherrypy.config.update({'server.socket_host': '192.168.62.149',
                        'server.socket_port': 80,
                       })

# Create zones and assign IDs for them
drippy = Drippy( [Green(), Red()] )

# This calls the run() method on drippy once a second. I have no idea
# how/why this works, but it does.
# 
# http://stackoverflow.com/questions/9207591/cherrypy-with-additional-threads-for-custom-jobs
#
Monitor(cherrypy.engine, drippy.run, frequency=1).subscribe()

# Finally, start the web server
cherrypy.quickstart(drippy)

