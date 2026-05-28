class UnsupportedLanguageError(Exception):
    def __init__(self, language_code: str) -> None:
        self.language_code = language_code
        super().__init__(f"UniMorphBackend does not support language '{language_code}'.")


class PosNotSupportedError(Exception):
    def __init__(self, pos: str) -> None:
        self.pos = pos
        super().__init__(f"POS '{pos}' is not supported by the UniMorph translator.")


class FeatureNotSupportedError(Exception):
    def __init__(self, key: str, value: str) -> None:
        self.key = key
        self.value = value
        super().__init__(f"UD feature '{key}={value}' has no UniMorph mapping.")
