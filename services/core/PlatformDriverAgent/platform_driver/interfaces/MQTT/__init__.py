import paho.mqtt.client as mqtt
import logging
import json
import csv
import time

from services.core.PlatformDriverAgent.platform_driver.interfaces import BaseInterface, BasicRevert, BaseRegister, \
    DriverInterfaceError
from services.core.PlatformDriverAgent.platform_driver.interfaces.rainforesteagle import NetworkStatus

_log = logging.getLogger(__name__)
type_mapping = {"string": str,
                "int": int,
                "integer": int,
                "float": float,
                "bool": bool,
                "boolean": bool}

client = None
data = dict()


class FirstMessage(BaseRegister):
    def __init__(self, read_only, pointName, units, reg_type, register_type, default_value=None, description=''):
        #     register_type, read_only, pointName, units, description = ''):
        super(FirstMessage, self).__init__("byte", read_only, pointName, units,
                                           description='')
        super().__init__(register_type, read_only, pointName, units, description)
        self.reg_type = reg_type                                                                                 # what variables go where in
                                                                                         # relation to the CSV file



# Point Name,Volttron Point Name,Units,Units Details,Writable,Starting Value,Type,Notes.

#MQTTregister_registers = {'FirstMessage': FirstMessage} # labeled first message


class Interface(BasicRevert, BaseInterface):
    def __init__(self, **kwargs):
        super(Interface, self).__init__(**kwargs)
        self.on_log = None
        self.on_disconnect = None
        self.Broker_address = None

    def configure(self, config_dict, registry_config_str):
        self.parse_config(registry_config_str)
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
        client.subscribe("devices/fake-campus/fake-building/MQTT")
        client.publish("devices/fake-campus/fake-building/MQTT", "my first message")

        # time.sleep(4)
        #client.loop_stop()
        # client.disconnect()

        # Adding 11:31 register stuff
        # if registry_config_str is None:
        #     registry_config_str = []
        # # ADDED 11:15am 7/8
        # for _ in registry_config_str:
        #     register = MQTTregister_registers['FirstMessage']
        #     self.insert_register(register())

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
        if rc == 0:
            _log.info('Connected to MQTT broker ({0})'.format(self.Broker_address))
        else:
            print("connection failed returned code==", rc)

    # def on_disconnect(self, client, userdata, flags, rc=0):
    #     print("disConnected result code " + str(rc))

    # SENDING MESSAGES TO DATA DICTIONARY
    def on_message(self, client, userdata, msg):
        global config_dict, CSVfile
        topic =msg.topic
        m_decode=str(msg.payload.decode("utf-8", "ignore"))
        data = m_decode
        print("just printing, what are you doing with this data?", "M_decode: " + m_decode, msg.topic, "Data: " + data)
        self.vip.pubsub.publish('MQTT', "devices/fake-campus/fake-building/MQTT", message= m_decode)


    def parse_config(self, configDict):
        if configDict is None:
            return

        for regDef in configDict:
            read_only = regDef['Writable'].lower() != 'true'
            point_name = regDef['Volttron Point Name']
            description = regDef.get('Notes', '')
            units = regDef['Units']
            default_value = regDef.get("Starting Value", 'sin').strip()
            if not default_value:
                default_value = None
            type_name = regDef.get("Type", 'string')
            reg_type = type_mapping.get(type_name, str)
            print("Hello")
            register_type = FirstMessage

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



