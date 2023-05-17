import copy
import dataclasses
import enum
from functools import wraps
import inspect
import json
import re
import os
from statistics import mode
import string
import typing
import pandas as pd
from types import ModuleType
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union

import yaml

class OpenAPIGeneratorException(Exception):
    pass


class OpenAPIDataModel:
    def __init__(self, typename: str, is_optional: bool = False) -> None:
        self.typename: str = typename
        self.x_properties = {}
        self.is_optional = is_optional

    def add_x_property(self, x_name : str, x_value):
        self.x_properties["x-"+x_name] = x_value

    def export_to_dict(self, objects_as_ref: bool = False) -> Dict[str, Any]:
        data_model_dict = {"type": self.typename}
        for x_property in self.x_properties:
            data_model_dict[x_property] = self.x_properties[x_property]
        return data_model_dict

    def to_json(self) -> str:
        return json.dumps(
            self.export_to_dict(),
            sort_keys=True,
            indent=4,
        )


# class OptionalModel(OpenAPIDataModel):
#     def __init__(self, model: OpenAPIDataModel) -> None:
#         self.model = model

#     def is_optional(self) -> bool:
#         return True

#     def export_to_dict(self, objects_as_ref: bool = False) -> Dict[str, Any]:
#         return self.model.export_to_dict(objects_as_ref)


class ReferencableModel(OpenAPIDataModel):
    def __init__(self, openapi_typename: str, name: str) -> None:
        super().__init__(openapi_typename)
        self.name = name
        self.ref = "#/components/schemas/" + self.name

    def export_to_dict(self, objects_as_ref: bool = False) -> Dict[str, Any]:
        if objects_as_ref:
            return {"$ref": self.ref}
        return super().export_to_dict()

class ObjectModel(ReferencableModel):
    def __init__(self, name: str, description: str = None) -> None:
        super().__init__("object", name)
        self.description = description
        self.properties: Dict[str, OpenAPIDataModel] = {}
        self.functions: Dict[str, OpenAPIDataModel] = {}

    def add_property(self, name: str, model: OpenAPIDataModel):
        self.properties[name] = model

    def add_function(self, name: str, model: OpenAPIDataModel):
        self.functions[name] = model

    def export_to_dict(self, objects_as_ref: bool = False) -> Dict[str, Any]:
        d = super().export_to_dict(objects_as_ref)
        if objects_as_ref:
            return d
        if self.description is not None:
            d["description"] = self.description
        # add properties by reference if possible
        d["properties"] = {
# Setting objects_as_ref to 'False' here will result in pandas.DataFrames not being defined.
            name: model.export_to_dict(objects_as_ref=False)
            for name, model in self.properties.items()
        }
        if self.functions:
            d["x-functions"] = {
                name: model.export_to_dict(objects_as_ref=False)
                for name, model in self.functions.items()
            }
        # add a list of required properties if there are any
        required = [
            name for name, model in self.properties.items() if not model.is_optional
        ]
        if required:
            d["required"] = required
        return d


class ArrayModel(OpenAPIDataModel):
    def __init__(self, item_model: OpenAPIDataModel = None) -> None:
        super().__init__("array")
        self.item_model = item_model

    def set_item_model(self, item_model: OpenAPIDataModel = None):
        self.item_model = item_model

    def export_to_dict(self, objects_as_ref: bool = False) -> Dict[str, Any]:
        d = super().export_to_dict()
        if self.item_model is None:
            raise RuntimeError(
                f"An item model has to be specified for each array model."
            )
        d["items"] = self.item_model.export_to_dict(objects_as_ref=True)
        return d


class DictModel(OpenAPIDataModel):
    def __init__(self, item_model: OpenAPIDataModel = None) -> None:
        super().__init__("object")
        # the model of the contained dictionary values; the keys have to be strings
        self.item_model = item_model

    def set_item_model(self, item_model: OpenAPIDataModel = None):
        self.item_model = item_model

    def export_to_dict(self, objects_as_ref: bool = False) -> Dict[str, Any]:
        d = super().export_to_dict()
        if self.item_model is not None:
            d["additionalProperties"] = self.item_model.export_to_dict(
                objects_as_ref=True
            )
        return d


class UnionModel(OpenAPIDataModel):
    def __init__(self, types: Iterable[OpenAPIDataModel]):
        super().__init__("union")
        self.types = types

    def export_to_dict(self, objects_as_ref: bool = False) -> Dict[str, Any]:
        d = super().export_to_dict()
        # replace 'type' property with 'anyOf' object
        del d["type"]
        d["anyOf"] = [t.export_to_dict(False) for t in self.types]
        return d


class TupleModel(OpenAPIDataModel):
    def __init__(self, types: Iterable[OpenAPIDataModel]):
        super().__init__("tuple")
        self.types = types

    def export_to_dict(self, objects_as_ref: bool = False) -> Dict[str, Any]:
        d = super().export_to_dict()
        # replace 'type' property with 'anyOf' object
        del d["type"]
        d["tupleTypes"] = [t.export_to_dict(True) for t in self.types]
        return d


class StringModel(OpenAPIDataModel):
    def __init__(self, format: str = None) -> None:
        super().__init__("string")
        self.format = format

    def export_to_dict(self, objects_as_ref: bool = False) -> Dict[str, Any]:
        d = super().export_to_dict()
        if self.format is not None:
            d["format"] = self.format
        return d


class EnumModel(ReferencableModel):
    def __init__(self, name: str, values: Iterable[str]) -> None:
        super().__init__("string", name)
        self.values = values

    def export_to_dict(self, objects_as_ref: bool = False) -> Dict[str, Any]:
        d = super().export_to_dict(objects_as_ref)
        if objects_as_ref:
            return d
        d["enum"] = self.values
        return d


class NumberModel(OpenAPIDataModel):
    def __init__(self, integer: bool = False) -> None:
        super().__init__("integer" if integer else "number")


class BooleanModel(OpenAPIDataModel):
    def __init__(self) -> None:
        super().__init__("boolean")


class NullModel(OpenAPIDataModel):
    def __init__(self) -> None:
        super().__init__("null")

def get_function_fields(type_: type) -> Dict[str, Any]:
    if not inspect.isfunction(type_):
        raise NotImplementedError("Only supports functions")
    resolved_hints = typing.get_type_hints(type_)

    sig = inspect.signature(type_)
    sig_keys = list(sig.parameters.keys())

    # *args and **kwargs do not work because of the asterisk, filter them out
    resolved_fields = { key : resolved_hints[key] for key in sig_keys if not (key == 'kwargs' or key == 'args')}

    # resolved_fields = {}
    # for key in sig_keys:
    #     param = sig.parameters[key]
    #     type_ = param._annotation
        
    #     if isinstance(type_, inspect._empty) or type_ == inspect._empty:
    #         type_ = object
    #     resolved_fields[key] = type_
    #     print(key)
    #print(resolved_fields)
    return resolved_fields

def get_dataclass_fields(type_: type) -> Dict[str, Any]:
    """Resolves type hints for properties of a dataclass

    :param type_: the dataclass to get the field types of
    :type type_: type
    :raises NotImplementedError: if the type is no dataclass
    :return: a dict mapping all field names of the dataclass
             to their according type annotations
    :rtype: Dict[str, Any]
    """
    if not dataclasses.is_dataclass(type_):
        raise NotImplementedError("Only supports dataclasses")
    resolved_hints = typing.get_type_hints(type_)
    field_names = [field.name for field in dataclasses.fields(type_)]
    resolved_fields = {name: resolved_hints[name] for name in field_names}
    return resolved_fields


def model_definition_storage(func: typing.Callable):
    """
    This function is used as a decorator for methods in OpenAPIGenerator that
    handle referencable data models. It checks, if the model has already been
    created before to avoid duplicates, and otherwhise stores it.

    :param func: The method to decorate
    :type func: typing.Callable
    :return: the decorated method
    :rtype: _type_
    """

    @wraps(func)
    def function_with_storage(self, type_: type, *args, **kwargs):
        name = type_.__name__
        # check if a data model for this type was already created
        if name in self.object_models:
            return self.object_models[name]
        model = func(self, type_, *args, **kwargs)
        # save the data model to reuse it
        self.object_models[name] = model
        return model

    return function_with_storage


class OpenAPIGenerator:
    API_DEFINITION_TEMPLATE = {
        "openapi": "3.0.0",
        "info": {"title": "My Spec", "version": "1.0.0"},
        "paths": {},
        "components": {"schemas": {}},
    }

    def __init__(self) -> None:
        # this dict is used to save all created data models for objects
        self.object_models: Dict[str, ObjectModel] = {}

    def create_api_definition(
        self, types: Iterable[type], funcs: Iterable[type], export_to_json: bool = False
    ) -> str:
        model_definitions = self.create_model_definitions(types, funcs)
        model_definitions_dict = self.model_objects_to_dict(model_definitions)
        api_definition = copy.deepcopy(OpenAPIGenerator.API_DEFINITION_TEMPLATE)
        assert isinstance(api_definition["components"], dict)
        api_definition["components"]["schemas"] = model_definitions_dict
        if export_to_json:
            return json.dumps(
                api_definition,
                sort_keys=False,
                indent=4,
            )
        else:
            return yaml.dump(api_definition, sort_keys=False)

    def create_api_definition_file(
        self, types: Iterable[type], funcs: Iterable[type], filename: str, export_to_json: bool = False
    ) -> None:
        definition = self.create_api_definition(types, funcs, export_to_json)
        file_extension = ".json" if export_to_json else ".yaml"
        if not filename.endswith(file_extension):
            filename = os.path.splitext(filename)[0] + file_extension
        with open(filename, "w+") as oa_definition_file:
            oa_definition_file.write(definition)

    def model_objects_to_dict(
        self, model_definitions: Dict[str, ObjectModel]
    ) -> Dict[str, Any]:
        return {key: model.export_to_dict() for key, model in model_definitions.items()}

    def create_model_definitions(self, types: Iterable[type], funcs: Iterable[type]) -> Dict[str, ObjectModel]:
        # create data models for all desired types
        for type_ in types:
            # get functions from type_
            self.create_model_definition(type_)
        for func_ in funcs:
            self.create_model_definition(func_)
        return self.object_models

    def create_func_definition(self, name) -> OpenAPIDataModel:
        return ObjectModel(name=name)

    def create_model_definition(self, type_) -> OpenAPIDataModel:
        # check if type_ is an actual type or a type annotation
        if isinstance(type_, str):
            return ObjectModel(type_)
        if inspect.isclass(type_):
            if type_ is object:
                return ObjectModel(type_.__name__)
            if type_ is str:
                return StringModel()
            elif type_ is float:
                return NumberModel()
            elif type_ is int:
                return NumberModel(integer=True)
            elif type_ is bool:
                return BooleanModel()
            elif type_ is type(None):
                return NullModel()
            elif dataclasses.is_dataclass(type_):
                return self.create_dataclass_model(type_)
            elif issubclass(type_, enum.Enum):
                return self.create_enum_model(type_)
            else:
                print(f'Other class: {type_}, type {type(type_)}')
                object_model = ObjectModel(f'{type_.__module__}.{type_.__name__}')
                object_model.add_property('x-type', StringModel(f'{type_.__module__}.{type_.__name__}'))
                return object_model
        elif inspect.isfunction(type_):
            return self.create_function_model(type_)
        else:
            # type_ probably is a type annotation like List[str].
            # Divide type_ into origin and args to check for container types.
            # Example: List[str] --> origin: List, args: (str)
            origin = typing.get_origin(type_)
            args = typing.get_args(type_)
            if origin is Union:
                union_types: Iterable[Any] = args
                is_optional = False
                if type(None) in args:
                    # Union of NoneType and other types: this is an optional property
                    # Remove NoneType from the list of types
                    is_optional = True
                    union_types = [t for t in args if t is not type(None)]
                    if len(union_types) == 1:
                        # Optional property with just one type --> don't use a UnionModel
                        model = self.create_model_definition(union_types[0])
                        model.is_optional = True
                        return model

                # normal Union of two or more types
                type_models = [self.create_model_definition(a) for a in union_types]
                union_model = UnionModel(type_models)
                union_model.is_optional = is_optional
                return union_model
            elif origin is list:
                item_type = args[0]
                item_model = self.create_model_definition(item_type)
                return ArrayModel(item_model)
            elif origin is set:
                if args[0] != str:
                    raise OpenAPIGeneratorException(
                        f"Found a set with key type {args[0]}. "
                        f"OpenAPI allows only strings as dictionary keys."
                    )
                return DictModel()
            elif origin is dict:
                if args[0] != str:
                    raise OpenAPIGeneratorException(
                        f"Found a dictionary with key type {args[0]}. "
                        f"OpenAPI allows only strings as dictionary keys."
                    )
                item_model = self.create_model_definition(args[1])
                return DictModel(item_model)
            elif origin is tuple:
                type_models = []
                for arg in args:
                    type_model = self.create_model_definition(arg)
                    type_models.append(type_model)
                return TupleModel(type_models)

        raise NotImplementedError(f"Could not resolve the type: {type_}")

    def metadata_from_description(self, description: str) -> Dict:
        """
        Searches description string for patterns in the likes of
            [datatype]@[field_name].[property_name]:[value]
        and extracts matches into a dictionary, identified by field_name.

        :param description: The string to search through
        :type description: str
        :return: The matching patterns
        :rtype: Dict
        """
        import re
        metadata = {}
        
        pat_properties_from_description = re.compile("(.*[@.:].*$)", re.MULTILINE)
        properties_from_description = []
        try:
            properties_from_description = (pat_properties_from_description.findall(description))
            properties_from_description = [i.strip() for i in properties_from_description]
        except:
            pass

        for line in properties_from_description:
            description = description.replace(line, "").strip()
            try:
                pat_prop_datatype = re.compile("(.*?)@")
                prop_datatype = (pat_prop_datatype.search(line).group(1))
                try:
                    prop_datatype = eval(pat_prop_datatype.search(line).group(1))
                except NameError:
                    print("Datatype {} is not defined.".format(prop_datatype))
                    continue

                pat_model_name = re.compile("@(.*?)\.")
                pat_prop_name = re.compile(".*\.(.*?):")
                pat_prop_value = re.compile(".*?\:(.*)")

                try:
                    model_name = pat_model_name.search(line).group(1)
                    prop_name = pat_prop_name.search(line).group(1)
                    prop_value = pat_prop_value.search(line).group(1)

                    prop_value = prop_datatype(prop_value)

                    if model_name in metadata:
                        metadata[model_name][prop_name] = prop_value
                    else:
                        metadata[model_name] = {prop_name : prop_value}
                except AttributeError as e:
                    print(e)
            except AttributeError as e:
                continue

        return description, metadata if bool(metadata) else None

    @model_definition_storage
    def create_dataclass_model(self, type_: type) -> ObjectModel:
        assert dataclasses.is_dataclass(type_), f"The type {type_} is no dataclass"
        name = type_.__name__
        description = type_.__doc__  # docstring of the class
        # Todo: makeshift solution to skip generated docstrings from dataclasses
        description, metadata = self.metadata_from_description(description)
        if description is not None and description.startswith(name):
            description = None
        model = ObjectModel(name, description)
        fields = get_dataclass_fields(type_)
        for field_name, field_type in fields.items():
            field_model = self.create_model_definition(field_type)

            # assume x-property information was provided by decorator;
            # prioritize decorator declaration
            if hasattr(type_, 'xattr'):
                property_dict = type_.xattr
                if property_dict is not None:
                    for key in property_dict:
                        # only add x properties to their respective fields
                        if not key == field_name:
                            continue
                        property_entry = property_dict[key]
                        if(isinstance(property_entry, List)):
                            for property_tuple in property_entry:
                                field_model.add_x_property(
                                        property_tuple[0],
                                        property_tuple[1]
                                        )
                        if(isinstance(property_entry, Tuple)):
                            field_model.add_x_property(
                                        property_entry[0],
                                        property_entry[1]
                            )
            else:
                if metadata is not None:
                    property_dict = metadata[field_name] if field_name in metadata else None
                    if property_dict is not None:
                        for key in property_dict:
                            field_model.add_x_property(key, property_dict[key])

            model.add_property(field_name, field_model)

        
        _magic_attr_pattern = re.compile('^[_]{2}.*[_]{2}$')
        _json_methods = ["to_json", "to_dict", "from_json", "from_dict"]
        funcs = { k : type_.__dict__[k] for k in type_.__dict__.keys() if ( callable(type_.__dict__[k]) and not _magic_attr_pattern.match(k) and k not in _json_methods )  }
        for func_name, func_pointer in funcs.items():
            func_model = self.create_func_definition(func_name)
            
            param_dict = {}
            if hasattr(type_, 'xattr'):
                property_dict = type_.xattr
                if property_dict is not None:
                    if func_name in property_dict:
                        func_attrs = property_dict[func_name]
                        # Assume mixture of function metadata and parameter metadata
                        if isinstance(func_attrs, List):
                            for attr in func_attrs:
                                # multiple function metadata
                                if isinstance(attr, List):
                                    for _attr in attr:
                                        func_model.add_x_property( _attr[0], _attr[1] )    
                                # singular function metadata
                                if isinstance(attr, Tuple):
                                    func_model.add_x_property( attr[0], attr[1] )
                                # parameter metadata
                                if isinstance(attr, Dict):
                                    param_dict = attr
                        # Assume only parameters metadata
                        if isinstance(func_attrs, Tuple):
                            func_model.add_x_property( attr[0], attr[1] )
                        # Assume only function metadata
                        if isinstance(func_attrs, Dict):
                            param_dict = attr
                        
            # function params
            params = func_pointer.__annotations__
            for param_name, param_type in params.items():
                # If it is a string, try to evaluate it as a data type
                if isinstance(param_type, str):
                    try:
                        param_type = eval(param_type)
                    except:
                        print(f'Could not evaluate {param_type}. Continuing as a string...')
                param_model = self.create_model_definition(param_type)
                if param_name in param_dict:
                    param_xattr = param_dict[param_name]
                    # multiple function metadata
                    if isinstance(param_xattr, List):
                        for _attr in param_xattr:
                            param_model.add_x_property( _attr[0], _attr[1] )    
                    # singular function metadata
                    if isinstance(param_xattr, Tuple):
                        param_model.add_x_property( param_xattr[0], param_xattr[1] )
                func_model.add_property(param_name, param_model)

            model.add_function(func_name, func_model)
        
        return model

    @model_definition_storage
    def create_enum_model(self, type_: type) -> EnumModel:
        assert issubclass(type_, enum.Enum)
        name = type_.__name__
        values = [e.value for e in type_]
        model = EnumModel(name, values)
        return model

    @model_definition_storage
    def create_function_model(self, type_: type) -> ObjectModel:
        assert inspect.isfunction(type_), f"The type {type_} is no function"
        name = type_.__name__
        description = type_.__doc__  # docstring of the class
        # Todo: makeshift solution to skip generated docstrings from dataclasses
        description, metadata = self.metadata_from_description(description)
        if description is not None and description.startswith(name):
            description = None
        model = ObjectModel(name, description)
        fields = get_function_fields(type_)
        for field_name, field_type in fields.items():
            field_model = self.create_model_definition(field_type)

            # assume x-property information was provided by decorator;
            # prioritize decorator declaration
            if hasattr(type_, 'xattr'):
                property_dict = type_.xattr
                if property_dict is not None:
                    for key in property_dict:
                        for entry in property_dict[key]:
                            if( isinstance(entry, Tuple) ):
                                model.add_x_property(
                                    entry[0],
                                    entry[1]
                                )
                            if( isinstance(entry, Dict) ):
                                for k,v in entry.items():
                                    if k != field_name:
                                        if k == "return":
                                            return_model = self.create_model_definition(type('object', (), {}))
                                            if(isinstance(v, List)):
                                                for property_tuple in v:
                                                    #print(property_tuple)
                                                    return_model.add_x_property(
                                                            property_tuple[0],
                                                            property_tuple[1]
                                                            )
                                            if(isinstance(v, Tuple)):
                                                return_model.add_x_property(
                                                            v[0],
                                                            v[1]
                                                )
                                            model.add_property("return", return_model)
                                        continue
                                    if(isinstance(v, List)):
                                        for property_tuple in v:
                                            #print(property_tuple)
                                            field_model.add_x_property(
                                                    property_tuple[0],
                                                    property_tuple[1]
                                                    )
                                    if(isinstance(v, Tuple)):
                                        field_model.add_x_property(
                                                    v[0],
                                                    v[1]
                                        )
                        # only add x properties to their respective fields
                            #print(property_dict)
                            #if not key == field_name:
                            #    continue
                            #property_entry = property_dict[key]
                            #if(isinstance(property_entry, List)):
                            #    for property_tuple in property_entry:
                            #        #print(property_tuple)
                            #        field_model.add_x_property(
                            #                property_tuple[0],
                            #                property_tuple[1]
                            #                )
                            #if(isinstance(property_entry, Tuple)):
                            #    field_model.add_x_property(
                            #                property_entry[0],
                            #                property_entry[1]
                            #    )
            else:
                if metadata is not None:
                    property_dict = metadata[field_name] if field_name in metadata else None
                    if property_dict is not None:
                        for key in property_dict:
                            field_model.add_x_property(key, property_dict[key])

            model.add_property(field_name, field_model)

        _magic_attr_pattern = re.compile('^[_]{2}.*[_]{2}$')
        _json_methods = ["to_json", "to_dict", "from_json", "from_dict"]
        funcs = { k : type_.__dict__[k] for k in type_.__dict__.keys() if ( callable(type_.__dict__[k]) and not _magic_attr_pattern.match(k) and k not in _json_methods )  }
        for func_name, func_pointer in funcs.items():
            func_model = self.create_func_definition(func_name)
            
            param_dict = {}
            if hasattr(type_, 'xattr'):
                property_dict = type_.xattr
                if property_dict is not None:
                    if func_name in property_dict:
                        func_attrs = property_dict[func_name]
                        # Assume mixture of function metadata and parameter metadata
                        if isinstance(func_attrs, List):
                            for attr in func_attrs:
                                # multiple function metadata
                                if isinstance(attr, List):
                                    for _attr in attr:
                                        func_model.add_x_property( _attr[0], _attr[1] )    
                                # singular function metadata
                                if isinstance(attr, Tuple):
                                    func_model.add_x_property( attr[0], attr[1] )
                                # parameter metadata
                                if isinstance(attr, Dict):
                                    param_dict = attr
                        # Assume only parameters metadata
                        if isinstance(func_attrs, Tuple):
                            func_model.add_x_property( attr[0], attr[1] )
                        # Assume only function metadata
                        if isinstance(func_attrs, Dict):
                            param_dict = attr
                        
            # function params
            params = func_pointer.__annotations__
            for param_name, param_type in params.items():
                # If it is a string, try to evaluate it as a data type
                if isinstance(param_type, str):
                    try:
                        param_type = eval(param_type)
                    except:
                        print(f'Could not evaluate {param_type}. Continuing as a string...')
                param_model = self.create_model_definition(param_type)
                if param_name in param_dict:
                    param_xattr = param_dict[param_name]
                    # multiple function metadata
                    if isinstance(param_xattr, List):
                        for _attr in param_xattr:
                            param_model.add_x_property( _attr[0], _attr[1] )    
                    # singular function metadata
                    if isinstance(param_xattr, Tuple):
                        param_model.add_x_property( param_xattr[0], param_xattr[1] )
                func_model.add_property(param_name, param_model)

            model.add_function(func_name, func_model)

        return model


def collect_classes_from_module(module: ModuleType) -> Iterable[type]:
    """
    Collects all classes defined in a module. Excludes classes that were
    imported from other modules.

    :param module: The module to search for classes
    :type module: Module
    :return: The found class definitions
    :rtype: Iterable[type]
    """
    return [
        c
        for _, c in inspect.getmembers(module, inspect.isclass)
        if c.__module__ == module.__name__
    ]

def collect_funcs_from_module(module: ModuleType) -> Iterable[type]:
    """
    Collects all functions defined in a module. Excludes functions that were
    imported from other modules.

    :param module: The module to search for classes
    :type module: Module
    :return: The found function definitions
    :rtype: Iterable[type]
    """
    return [
        f
        for _, f in inspect.getmembers(module, inspect.isfunction)
        if f.__module__ == module.__name__
    ]


def parse_arguments():
    from argparse import ArgumentParser

    parser = ArgumentParser()

    parser.add_argument("-m", "--module", help="python module to generate OpenAPI document from", required=True)
    parser.add_argument("-o", "--out", help="OpenAPI output filename", required=True)
    parser.add_argument("-r", "--reference", help="python module to generate OpenAPI document from", action='store_true')
    parser.add_argument("-j", "--json", help="Use this flag to convert to JSON instead of YAML", action='store_true')


    return parser.parse_args()
    
import importlib

args = vars(parse_arguments())
#args = {'module': 'minimal_xattr', 'out': 'minimal_xattr', 'json': False}

import_mod = importlib.import_module(args["module"])

generator = OpenAPIGenerator()
types = collect_classes_from_module(import_mod)
funcs = collect_funcs_from_module(import_mod)
filename = args["out"]
generator.create_api_definition_file(types, funcs, filename, args["json"])

#generator = OpenAPIGenerator()
#types = collect_classes_from_module(pylpg)
#filename = "Examples\\lpg_openapi"
#generator.create_api_definition_file(types, filename)