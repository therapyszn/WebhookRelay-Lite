import argparse
import sys
import uvicorn
from webhookrelay.server import create_app


def parse_args():
    parser = argparse.ArgumentParser(
        prog="webhookrelay",
        description="Self-hosted webhook inspector, local replay engine, and HMAC signer",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8080, help="Port to listen on (default: 8080)")
    parser.add_argument("--forward", help="Auto-forward incoming webhooks to target URL")
    parser.add_argument("--secret", help="Default signing secret for HMAC recalculation")
    parser.add_argument(
        "--provider",
        choices=["stripe", "github", "shopify", "generic"],
        default="stripe",
        help="Default webhook provider for HMAC signing",
    )
    parser.add_argument("--db", default="webhooks.db", help="SQLite database path (default: webhooks.db)")
    return parser.parse_args()


def main():
    args = parse_args()
    app = create_app(
        db_path=args.db,
        forward_url=args.forward,
        default_secret=args.secret,
        default_provider=args.provider,
    )

    print(f"WebhookRelay Lite listening on http://{args.host}:{args.port}")
    print(f"Dashboard available at: http://{args.host}:{args.port}/")
    print(f"Send incoming webhooks to: http://{args.host}:{args.port}/webhook")
    if args.forward:
        print(f"Auto-forwarding enabled -> {args.forward}")

    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
