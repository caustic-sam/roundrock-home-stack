# 🏠 pi-home Deployment Guide (Triple Stack Edition)

Welcome to your fully containerized smart home hub! This guide covers setup, default settings, and how to make changes for:

- 📡 Pi-hole (ad blocker)
- 🧠 Home Assistant (smart home)
- 📺 Plex Media Server (media streamer)

---

## 🚀 Services Summary

| Service       | Port     | Access URL                   | Credentials             |
|---------------|----------|------------------------------|--------------------------|
| Pi-hole       | 80       | http://pi-home.local/admin   | `admin` / `${PIHOLE_PASSWORD}` |
| Home Assistant| 8123     | http://pi-home.local:8123    | Create on first login    |
| Plex          | 32400    | http://pi-home.local:32400   | Plex account required    |

---

## 📂 Volumes and Paths

| Path                      | Purpose                  |
|---------------------------|--------------------------|
| `${CONFIG_DIR}/pihole`    | Pi-hole config & DNS     |
| `${CONFIG_DIR}/homeassistant` | Home Assistant config |
| `${CONFIG_DIR}/plex`      | Plex library & settings  |
| `${MEDIA_DIR}`            | Mounted SSD for media    |

---

## 🔐 Security & Access

- Default Pi-hole password: `ChangeMeNow_AdBlock123`
- Host networking ensures visibility on your LAN
- Update credentials in `.env` file
- Use `ufw` for firewall, `fail2ban` for SSH brute-force protection
- Tailscale recommended for remote access

---

## 🛠️ How to Start

1. SSH into your Pi
2. Place all files in `/home/pi/pi-home-stack`
3. Mount your external SSD to `/mnt/media`
4. Run:

```bash
cd ~/pi-home-stack
cp .env .env.local  # Or edit `.env` directly
docker compose up -d
```

---

## 🧠 Advanced Tips

- Add Watchtower for auto-updates
- Add Traefik for subdomain-based access (e.g., plex.pi-home.local)
- Backup `~/pi-home-config` weekly

---

## 🖥️ GUI Desktop Access

Install GUI & VNC for remote desktop access (run on host Pi, not HA):

```bash
sudo apt update
sudo apt install -y xfce4 xfce4-goodies tightvncserver
vncserver :1
```

Then access from VNC Viewer (Mac/iPad) at:

```
pi-home.local:1 or <Pi-IP>:1
```

---

Happy hacking, partner 🤠