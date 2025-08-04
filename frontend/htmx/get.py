import inspect
import json
from typing import Any

from flask import Response, make_response, request

from flask_login import current_user

from .. import routes
from ...typing.registration.get_type_expectation_from_type_annotation import get_type_expectation_from_type_annotation
from ..framework.url_for_func import url_for_func
from ..framework.html_attr import HtmlAttr


## Deprecate? This is the "get" version of htmxmethod, but it needs to either be updated to match htmxmethod, or removed.

def get(rule: str | None = None, *, login_required: bool = True):

	def decorator(func):
		# Assign route parameters
		api_route_name = f"api_{func.__name__}"
		nonlocal rule
		if rule is None: # Automatically set the rule (aka the api URL) to be /api/ + the function name if we didn't explicitly set a rule.
			rule = f"/api/{func.__name__}"
		options = { "methods": ["GET"] } # Set default options
		
		# Take in the function
		func_parameters = inspect.signature(func).parameters
		# TODO: Isolate static parameters

		# 1. Construct API Route and register it with Flask
		def api_route() -> Response:
			""" The API route which the HTMX will call. Wraps the passed in func — extracting anddecoding the arguments from request.form before passing them into func. """
			from ...typing.serialization.bson_to_type_annotation import bson_to_type_annotation
			
			if login_required and not current_user.is_authenticated:
				return make_response(f"Authentication is required to access the endpoint '{rule}'.", 401)
			
			# Extract arguments from the request
			query_params = dict(request.args)
			
			# Iterate through parameters in the method signature and look for the corresponding static arg for each. Deserialize each based on the method signature.
			static_args: dict[str, Any] = {}
			for parameter_name, parameter in func_parameters.items():
				# Skip the **kwargs parameter which is used for dynamic args
				if parameter.kind is inspect._ParameterKind.VAR_KEYWORD:
					continue
				if not parameter_name in query_params:
					raise ValueError(f"Missing parameter: {parameter_name}.")
				# Retrieve and remove the static query parameters
				argument_url_value = query_params.pop(parameter_name)
				argument_json_value = json.loads(argument_url_value)
				static_arg = bson_to_type_annotation(argument_json_value, parameter.annotation, None)
				static_args[parameter_name] = static_arg
			
			# Pass the deserialized arguments into the original function
			return func(**static_args, **query_params)
		
		# Rename the function (to prevent conflicts) and then register it as a route
		api_route.__name__ = f"api_{func.__name__}"
		routes[api_route] = [(rule, options)]

		# 2. Construct HTMX generator function. This is what we will ultimately return so that we can "call" the API route directly from our view/template code.
		def url_generator(*args, **kwargs) -> HtmlAttr:
			""" A function that generates client-side HTMX to call the API route. 
			Performs type-checking on each passed in argument to make sure it matches the argument annotation. """
			from ...typing.serialization.obj_to_bson import obj_to_bson

			query_params: dict[str, str] = {}
			for idx, (parameter_name, parameter) in enumerate(func_parameters.items()):
				# At the moment, the rule is to use **kwargs for dynamic arguments. inspect designates a special "kind" to this argument -> _ParameterKind.VAR_KEYWORD.
				if parameter.kind is inspect._ParameterKind.VAR_KEYWORD:
					continue
				
				# First look for the parameter in args
				if idx <= len(args) - 1:
					static_arg = args[idx]
				# Otherwise, look for it in kwards
				else:
					if parameter_name not in kwargs:
						raise ValueError(f"Argument {parameter_name} was not passed into this function as either a arg or a kwarg.")
					static_arg = kwargs[parameter_name]
				
				# Validate that the argument provided matches the annotation. This will help us catch errors at "compile time" (i.e. when the page is created rather than waiting until we hit this endpoint to raise an error).
				type_expectation = get_type_expectation_from_type_annotation(parameter.annotation)
				type_expectation.validate(static_arg, None)
				
				arg_json_value = obj_to_bson(static_arg)
				arg_url_value = json.dumps(arg_json_value)
				query_params[parameter_name] = arg_url_value

			url = url_for_func(api_route, **query_params) # url_for will automatically url-encode query parameters
			return HtmlAttr(hx_get=url)
		
		return url_generator
	
	return decorator


