from mafia import Mafia


class Don(Mafia):
    """Класс Дона мафии"""

    def __init__(self, game, user):
        super().__init__(game, user)
        self.role_name = game.gt("roles.don")
        self.role_name_short = game.gt("don_role_name_short")
        self.role_description = game.gt("don_role_description")
