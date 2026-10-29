class ServiceNotReadyError(RuntimeError):
    """
    Raised when required reference data has not been loaded
    into the database (for example the symptom catalogue or
    the active model version). The API reports it as HTTP 503.
    """
