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
    JOINING = 4
    GETTINGNAME = 5

    id = Column("id", Integer, primary_key=True)
    status = Column("status", Integer)
    secret_name = Column("secret_name", String)
    username = Column("username", String)
    list_id = Column("list_id", Integer)
    fellow_id = Column("fellow_id", Integer)
    game_id = Column(ForeignKey("games.id"))
    game = relationship("Game", back_populates="players")

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
    players = relationship("Player", back_populates="game")

    def __init__(self, game_id, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.id = game_id
        self.is_on = False

    def create_list(self, status, exclude_id):
        answer = ""
        if status == Player.INGAME or status == Player.GETTINGNAME:
            for player in self.players:
                if player.id != exclude_id:
                    answer += f"{player.username} -- {player.secret_name}"
                    answer += " ✅\n" if player.status == Player.WAITING else "\n"
                else:
                    answer += f"{player.username} -- ❔\n"
        elif status == Player.PREGAME or status == Player.JOINING:
            for player in self.players:
                answer += f"{player.username}\n"
        elif status == Player.WAITING:
            for player in self.players:
                answer += f"{player.username} -- {player.secret_name}"
                answer += " ✅\n" if player.status == Player.WAITING else "\n"
        if answer == "":
            answer = "ти тут сам"
        return answer


engine = create_engine("sqlite:///players.db", echo=True)
Base.metadata.create_all(bind=engine)

Session = sessionmaker(bind=engine)
session = Session()
