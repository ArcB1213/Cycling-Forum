from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# 创建扩展实例，但不与 app 关联
db = SQLAlchemy()
migrate = Migrate()