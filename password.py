import bcrypt
from flask_mysqldb import MySQL
from flask import Flask

# 初始化 MySQL
app = Flask(__name__)
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'xk_system'
mysql = MySQL(app)

def hash_password(password):
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed_password

def update_passwords():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT ID, password FROM user")
    users = cursor.fetchall()

    for user in users:
        user_id = user[0]
        plain_password = user[1]
        hashed_password = hash_password(plain_password)
        cursor.execute("UPDATE user SET password = %s WHERE ID = %s", (hashed_password, user_id))

    mysql.connection.commit()
    cursor.close()

if __name__ == '__main__':
    with app.app_context():
        update_passwords()