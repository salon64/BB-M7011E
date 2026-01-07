import sys
import jwt
import json


def decode_token(token: str) -> dict:
    """Decode JWT token without verification (for debugging)"""
    try:
        decoded = jwt.decode(token, options={"verify_signature": False})
        return decoded
    except Exception as e:
        print(f"Failed to decode token: {e}", file=sys.stderr)
        return {}


def main():
    if len(sys.argv) != 2:
        print("Usage: python tmp_decode_token.py <JWT_TOKEN>", file=sys.stderr)
        sys.exit(1)
    token = sys.argv[1]
    decoded = decode_token(token)
    print(json.dumps(decoded, indent=2))


if __name__ == "__main__":
    main()
