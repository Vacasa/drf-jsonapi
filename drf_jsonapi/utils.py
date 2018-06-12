
def listify(item_or_list):
    """
    This function converts single items into single-item lists.
    """

    return item_or_list if isinstance(item_or_list, list) else [item_or_list]
