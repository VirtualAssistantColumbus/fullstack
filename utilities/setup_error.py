class SetupError(Exception):
    """Exception raised for configuration errors."""
    
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)