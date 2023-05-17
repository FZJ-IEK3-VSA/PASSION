from typing import Dict, List, Tuple


def xattr(_cls=None, *, xattr = None):
    #print(_cls)
    #print(attr_dict)
    
    def wrap(cls):
        return _process_class(cls, x_attr=xattr)

    if _cls is None:
        return wrap

    return wrap(_cls)

def _process_class(cls, x_attr):
    cls_init = cls.__init__

    __x_attr = {}

    for key in x_attr:
        if not isinstance(x_attr[key], List):
            __x_attr[key] = [x_attr[key]]
        else:
            __x_attr[key] = x_attr[key]

    cls.xattr = __x_attr

    def __init__(self, *args, **kwargs):
        cls_init(self, *args, **kwargs)

    cls.__init__ = __init__
    
    return cls

"""
def xattr(_cls=None, attr_dict = None):
    print(attr_dict)
    print(_cls)

    def wrap(cls):
        return _process_class(cls, attr_dict)

    if _cls is None:
        return wrap(_cls)

    return _cls

def _process_class(cls, attr_dict):
    if attr_dict is not None:
        cls.attr_dict = attr_dict
    
    return cls
"""