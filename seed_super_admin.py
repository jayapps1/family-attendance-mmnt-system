"""Seed the configured first super administrator without bypassing TOTP."""
import argparse
from services.seed_service import SeedService

DEFAULT_EMAIL = "nanagyachie@gmail.com"
DEFAULT_PHONE = "0542011738"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", default=DEFAULT_EMAIL)
    parser.add_argument("--phone", default=DEFAULT_PHONE)
    parser.add_argument("--username", default=None)
    args = parser.parse_args()
    from config.database import SessionLocal
    try:
        result = SeedService(SessionLocal).super_admin(args.email, args.phone, args.username)
    except ValueError as exc:
        parser.exit(1, str(exc) + "\n")
    print("Super administrator created." if result["created"] else "Super administrator already exists.")
    print(f'Username: {result["username"]}')
    print(f'Email: {result["email"]}')
    print(f'Phone: {result["phone_number"]}')
    if result["enrollment_required"]:
        print("Start main.py and complete first-administrator authenticator setup.")
    else:
        print("Existing authenticator enrollment was preserved.")


if __name__ == "__main__":
    main()
