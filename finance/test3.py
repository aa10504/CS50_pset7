from datetime import datetime,timezone,timedelta

dt = datetime.utcnow()
print(dt)
print(type(dt))

utc_dt = dt.replace(tzinfo=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
print(utc_dt)
print(type(utc_dt))

tzutc_8 = timezone(timedelta(hours=8))
local_dt = dt.astimezone(tzutc_8).strftime('%Y-%m-%d %H:%M:%S')
print(local_dt)
print(type(local_dt))

print()