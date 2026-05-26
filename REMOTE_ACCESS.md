# Accessing HolyTerminal Remotely (SSH)

## Dashboard
- **URL**: `http://<HOST_IP>:3000`
- Find HOST_IP: `hostname -I` on the remote machine

## PostgreSQL
- **Host**: `<HOST_IP>`
- **Port**: `5432`
- **Database**: `holyterminal`
- Connect with any PostgreSQL client (DBeaver, pgAdmin, psql)

## Blnk Ledger API
- **URL**: `http://<HOST_IP>:7789`

## Security Note
These ports are open to the network. For production, use a firewall (ufw) or SSH tunnel:

```bash
# SSH tunnel (more secure — no open ports):
ssh -L 3000:localhost:3000 -L 5432:localhost:5432 user@remote-host
# Then access http://localhost:3000 on your local PC
```
