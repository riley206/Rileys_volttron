

import random
import datetime
import math
from math import pi
import time
import csv
import _csv

from services.core.PlatformDriverAgent.platform_driver.interfaces import BaseInterface, BaseRegister, BasicRevert
from io import StringIO
import logging
import paho.mqtt.client as mqtt
import sqlite3

_log = logging.getLogger(__name__)
type_mapping = {"string": str,
                "int": int,
                "integer": int,
                "float": float,
                "bool": bool,
                "boolean": bool}

mqtt_client = None

class FirstMessage(BaseRegister):
    def __init__(self, read_only, pointName, units, reg_type,
                 default_value=None, description=''):
        super(FirstMessage, self).__init__("byte", read_only, pointName, units,
                                          description='')
        global msg, mqtt_client, m_decode

        self.reg_type= reg_type
        self.value = m_decode
        print("is this working?: " + m_decode)


class FakeRegister(BaseRegister):
    def __init__(self, read_only, pointName, units, reg_type,
                 default_value=None, description=''):
        #     register_type, read_only, pointName, units, description = ''):
        super(FakeRegister, self).__init__("byte", read_only, pointName, units,
                                           description='')
        self.reg_type = reg_type

        if default_value is None:
            self.value = self.reg_type(random.uniform(0, 100))
        else:
            try:
                self.value = self.reg_type(default_value)
            except ValueError:
                self.value = self.reg_type()


class EKGregister(BaseRegister):
    def __init__(self, read_only, pointName, units, reg_type,
                 default_value=None, description=''):
        super(EKGregister, self).__init__("byte", read_only, pointName, units,
                                          description='')
        self._value = 1;

        math_functions = ('acos', 'acosh', 'asin', 'asinh', 'atan', 'atan2',
                          'atanh', 'sin', 'sinh', 'sqrt', 'tan', 'tanh')
        if default_value in math_functions:
            self.math_func = getattr(math, default_value)
        else:
            _log.error('Invalid default_value in EKGregister.')
            _log.warning('Defaulting to sin(x)')
            self.math_func = math.sin

    @property
    def value(self):
        now = datetime.datetime.now()
        seconds_in_radians = pi * float(now.second) / 30.0

        yval = self.math_func(seconds_in_radians)

        return self._value * yval

    @value.setter
    def value(self, x):
        self._value = x


class Interface(BasicRevert, BaseInterface):
    def __init__(self, **kwargs):
        super(Interface, self).__init__(**kwargs)

    def configure(self, config_dict, registry_config_str):
        self.parse_config(registry_config_str)
        global mqtt_client

        self.Broker_address = config_dict.get("broker_address")  # From config file (MQTTfake)
        # Connect to MQTT broker.

        mqtt_client = mqtt.Client(userdata=self)
        mqtt_client.on_connect = self.on_connect
        # client.on_disconnect = self.on_disconnect
        # client.on_log = self.on_log
        mqtt_client.on_message = self.on_message
        print("Connecting to broker ", self.Broker_address)
        mqtt_client.connect(self.Broker_address)
        mqtt_client.loop_start()
        mqtt_client.subscribe("devices/fake-campus/fake-building/MQTT")
        mqtt_client.publish("devices/fake-campus/fake-building/MQTT", "my first message")





    def get_point(self, point_name, **kwargs):
        register = self.get_register_by_name(point_name)
        return register.value()

    def _set_point(self, point_name, value):
        register = self.get_register_by_name(point_name)
        if register.read_only:
            raise RuntimeError(
                "Trying to write to a point configured read only: " + point_name)

        register.value = register.reg_type(value)
        return register.value

    def _scrape_all(self):
        result = {}
        read_registers = self.get_registers_by_type("byte", True)
        write_registers = self.get_registers_by_type("byte", False)
        for register in read_registers + write_registers:
            result[register.point_name] = register.value

        return result
    @staticmethod
    def _on_mqtt_connect(client, data, flags, rc):
        data._on_connect(client, flags, rc)

    @staticmethod
    def _on_mqtt_message(client, data, msg):
        data._on_message(client, msg)

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            _log.info('Connected to MQTT broker ({0})'.format(self.Broker_address))
        else:
            print("connection failed returned code==", rc)

    # def on_disconnect(self, client, userdata, flags, rc=0):
    #     print("disConnected result code " + str(rc))

    # SENDING MESSAGES TO DATA DICTIONARY
    def on_message(self, client, userdata, msg):
        global config_dict, CSVfile, mqtt_client
        _log.info('Received "{0}" on "{1}"'.format(msg.payload, msg.topic))
        m_decode=str(msg.payload.decode("utf-8", "ignore"))
        #data = m_decode
        print("just printing, what are you doing with this data?", "M_decode: " + m_decode, "MSG.topic " + msg.topic)
        #self.vip.pubsub.publish('pubsub', "devices/fake-campus/fake-building/MQTT", msg.topic, msg.payload)

        self.vip.pubsub.publish("pubsub", msg.topic,
                            headers={"source": msg.topic},
                            message=m_decode)
#goal is to get data into the CSV file
    # def message_handler(self, client, msg, topic):
    #     data = config_dict.get("registry_config")
    #     tnow=time.localtime(time.time())
    #     m = time.asctime(tnow) + " " +topic+" "+msg
    #     data["time"] = tnow
    #     data["topic"] = topic
    #     data["message"] = msg
    #     _log.log(data)

    def parse_config(self, configDict):
        if configDict is None:
            return


        for regDef in configDict:
            # Skip lines that have no address yet.
            if not regDef['Point Name']:
                continue

            read_only = regDef['Writable'].lower() != 'true'
            point_name = regDef['Volttron Point Name']
            description = regDef.get('Notes', '')
            units = regDef['Units']
            default_value = regDef.get("Starting Value", 'sin').strip()
            if not default_value:
                default_value = None
            type_name = regDef.get("Type", 'string')
            reg_type = type_mapping.get(type_name, str)

            register_type = FakeRegister if not point_name.startswith('EKG') else EKGregister

            register = register_type(
                read_only,
                point_name,
                units,
                reg_type,
                default_value=default_value,
                description=description)

            if default_value is not None:
                self.set_default(point_name, register.value)

            self.insert_register(register)
