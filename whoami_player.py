from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy import create_engine, Integer, String, Column, Boolean, ForeignKey

Base = declarative_base()


class Player(Base):
    __tablename__ = "players"

    INACTIVE = 0
    WAITING = 1
    PREGAME = 2
    INGAME = 3

    id = Column("id", Integer, primary_key=True)
    status = Column("status", Integer)
    secret_name = Column("secret_name", String)
    username = Column("username", String)
    replay_id = Column("replay_id", Integer)
    list_id = Column("list_id", Integer)
    game_id = Column(Integer, ForeignKey("games.id"))
    game = relationship(back_populates="players")

    def __init__(self, telegram_id, username, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.id = telegram_id
        self.username = username
        self.status = Player.INACTIVE
        self.secret_name = ""


class Game(Base):
    __tablename__ = "games"

    id = Column("id", Integer, primary_key=True)
    is_on = Column("is_on", Boolean)
    players = relationship(back_populates="game")

    def __init__(self, game_id, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.id = game_id
        self.is_on = False

engine = create_engine("sqlite:///players.db", echo=True)
Base.metadata.create_all(bind=engine)

Session = sessionmaker(bind=engine)
session = Session()

