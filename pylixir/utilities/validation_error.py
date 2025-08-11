class ValidationError(Exception):
    """Exception raised when field validation fails.
    NOTE: Messages in these errors should be shareable to the user.
    In your front-end code, you should handle the display of these errors when they arise. """
    
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(self.message)