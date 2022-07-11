import paho.mqtt.client as mqtt
import logging
import json
import csv

from services.core.PlatformDriverAgent.platform_driver.interfaces import BaseInterface, BasicRevert, BaseRegister, \
    DriverInterfaceError
from services.core.PlatformDriverAgent.platform_driver.interfaces.rainforesteagle import NetworkStatus

_log = logging.getLogger(__name__)

client = None
data = dict()


class FirstMessage(BaseRegister):
    def __init__(self, read_only, volttron_point_name, string):
        super(FirstMessage, self).__init__("byte", read_only, volttron_point_name, string) # Confused in this area about
                                                                                           # what variables go where in
                                                                                           # relation to the CSV file
    def value(self):
        global data
        return data['FirstMessage'][0]


# Point Name,Volttron Point Name,Units,Units Details,Writable,Starting Value,Type,Notes.

MQTTregister_registers = {'FirstMessage': FirstMessage} # labeled first message


class Interface(BasicRevert, BaseInterface):
    def __init__(self, **kwargs):
        super(Interface, self).__init__(**kwargs)
        self.on_log = None
        self.on_disconnect = None
        self.Broker_address = None

    def configure(self, config_dict, registry_config_str):
        global client

        self.Broker_address = config_dict.get("broker_address")  # From config file (MQTTfake)

        # Connect to MQTT broker.

        client = mqtt.Client(userdata=self)
        client.on_connect = self.on_connect
        client.on_disconnect = self.on_disconnect
        client.on_log = self.on_log
        client.on_message = self.on_message
        print("Connecting to broker ", self.Broker_address)
        client.connect(self.Broker_address)
        client.loop_start()
        client.subscribe("house/sensor1")
        client.publish("house/sensor1", "my first message")
        # time.sleep(4)
        # client.loop_stop()
        # client.disconnect()

        # Adding 11:31 register stuff
        if registry_config_str is None:
            registry_config_str = []
        # ADDED 11:15am 7/8
        for name in registry_config_str:
            register = MQTTregister_registers[name]
            self.insert_register(register())

        # for name in register_config:
        #     register = cta2045_registers[name]
        #     self.insert_register(register())

        # Network Status register (in progress)

        try:
            self.get_register_by_name('NetworkStatus')
        except DriverInterfaceError:
            self.insert_register(NetworkStatus())

    def get_point(self, point_name, **kwargs):
        register = self.get_register_by_name(point_name)
        return register.value()
    print("GotPoint")

    def _set_point(self, point_name, value):
        register = self.get_register_by_name(point_name)
        if register.read_only:
            raise IOError(
                "trying to write point read only" + point_name)

        register.set_value(value)
        return register.value

    # Fake Driver Example Scrape All
    def _scrape_all(self):
        result = {}
        read_registers = self.get_registers_by_type("byte", True)
        write_registers = self.get_registers_by_type("byte", False)
        for register in read_registers + write_registers:
            result[register.point_name] = register.value

        return result

    # def on_log(self, client, userdata, level, buf):
    #     print("log: " + buf)
    #
    @staticmethod
    def _on_mqtt_connect(client, data, flags, rc):
        data._on_connect(client, flags, rc)

    @staticmethod
    def _on_mqtt_message(client, data, msg):
        data._on_message(client, msg)

    def on_connect(self, client, userdata, flags, rc):
        _log.info('Connected to MQTT broker ({0})'.format(rc))
        # if rc == 0:
        #     print("Connected ok")
        # else:
        #     print("connection failed retuend code==", rc)

    # def on_disconnect(self, client, userdata, flags, rc=0):
    #     print("disConnected result code " + str(rc))

    # SENDING MESSAGES TO DATA DICTIONARY

    def on_message(self, client, userdata, msg):
        global data
        _log.info('Received "{0}" on "{1}"'.format(msg.payload, msg.topic))
        doc = json.loads(msg.payload)  # storing message
        data = doc

