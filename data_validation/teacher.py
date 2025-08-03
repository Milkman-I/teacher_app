from pydantic import BaseModel

class Teacher(BaseModel):
    username:str
    password:str
