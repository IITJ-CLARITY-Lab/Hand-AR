
# Step 1: Create the user service directory

```bash
mkdir -p ~/.config/systemd/user
```

---

# Step 2: Create the service file

```bash
nano ~/.config/systemd/user/handarm2.service
```

Paste this:

```ini
[Unit]
Description=Hand-ArM2 Gesture Control System
After=graphical-session.target

[Service]
Type=simple
WorkingDirectory=/home/dhaniya/Desktop/Hand-point-cloud

ExecStart=/home/dhaniya/Desktop/Hand-point-cloud/handtrack_env/bin/python /home/dhaniya/Desktop/Hand-point-cloud/opening.py

Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
```

Save:

* **Ctrl + O**
* **Enter**
* **Ctrl + X**

---

# Step 3: Reload systemd

```bash
systemctl --user daemon-reload
```

---

# Step 4: Enable the service

```bash
systemctl --user enable handarm2.service
```

You should see something similar to:

```text
Created symlink ...
```

---

# Step 5: Start it without rebooting

```bash
systemctl --user start handarm2.service
```

---

# Step 6: Check its status

```bash
systemctl --user status handarm2.service
```

If everything is working, you'll see:

```text
Active: active (running)
```

---

# Step 7: Reboot

```bash
sudo reboot
```

Hand-ArM2 should start automatically after you log into your desktop session.

---

# Useful Commands

### Stop the application

```bash
systemctl --user stop handarm2.service
```

---

### Start it again

```bash
systemctl --user start handarm2.service
```

---

### Disable auto-start

```bash
systemctl --user disable handarm2.service
```

After this, your Raspberry Pi will boot normally to the desktop.

---

### Enable auto-start again

```bash
systemctl --user enable handarm2.service
```

---

### Disable and stop immediately

```bash
systemctl --user disable --now handarm2.service
```

---

### Check whether it's enabled

```bash
systemctl --user is-enabled handarm2.service
```

Expected output:

```text
enabled
```

or

```text
disabled
```

---

### View logs

```bash
journalctl --user -u handarm2.service -f
```

---

## If you want it to start even when you haven't logged in

Run this once:

```bash
sudo loginctl enable-linger dhaniya
```

This allows your user services to remain available without an active login session. For a normal desktop workflow where you log in automatically, this step is optional.
