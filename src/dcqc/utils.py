def validate_from_dict(cls, dictionary):
    type_ = dictionary.pop("type")
    if type_ != cls.__name__:
        message = f"Type ({type_}) does not match the class ({cls.__name__})."
        raise ValueError(message)
    return dictionary
