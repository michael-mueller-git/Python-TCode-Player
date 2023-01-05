# pip install inputs
from inputs import get_gamepad

while 1:
    events = get_gamepad()
    for event in events:
        if event.ev_type == "Sync":
            continue
        if True:
            if event.ev_type == "Absolute":
                if event.code == "ABS_Z":
                    if event.state in [127, 128, 129]:
                        continue

        print(event.ev_type, event.code, event.state)
