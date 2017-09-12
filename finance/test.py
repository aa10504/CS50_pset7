import time
from datetime import datetime,timezone,timedelta

t = time.time() # 獲得現在的時間戳
utc_time = datetime.fromtimestamp(t).strftime('%Y-%m-%d %H:%M:%S')

now = datetime.now().timestamp()

tzutc_8 = timezone(timedelta(hours=8))
local_dt = utc_time.astimezone(tzutc_8).strftime('%Y-%m-%d %H:%M:%S')

print(t)
print(type(t))
print(utc_time)
print(now)
print(local_dt)