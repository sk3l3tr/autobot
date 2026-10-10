from path_provider import PathProvider


def initialize_user_environment() -> None:
    PathProvider().ensure_user_data_initialized()
