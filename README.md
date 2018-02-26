# broadlink thermostat with mqtt and openhab

default.items
<pre>Number TS_Room        "Temperature Room  [%.1f °C]"  <temperature>  (Temperatur)
        { mqtt="<[mo:/broadlink/xxxxxx34ea34/room_temp:state:JS(number.js)]" }
Number TS_Room_Set    "Setpoint Room  [%.1f °C]"     <temperature>  (Temperatur)
        { mqtt="<[mo:/broadlink/xxxxxx34ea34/thermostat_temp:state:JS(number.js)], 
          >[mo:/broadlink/xxxxxx34ea34/cmd/set_temp:command:*:default]"}
Switch TS_Room_Activ  "Room is heating"              <switch>       (Temperatur)
        { mqtt="<[mo:/broadlink/xxxxxx34ea34/active:state:MAP(active.map)"}
Switch TS_Room_Mode   "Room Auto-Mode (ON/OFF)"      <switch>       (Temperatur)
        { mqtt="<[mo:/broadlink/xxxxxx34ea34/auto_mode:state:MAP(active.map)],
          >[mo:/broadlink/xxxxxx34ea34/cmd/set_mode:command:*:MAP(active.map)]"}
Switch TS_Room_Power  "Room Power (ON/OFF)"          <switch>       (Temperatur)
        { mqtt="<[mo:/broadlink/xxxxxx34ea34/power:state:MAP(active.map)],
          >[mo:/broadlink/xxxxxx34ea34/cmd/set_power:command:*:MAP(active.map)]"}</pre>

default.sitemap
<pre>Text      item=TS_Room  labelcolor=[TS_Room_Activ==ON="red"]  valuecolor=[>22="orange",>17="green",>5="blue"]
Setpoint  item=TS_Room_Set minValue=5 maxValue=35 step=1
Switch    item=TS_Room_Activ
Switch    item=TS_Room_Mode
Switch    item=TS_Room_Power</pre>

default.rule
<pre>rule "heat_autm_on_TS_Room_Set"
when
  Time cron "0  0  6 ? * MON-FRI *" or
  Time cron "0  0  9 ? * SAT-SUN *" or
  Time cron "0 30 18 ? * MON-FRI *" or
  Time cron "0 30 18 ? * SAT-SUN *"
then
  TS_Room_Set.sendCommand(22)
end
rule "heat_autm_off_TS_Room_Set"
when
  Time cron "0 30  7 ? * MON-FRI *" or
  Time cron "0 30 10 ? * SAT-SUN *" or
  Time cron "0  0 20 ? * MON-FRI *" or
  Time cron "0  0 21 ? * SAT-SUN *"
then
  TS_Room_Set.sendCommand(19)
end</pre>

number.js
<pre>result = parseFloat(input.trim()).toFixed(2);</pre>

active.map
<pre>0=OFF
1=ON
OFF=0
ON=1
-=unknown</pre>

# broadlink thermostat with mqtt and mosquitto_sub/mosquitto_pub

read from mqtt
<pre>mosquitto_sub -v -h mqtt -t '/broadlink/#'

/broadlink/xxxxxx34ea34/dayofweek 1
/broadlink/xxxxxx34ea34/remote_lock 0
/broadlink/xxxxxx34ea34/osv 42
/broadlink/xxxxxx34ea34/sec 36
/broadlink/xxxxxx34ea34/external_temp 0.0
/broadlink/xxxxxx34ea34/fre 0
/broadlink/xxxxxx34ea34/min 56
/broadlink/xxxxxx34ea34/unknown 0
/broadlink/xxxxxx34ea34/sensor 0
/broadlink/xxxxxx34ea34/loop_mode 1
/broadlink/xxxxxx34ea34/room_temp 14.5
/broadlink/xxxxxx34ea34/power 1
/broadlink/xxxxxx34ea34/thermostat_temp 5.0
/broadlink/xxxxxx34ea34/temp_manual 0
/broadlink/xxxxxx34ea34/room_temp_adj 0.0
/broadlink/xxxxxx34ea34/active 0
/broadlink/xxxxxx34ea34/poweron 0
/broadlink/xxxxxx34ea34/auto_mode 0
/broadlink/xxxxxx34ea34/svl 5
/broadlink/xxxxxx34ea34/hour 22
/broadlink/xxxxxx34ea34/svh 35
/broadlink/xxxxxx34ea34/dif 2
/broadlink/xxxxxx34ea34/schedule [[{"start_hour": 6, "temp": 20.0, "start_minute": 0}, {"start_hour": 8, "temp": 15.0, "start_minute": 0}, {"start_hour": 11, "temp": 15.0, "start_minute": 30}, {"start_hour": 12, "temp": 15.0, "start_minute": 30}, {"start_hour": 17, "temp": 22.0, "start_minute": 0}, {"start_hour": 22, "temp": 15.0, "start_minute": 0}], [{"start_hour": 8, "temp": 22.0, "start_minute": 0}, {"start_hour": 23, "temp": 15.0, "start_minute": 0}]]</pre>

set temperature for manual mode (also activates manual mode if currently in automatic)
<pre>mosquitto_pub -h 192.168.1.9 -t /broadlink/xxxxxx34ea34/cmd/set_temp -m '22'</pre>

set auto_mode = 1 for auto (scheduled/timed) mode, 0 for manual mode.
<pre>mosquitto_pub -h 192.168.1.9 -t /broadlink/xxxxxx34ea34/cmd/set_mode -m '0'</pre>

set device on(1) or off(0), does not deactivate Wifi connectivity
<pre>mosquitto_pub -h 192.168.1.9 -t /broadlink/xxxxxx34ea34/cmd/set_power -m '1'</pre>

set timer schedule, format is the same as you get from mosquitto_sub.
<pre>mosquitto_pub -h mqtt -t /broadlink/xxxxxx34ea34/cmd/set_schedule  -m '[[{"start_hour": 6, "temp": 20.0, "start_minute": 0}, {"start_hour": 8, "temp": 15.0, "start_minute": 0}, {"start_hour": 11, "temp": 15.0, "start_minute": 30}, {"start_hour": 12, "temp": 15.0, "start_minute": 30}, {"start_hour": 17, "temp": 22.0, "start_minute": 0}, {"start_hour": 22, "temp": 15.0, "start_minute": 0}], [{"start_hour": 8, "temp": 22.0, "start_minute": 0}, {"start_hour": 23, "temp": 15.0, "start_minute": 0}]]'</pre>
