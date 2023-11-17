def check_filename(name: str) -> None:
    """
    Ensure file name is valid, if not raise ValueError
    """
    if '/' in name or name == '.' or name == '..':
        raise ValueError('illegal name')
