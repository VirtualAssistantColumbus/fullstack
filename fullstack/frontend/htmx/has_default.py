from inspect import Parameter


def parameter_has_default(parameter: Parameter):
    """ Returns whether a function 'parameter has as default value set. """
    return parameter.default is not Parameter.empty