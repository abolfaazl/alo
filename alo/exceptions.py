class AloError(Exception):
    pass

class MissingAPIKeyError(AloError):
    pass

class KeyringUnavailableError(AloError):
    pass
