# Discord Bot Service

Discord bot for the BB system, allowing users to interact with the platform via Discord.

## Features

- Check account balance
- List available items
- Purchase items
- View transaction history

## Commands

| Command | Description |
|---------|-------------|
| `!ping` | Check if the bot is responsive |
| `!balance` | Check your account balance |
| `!items` | List available items |
| `!buy <item_id>` | Purchase an item |
| `!help` | Show available commands |

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DISCORD_TOKEN` | Discord bot token (required) | - |
| `COMMAND_PREFIX` | Bot command prefix | `!` |
| `USER_SERVICE_URL` | User service URL | `http://user-service:8001` |
| `PAYMENT_SERVICE_URL` | Payment service URL | `http://payment-service:8002` |
| `ITEM_SERVICE_URL` | Item service URL | `http://item-service:8003` |
| `LOG_LEVEL` | Logging level | `INFO` |

## Local Development

1. Create a `.env` file:
```bash
DISCORD_TOKEN=your_discord_bot_token
COMMAND_PREFIX=!
USER_SERVICE_URL=http://localhost:8001
PAYMENT_SERVICE_URL=http://localhost:8002
ITEM_SERVICE_URL=http://localhost:8003
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the bot:
```bash
python main.py
```

## Testing

```bash
pytest tests/ -v
```

## Docker

Build and run:
```bash
docker build -t discord-bot -f discord_bot/Dockerfile .
docker run --env-file .env discord-bot
```

## Kubernetes Deployment

Deploy using Helm:
```bash
helm install discord-bot ./k8s --set discordToken=YOUR_TOKEN
```
