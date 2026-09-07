from sqlalchemy import text

from config.database import engine


def test_connection():
    try:
        with engine.connect() as connection:
            result = connection.execute(
                text("SELECT current_database(), current_user")
            )

            database_name, database_user = result.one()

            print("======================================")
            print("DATABASE CONNECTION SUCCESSFUL")
            print("======================================")
            print(f"Database : {database_name}")
            print(f"User     : {database_user}")
            print("======================================")

    except Exception as exc:
        print("======================================")
        print("DATABASE CONNECTION FAILED")
        print("======================================")
        print(exc)


if __name__ == "__main__":
    test_connection()