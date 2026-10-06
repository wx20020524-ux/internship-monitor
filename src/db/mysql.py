import os
from pathlib import Path

import pymysql
from dotenv import load_dotenv


# =========================================================
# 项目根目录
# =========================================================

BASE_DIR = Path(
    __file__
).resolve().parents[2]


# =========================================================
# 加载 .env
# =========================================================

load_dotenv(
    BASE_DIR / ".env"
)


# =========================================================
# 获取 MySQL 连接
# =========================================================

def get_connection():
    """
    创建并返回一个 MySQL 数据库连接。
    """

    connection = pymysql.connect(
        host=os.getenv(
            "MYSQL_HOST",
            "localhost",
        ),

        port=int(
            os.getenv(
                "MYSQL_PORT",
                "3306",
            )
        ),

        user=os.getenv(
            "MYSQL_USER",
            "root",
        ),

        password=os.getenv(
            "MYSQL_PASSWORD",
            "",
        ),

        database=os.getenv(
            "MYSQL_DATABASE",
            "internship_monitor",
        ),

        charset="utf8mb4",

        cursorclass=pymysql.cursors.DictCursor,
    )

    return connection


# =========================================================
# 单独运行时测试数据库连接
# =========================================================

if __name__ == "__main__":

    connection = None

    try:

        connection = get_connection()

        with connection.cursor() as cursor:

            cursor.execute(
                "SELECT DATABASE();"
            )

            result = cursor.fetchone()

        print("MySQL 连接成功！")
        print(
            "当前数据库：",
            result["DATABASE()"],
        )

    except Exception as error:

        print("MySQL 连接失败！")
        print(
            "错误信息：",
            error,
        )

    finally:

        if connection:
            connection.close()