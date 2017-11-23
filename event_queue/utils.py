import traceback


def format_exc_info(exc_info):
    """
    Format exception info as string
    :param exc_info: exception info
    :return: string
    """
    if exc_info[0] is None:
        return 'None'
    lines = traceback.format_exception(*exc_info)
    return ''.join(line for line in lines)
