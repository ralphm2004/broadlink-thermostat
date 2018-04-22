#!/usr/bin/env python
# -*- coding: utf-8 -*
from multiprocessing import Process, Lock, Pipe
import multiprocessing, argparse, time, datetime, sys, os, signal, traceback, socket, sched, atexit
import paho.mqtt.client as mqtt  # pip install paho-mqtt
import broadlink  # pip install broadlink
import json  # pip install json
HAVE_TLS = True
try:
    import ssl
except ImportError:
    HAVE_TLS = False

dirname = os.path.dirname(os.path.abspath(__file__)) + '/'
CONFIG = os.getenv('BROADLINKMQTTCONFIG', dirname + 'broadlink-thermostat.conf')

class Config(object):
    def __init__(self, filename=CONFIG):
        self.config = {}
        self.config['ca_certs']     = None
        self.config['tls_version']  = None
        self.config['certfile']     = None
        self.config['keyfile']      = None
        self.config['tls_insecure'] = False
        self.config['tls']          = False
        execfile(filename, self.config)

        if HAVE_TLS == False:
            logging.error("TLS parameters set but no TLS available (SSL)")
            sys.exit(2)

        if self.config.get('ca_certs') is not None:
            self.config['tls'] = True

        if self.config.get('tls_version') is not None:
            if self.config.get('tls_version') == 'tlsv1':
                self.config['tls_version'] = ssl.PROTOCOL_TLSv1
            if self.config.get('tls_version') == 'tlsv1.2':
                # TLS v1.2 is available starting from python 2.7.9 and requires openssl version 1.0.1+.
                if sys.version_info >= (2,7,9):
                    self.config['tls_version'] = ssl.PROTOCOL_TLSv1_2
                else:
                    logging.error("TLS version 1.2 not available but 'tlsv1.2' is set.")
            	    sys.exit(2)
            if self.config.get('tls_version') == 'sslv3':
                self.config['tls_version'] = ssl.PROTOCOL_SSLv3

    def get(self, key, default='special empty value'):
        v = self.config.get(key, default)
        if v == 'special empty value':
            logging.error("Configuration parameter '%s' should be specified" % key)
            sys.exit(2)
        return v
        
def unhandeledException(e):
    trace = open('/tmp/transfer-unhandled-exception.log', 'w+')
    traceback.print_exc(None, trace)
    trace.close()

class ReadDevice(Process):
    def __init__(self, pipe, divicemac, device, conf):
        super(ReadDevice, self).__init__()
        self.pipe         = pipe
        self.divicemac    = divicemac
        self.device       = device
        self.conf         = conf


    def run(self):
        print('PID child %d' % os.getpid())
        mqttc= mqtt.Client(self.conf.get('mqtt_clientid', 'broadlink')+'-%s-%s' % (self.divicemac,os.getpid()), clean_session=self.conf.get('mqtt_clean_session', False))
        mqttc.will_set('%s/%s'%(self.conf.get('mqtt_topic_prefix', '/broadlink'), self.divicemac), payload="Disconnect", qos=self.conf.get('mqtt_qos', 0), retain=False)
        mqttc.reconnect_delay_set(min_delay=3, max_delay=30)
        if self.conf.get('tls') == True:
            mqttc.tls_set(self.conf.get('ca_certs'), self.conf.get('certfile'), self.conf.get('keyfile'), tls_version=self.conf.get('tls_version'), ciphers=None)
        if self.conf.get('tls_insecure'):
            mqttc.tls_insecure_set(True)
        mqttc.username_pw_set(self.conf.get('mqtt_username'), self.conf.get('mqtt_password'))
        mqttc.connect(self.conf.get('mqtt_broker', 'localhost'), int(self.conf.get('mqtt_port', '1883')), 60)
        mqttc.loop_start()
        try:
            if self.device.auth():
                self.run = True
                print self.device.type
                now=datetime.datetime.now()
                # set device time
                self.device.set_time(now.hour, now.minute, now.second, now.weekday()+1)
                print('set time %d:%d:%d %d' % (now.hour, now.minute, now.second, now.weekday()+1))
                # set auto_mode = 0, loop_mode = 0 ("12345,67")
                self.device.set_mode(self.conf.get('auto_mode', 0), self.conf.get('loop_mode', 0))
                # set device on, remote_lock off
                self.device.set_power(1, self.conf.get('remote_lock', 0))
            else:
                self.run = False
            while self.run:
                try:
                    if self.pipe.poll(self.conf.get('loop_time', 60)):
                        result = self.pipe.recv()
                        if type(result) == tuple and len(result) == 2:
                            (cmd, opts) = result
                            if cmd=='set_temp' and float(opts)>0:
                                self.device.set_temp(float(opts))
                            elif cmd=='set_mode':
                                self.device.set_mode(0 if int(opts) == 0 else 1, self.conf.get('loop_mode', 0))
                            elif cmd=='set_power':
                                self.device.set_power(0 if int(opts) == 0 else 1, self.conf.get('remote_lock', 0))
                            elif cmd=='switch_to_auto':
                                self.device.switch_to_auto()
                            elif cmd=='switch_to_manual':
                                self.device.switch_to_manual()
                            elif cmd=='set_schedule':
                                try:
                                    schedule=json.loads(opts)
                                    self.device.set_schedule(schedule[0],schedule[1])
                                except Exception, e:
                                    pass
                        else:
                            if result == 'STOP':
                                self.shutdown()
                                mqttc.loop_stop()
                                return
                    else:
                        try:
                            data = self.device.get_full_status()
                        except socket.timeout:
                            mqttc.loop_stop()
                            return
                        except Exception, e:
                            unhandeledException(e)
                            mqttc.loop_stop()
                            return
                        for key in data:
                            if type(data[key]).__name__ == 'list':
                                mqttc.publish('%s/%s/%s'%(self.conf.get('mqtt_topic_prefix', '/broadlink'), self.divicemac, key), json.dumps(data[key]), qos=self.conf.get('mqtt_qos', 0), retain=self.conf.get('mqtt_retain', False))
                                pass
                            else:
                                if key == 'room_temp':
                                    print "  {} {} {}".format(self.divicemac, key, data[key])
                                mqttc.publish('%s/%s/%s'%(self.conf.get('mqtt_topic_prefix', '/broadlink'), self.divicemac, key), data[key], qos=self.conf.get('mqtt_qos', 0), retain=self.conf.get('mqtt_retain', False))
                        mqttc.publish('%s/%s/%s'%(self.conf.get('mqtt_topic_prefix', '/broadlink'), self.divicemac, 'schedule'), json.dumps([data['weekday'],data['weekend']]), qos=self.conf.get('mqtt_qos', 0), retain=self.conf.get('mqtt_retain', False))
                except Exception, e:
                    unhandeledException(e)
                    mqttc.loop_stop()
                    return
            mqttc.loop_stop()
            return

        except KeyboardInterrupt:
            mqttc.loop_stop()
            return

        except Exception, e:
            unhandeledException(e)
            mqttc.loop_stop()
            return

def main():
    try:
        conf = Config()
    except Exception, e:
        print "Cannot load configuration from file %s: %s" % (CONFIG, str(e))
        sys.exit(2)

    jobs = []
    pipes = []
    founddevices = {}
    
    def on_message(client, pipes, msg):
        cmd = msg.topic.split('/')
        devicemac = cmd[2]
        command = cmd[4]
        if cmd[3] == 'cmd':
            try:
                for (ID, pipe) in pipes:
                    if ID==devicemac:
                        print 'send to pipe %s' % ID
                        pipe.send((command, msg.payload))
            except:
                print "Unexpected error:", sys.exc_info()[0]
                raise

    def on_disconnect(client, empty, rc):
        print("Disconnect, reason: " + str(rc))
        print("Disconnect, reason: " + str(client))
        client.loop_stop()
        time.sleep(10)
        
    def on_kill(mqttc, jobs):
        mqttc.loop_stop()
        for j in jobs:
            j.join()

    def on_connect(client, userdata, flags, rc):
        client.publish(conf.get('mqtt_topic_prefix', '/broadlink'), 'Connect')
        print("Connect, reason: " + str(rc))

    def on_log(mosq, obj, level, string):
        print(string)

    mqttc = mqtt.Client(conf.get('mqtt_clientid', 'broadlink')+'-%s'%os.getpid(), clean_session=conf.get('mqtt_clean_session', False), userdata=pipes)
    mqttc.on_message = on_message
    mqttc.on_connect = on_connect
    mqttc.on_disconnect = on_disconnect
    #mqttc.on_log = on_log
    mqttc.will_set(conf.get('mqtt_topic_prefix', '/broadlink'), payload="Disconnect", qos=conf.get('mqtt_qos', 0), retain=False)
    mqttc.reconnect_delay_set(min_delay=3, max_delay=30)
    if conf.get('tls') == True:
        mqttc.tls_set(conf.get('ca_certs'), conf.get('certfile'), conf.get('keyfile'), tls_version=conf.get('tls_version'), ciphers=None)
    if conf.get('tls_insecure'):
        mqttc.tls_insecure_set(True)
    mqttc.username_pw_set(conf.get('mqtt_username'), conf.get('mqtt_password'))
    mqttc.connect(conf.get('mqtt_broker', 'localhost'), int(conf.get('mqtt_port', '1883')), 60)
    mqttc.subscribe(conf.get('mqtt_topic_prefix', '/broadlink') + '/+/cmd/#', qos=conf.get('mqtt_qos', 0))

    atexit.register(on_kill, mqttc, jobs)
    
    run = True
    while run:
        try:
            for idx, j in enumerate(jobs):
                if not j.is_alive():
                    try:
                        j.join()
                    except:
                        pass
                    try:
                        del founddevices[j.pid]
                    except:
                        pass
                    try:
                        del jobs[idx]
                    except:
                        pass
            print "broadlink discover"
            devices = broadlink.discover(timeout=conf.get('lookup_timeout', 5))
            for device in devices:
                divicemac = ''.join(format(x, '02x') for x in device.mac)
                if divicemac not in founddevices.values():
                    transportPipe, MasterPipe = Pipe()
                    pipes.append((divicemac, MasterPipe))

                    print "found: {} {}".format(device.host[0], ''.join(format(x, '02x') for x in device.mac))
                    p = ReadDevice(transportPipe, divicemac, device, conf)
                    jobs.append(p)
                    p.start()
                    founddevices[p.pid] = divicemac
                    time.sleep(2)
            mqttc.user_data_set(pipes)
            mqttc.loop_stop()
            print "Reconnect"
            mqttc.loop_start()
            time.sleep(conf.get('rediscover_time', 600))
        except KeyboardInterrupt:
            run = False
        except Exception, e:
            run = False
            unhandeledException(e)
        except SignalException_SIGKILL:
            run = False

    mqttc.loop_stop()
    for j in jobs:
        j.join()
    return

main()
