import psycopg

from config.settings import (
    DB_HOST,
    DB_PORT,
    DB_USER,
    DB_PASSWORD,
)


KNOWN_DATABASE = "gnfs_simulator_db"
TARGET_DATABASE = "family_management_db"


try:
    print("1. Connecting to known PostgreSQL database...")
    print(f"   Host: {DB_HOST}")
    print(f"   Port: {DB_PORT}")
    print(f"   User: {DB_USER}")
    print(f"   Database: {KNOWN_DATABASE}")
    print()

    connection = psycopg.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=KNOWN_DATABASE,
        user=DB_USER,
        password=DB_PASSWORD,
        connect_timeout=5,
    )

    print("CONNECTED successfully.")
    print()

    with connection.cursor() as cursor:

        # PostgreSQL server information
        cursor.execute(
            """
            SELECT
                current_database(),
                current_user,
                inet_server_addr(),
                inet_server_port(),
                version()
            """
        )

        db_name, db_user, server_ip, server_port, version = cursor.fetchone()

        print("2. PostgreSQL server information")
        print("--------------------------------")
        print("Current Database :", db_name)
        print("Current User     :", db_user)
        print("Server Address   :", server_ip)
        print("Server Port      :", server_port)
        print()

        # Check whether target database exists
        cursor.execute(
            """
            SELECT
                datname,
                datallowconn,
                datconnlimit
            FROM pg_database
            WHERE datname = %s
            """,
            (TARGET_DATABASE,),
        )

        database = cursor.fetchone()

        print("3. Checking family_management_db")
        print("--------------------------------")

        if database is None:
            print("RESULT: DATABASE DOES NOT EXIST")

        else:
            name, allow_connections, connection_limit = database

            print("Database Name    :", name)
            print("Allows Connection:", allow_connections)
            print("Connection Limit :", connection_limit)

            # Check CONNECT permission
            cursor.execute(
                """
                SELECT has_database_privilege(
                    %s,
                    %s,
                    'CONNECT'
                )
                """,
                (DB_USER, TARGET_DATABASE),
            )

            can_connect = cursor.fetchone()[0]

            print("User Can Connect :", can_connect)

    connection.close()

    print()
    print("Diagnostic completed.")

except Exception as error:
    print()
    print("DIAGNOSTIC FAILED")
    print("-----------------")
    print(type(error).__name__)
    print(error)