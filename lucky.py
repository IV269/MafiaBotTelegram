from role import Role


class Lucky(Role):
    """Стандартный класс везунчика"""

    def __init__(self, game, user):
        super().__init__(game, user)
        self.role_name = game.gt("roles.lucky")
        self.role_name_short = game.gt("lucky_role_name_short")
        self.role_description = game.gt("lucky_role_description")
