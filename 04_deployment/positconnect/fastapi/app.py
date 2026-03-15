# -*- coding: utf-8 -*-

import json
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List


class Greeting(BaseModel):
    lang: str
    text: str


app = FastAPI()
db = json.load(open("greetings.json"))


@app.get("/greetings", response_model=List[Greeting])
async def greetings():
    return [Greeting(lang=lang, text=text) for lang, text in sorted(db.items())]


@app.get("/greetings/{lang}", response_model=Greeting)
async def greeting(lang: str = "en"):
    return Greeting(lang=lang, text=db.get(lang))
