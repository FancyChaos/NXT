#!/usr/bin/env python
# -*- coding: utf-8 -*-

import nxt.locator
import thread
from nxt.motor import *
from nxt.sensor import *

import thread
import threading
import time

import random
import sys

# joystick support
import pygame

from lib.nxt_player import Nxt_Player
from lib.nxt_pad import PadController
from lib.nxt_autopilot import AutoPilot

class ScoutRobo(object):

    '''
    ScoutRobo is a python class to control a lego-nxt robot by using bluetooth
    or usb connection.
    '''

    def __init__(self, **kwargs):

        '''
        initialize robot. by default robot is found using bluetooth,
        remember to install bluetooth lib before usage!
        '''

        # get config from keyword-arguments, default-value after comma
        self.bluetooth_only = kwargs.get('bluetooth_only', True)
        self.cannon = kwargs.get('cannon', False)
        self.pad_mode = kwargs.get('pad', False)
        self.autopilot_mode = kwargs.get('autopilot', False)

        # find brick using locator-method
        if self.bluetooth_only:
            find_brick_method = nxt.locator.Method(usb = False, bluetooth = True)
        else:
            find_brick_method = nxt.locator.Method()

        # magic method-call to find robo
        self.brick = nxt.locator.find_one_brick(method = find_brick_method)

        # initialize basic functions
        self.init_motors()
        self.init_sensors()

        # initialize some useful vars
        self.touch_right = False
        self.touch_left = False

        # locked is used to stop robo from moving when it has collided
        # getting orders from http-server
        self.locked = False

        # player for beeps and stuff
        self.player = Nxt_Player(self.brick)

        # start pad-mode if configured
        if self.pad_mode:
            self.pad_controller = PadController(self)
            return # do not run other modes afterwards!

        # start autopilot-mode if configured
        if self.autopilot_mode:
            self.autopilot = AutoPilot(self)
            return

    def init_motors(self):
        '''
        find and initialize motors from ports of brick
        '''
        self.motor_left = Motor(self.brick, PORT_A)
        self.motor_right = Motor(self.brick, PORT_B)

        # put main motors into list for driving
        self.motors = [self.motor_left, self.motor_right]

        # cannon is not in use for normal setup right now
        if self.cannon:
            # crashes if no motor is connected to port_c!
            self.cannon_motor = Motor(self.brick, PORT_C)

    def init_sensors(self):
        '''
        find and initialize sensors from ports of brick
        '''
        self.sensor_ultrasonic = Ultrasonic(self.brick, PORT_4)
        self.sensor_touch_left = Touch(self.brick, PORT_2)
        self.sensor_touch_right = Touch(self.brick, PORT_1)
        self.sensor_light_color = Color20(self.brick, PORT_3)

    def test(self):
        '''
        use this to test new functions n' shit
        '''
        print 'testing...'
        while True:
            try:
                val = self.sensor_light_color.get_sample()
                print val
            except KeyboardInterrupt:
                break

    def get_telemetry(self):
        '''
        method to acquire sensor data, called e.g. by external modules
        '''

        telemetry = {
            'touch_left' : self.sensor_touch_left.get_sample(),
            'touch_right' : self.sensor_touch_right.get_sample(),
            'distance' : self.sensor_ultrasonic.get_sample(),
            'color' : self.sensor_light_color.get_sample()
        }

        return telemetry

    def check_color(self):
        '''
        check if underground has white color (= 6)
        '''

        val = self.sensor_light_color.get_sample()
        if val == 5:
            return True
        else:
            return False

    def check_collision(self):
        '''
        check touch and ultrasonic sensors to detect collisions
        '''
        self.touch_left = self.sensor_touch_left.get_sample()
        self.touch_right = self.sensor_touch_right.get_sample()

        if self.touch_left or self.touch_right:
            return True

        # also check ultrasonic here, its useful if robo drives straight
        # forward towards a wall, so touch sensors cant detect collision
        self.distance = self.sensor_ultrasonic.get_sample()
        if self.distance < 6:
            return True

        return False

    def timed_checks(self, ftime):
        '''
        timed collision and color checks done while robo is moving
        '''

        # count times color sensor detects goal color
        color_times = 0

        # color sensor can be a little fuzzy, so one detection does not
        # neccessarily mean "goal reached"
        color_times_limit = 3

        # TODO: reset counter after certain amount of time!

        start = time.time()
        while True:
            now = time.time()
            if (now - start) > ftime:
                break
            if self.check_collision():
                self.stop()
                if not self.player.playing_song:
                    self.player.play_song('fail')
                # self.locked = True
                break
            if self.check_color():
                color_times += 1
                if color_times > color_times_limit:
                    self.stop()
                    if not self.player.playing_song:
                        self.player.play_song('success')
                    # self.locked = True
                    break

        return

    def unlock(self):
        '''
        robo is locked when it collides. unlock is called by nxt-control app
        '''
        self.locked = False

    def go_forward_forever(self, power = 80):
        for motor in self.motors:
            motor.run(power)

    def go_backward_forever(self, power = 80):
        for motor in self.motors:
            motor.run(-power)

    def stop(self):
        for motor in self.motors:
            motor.idle()

    def go_forward(self, power=80, ftime=1):
        if self.locked:
            return
        for motor in self.motors:
            motor.run(power)

        self.timed_checks(ftime)

        for motor in self.motors:
            motor.idle()

    def go_backward(self, power=80, ftime=1):
        if self.locked:
            return
        for motor in self.motors:
            motor.run(-power)

        self.timed_checks(ftime)

        for motor in self.motors:
            motor.idle()

    def turn_left(self, power=80, ftime=1):
        if self.locked:
            return
        for motor in self.motors:
            if motor == self.motor_left:
                motor.run(-power)
            elif motor == self.motor_right:
                motor.run(power)

        self.timed_checks(ftime)

        for motor in self.motors:
            motor.idle()

    def turn_right(self, power=80, ftime=1):
        if self.locked:
            return
        for motor in self.motors:
            if motor == self.motor_left:
                motor.run(power)
            elif motor == self.motor_right:
                motor.run(-power)

        self.timed_checks(ftime)

        for motor in self.motors:
            motor.idle()

    def turn_right_forever(self, power=80):
        for motor in self.motors:
            if motor == self.motor_left:
                motor.run(power)
            elif motor == self.motor_right:
                motor.run(-power)

    def turn_left_forever(self, power=80):
        for motor in self.motors:
            if motor == self.motor_left:
                motor.run(-power)
            elif motor == self.motor_right:
                motor.run(power)

    def fire_cannon(self, balls=1):
        self.cannon_motor.turn(127,360*balls)
        self.cannon_motor.idle()

if __name__ == '__main__':
    robo = ScoutRobo(pad = True)
    #robo.test()
    if len(sys.argv) > 1:
        mode = sys.argv[1]
    else:
        mode = None
    if mode == 'run':
        try:
            robo.running = True
            robo.run()
        except Exception as e:
            print e
            print 'run-mode died'
            robo.stop()
    elif mode == 'test':
        robo.test()
    elif mode == 'pad':
        try:
            robo.pad_controller.run_gamepad()
        except Exception as e:
            print e
            print 'pad-mode died...'
            robo.stop()
