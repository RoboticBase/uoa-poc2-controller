class Token:
    _tokens = {}

    @classmethod
    def get(cls, token):
        if token not in cls._tokens:
            cls._tokens[token] = cls(token)
        return cls._tokens[token]

    def __init__(self, token):
        self._token = token

    def get_lock(self, robot_id):
        print('@@@lock@@@', self._token, robot_id)
        return True

    def release_lock(self, robot_id):
        print('###release###', self._token, robot_id)
