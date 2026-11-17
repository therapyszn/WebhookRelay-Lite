# WebhookRelay Lite

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.8+" />
  <img src="https://img.shields.io/badge/FastAPI-Framework-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/SQLite-Storage-003B57?style=for-the-badge&logo=sqlite&logoColor=white" alt="SQLite" />
  <img src="https://img.shields.io/badge/Windows-Supported-0078D6?style=for-the-badge&logo=windows&logoColor=white" alt="Windows" />
  <img src="https://img.shields.io/badge/Linux-Supported-FCC624?style=for-the-badge&logo=linux&logoColor=black" alt="Linux" />
  <img src="https://img.shields.io/badge/macOS-Supported-000000?style=for-the-badge&logo=apple&logoColor=white" alt="macOS" />
</p>

A local developer utility and interactive dashboard to intercept incoming webhook payloads, inspect headers, replay events against local development servers, and recalculate HMAC-SHA256 signatures for Stripe, GitHub, and Shopify.

---

## Features

- **Catch-All Webhook Ingestion**: Listens on `/webhook` (or any sub-path) and captures headers, query parameters, IP, content-type, and raw request bodies.
- **Real-Time Live Dashboard**: Streams newly captured webhooks to your browser instantly using Server-Sent Events (SSE).
- **Embedded SQLite Storage**: Persists all intercepted requests locally in a lightweight SQLite database (`webhooks.db`).
- **One-Click Local Replay**: Re-dispatch captured requests to your local development endpoints (e.g. `http://localhost:3000/api/webhook`).
- **HMAC Signature Recalculation**: Automatically regenerates cryptographic signatures when editing payloads in the dashboard:
  - `stripe-signature` (timestamped `t=...,v1=...`)
  - `x-hub-signature-256` (GitHub sha256 hex digest)
  - `x-shopify-hmac-sha256` (Shopify base64 digest)
  - Generic `x-signature-sha256`
- **Zero Heavy Tooling**: Self-contained Python service with an embedded single-page interface.

---

## Prerequisites

- Python 3.8 or newer
- Windows, Linux, or macOS

---

## Installation

Clone the repository and install dependencies:

```bash
git clone https://github.com/therapyszn/WebhookRelay-Lite.git
cd WebhookRelay-Lite
pip install -r requirements.txt
```

---

## Quick Start

Start the relay server:

```bash
python main.py
```

The service will start with:
- **Web Dashboard**: `http://127.0.0.1:8080/`
- **Webhook Ingestion URL**: `http://127.0.0.1:8080/webhook`

### CLI Options

```bash
python main.py --help

options:
  --host HOST           Host interface to bind (default: 127.0.0.1)
  --port PORT           Port to listen on (default: 8080)
  --forward FORWARD     Auto-forward incoming webhooks to target URL
  --secret SECRET       Default signing secret for HMAC recalculation
  --provider {stripe,github,shopify,generic}
                        Default webhook provider for HMAC signing
  --db DB               SQLite database path (default: webhooks.db)
```

### Auto-Forwarding Example

To automatically stream all received webhooks directly to your local backend while logging them to the dashboard:

```bash
python main.py --port 8080 --forward http://127.0.0.1:3000/api/webhooks
```

---

## Testing Webhooks

Send a sample webhook to your local listener:

```bash
curl -X POST http://127.0.0.1:8080/webhook \
  -H "Content-Type: application/json" \
  -d '{"event": "payment_intent.succeeded", "amount": 2500}'
```

The event will appear immediately on the dashboard with headers, payload, and replay options.

---

## License

MIT License.
