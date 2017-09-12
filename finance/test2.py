from datetime import datetime,timezone,timedelta
dt = datetime.utcnow()
print(dt)
print(type(dt))
dt = dt.replace(tzinfo=timezone.utc)
print(dt)
print(type(dt))
tzutc_8 = timezone(timedelta(hours=8))
local_dt = dt.astimezone(tzutc_8).strftime('%Y-%m-%d %H:%M:%S')
print(local_dt)
print(type(local_dt))