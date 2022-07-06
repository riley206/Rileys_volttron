import paho.mqtt.client as mqtt
import time

from platform_driver.interfaces import BaseInterface, BasicRevert

data = dict()

class Interface(BasicRevert, BaseInterface):
    def __init__(self, **kwargs):
        super(Interface, self).__init__(**kwargs)

    def configure(self, config_dict, registry_config_str):
        self.parse_config(registry_config_str)

    def get_point(self, point_name):
        register = self.get_register_by_name(point_name)

        return register.value

    def _set_point(self, point_name, value):
        register = self.get_register_by_name(point_name)
        if register.read_only:
            raise RuntimeError(
                "Trying to write to a point configured read only: " + point_name)
        
    def on_log(client, userdata, level, buf):
        print("log: "+buf)

    def on_connect(client, userdata, flags, rc):
        if rc==0:
            print("Connected ok")
        else:
            print("connection failed retuend code==",rc)
    def on_disconnect(client, userdata, flags, rc=0):
        print("disConnected result code "+str(rc))

    def on_message(client, userdata, msg):
            topic=msg.topic
            m_decode=str(msg.payload.decode("utf-8","ignore"))
            print("message received",m_decode)
    broker="130.20.99.141"
    client = mqtt.Client("P1")

    client.on_connect=on_connect
    client.on_disconnect=on_disconnect
    client.on_log=on_log
    client.on_message=on_message

    print("conecting to broker ",broker)

    client.connect(broker)
    client.loop_start()
    client.subscribe("house/sensor1")
    client.publish("house/sensor1","my first message")

    time.sleep(4)
    client.loop_stop()
    client.disconnect()
    


    

