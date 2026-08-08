import os

class Config:
    
    DB_CONFIG = {
        "host" : os.getenv("DB_HOST", "localhost"),
        "user" : os.getenv("DB_USER", "root"),
        "password" : os.getenv("DB_PASSWORD", ""),
        "database" : os.getenv("DB_DATABASE", "proyek_12")
    }
    
    SECRET_KEY = "dannDEV"