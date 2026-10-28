from campuseats.extensions import db


class User(db.Model):
    __tablename__ = "users" #database table is called 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), 
                #Requires every user creation to have a timestamp           
                nullable=False, 
                server_default=db.func.current_timestamp()
    )

    def __repr__(self):
        return f"<User {self.name}>"