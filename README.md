# broadlink-thermostat
link broadlink thermostat with mqtt to openhab

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
