"""
Documentation:
A very clever (if I do say so myself) way to define a function which is "client-callable," meaning we can directly use this function in our views, with static type checking.
The way this works is that when you define an endpoint, this decorator takes in the endpoint and actually creates TWO functions: one which generates HTMX attributes which can be placed on any html element that you want to make interactive, and a second function which deserializes the values from the HTMX request and passes them back into the original function. This means that the function which is actually returned from the decorator is actually just an HTMX generator which will submit its values (and client input values) to the decoding function and then to the original function.

- Static arguments are those which we can specify ahead of time on the server side. For example, what page we want a button to redirect to, or where we want form data to submit to.
- Dynamic arguments are those that are specified by user input.
- You access the client's URL within any post request using Flask's g variable

All static arguments will be serialized into an hx-vals which will in turn be sent *back* to the server when the event is triggered.

In this way, we can basically define a function which is "client-callable".

All dynamic arguments will be sent back as kwargs which maps html element name -> element input value. (Just like how form data is typically returned.)

Note about type-hinting: The reason type-hinting still works is because Python's static type checker assumes that a decorator will not modify the method signature of the decorated function.

All htmxmethod() routes are registered on the API_HOST defined in environment variables.
"""

from dataclasses import dataclass
import inspect
import json
import sys
from types import MappingProxyType
from typing import Any, Callable, ForwardRef, get_args
import html

from flask import Response, make_response, request, Request
from flask_login import current_user

from ...typing.bsonable_dataclass.bsonable_dataclass import BsonableDataclass
from ...typing.fields.field_path import FieldPath
from ...typing.serialization.bson_to_type_expectation import bson_to_type_expectation
from ...typing.registration.type_expectation import TypeExpectation
from ...typing.registration.type_info import TypeInfo
from ...typing.registration.get_type_expectation_from_type_annotation import get_type_expectation_from_type_annotation
from ...utilities.validation_error import ValidationError
from ...utilities.setup_error import SetupError
from ..components.page_ import Page_

from ..components.alerts import snackbar_error_message_
from ..components.element_ import Viewable, draw
from ..htmx.htmx_response import make_htmx_response
from ..htmx.client_supplied_field import BY_PARAMETER_NAME, DataLookupBuilder, Lookup, LookupLocation, parameter_is_raw_client_supplied_json, parameter_is_client_supplied_field
from ..framework.client_url import stash_client_url_into_g
from ..components.page_context import DATA_FRAME_CONTAINER_PAGE_FIELD_PATH, FrameContext, PageContext, stash_page_context_into_g
from ..framework.html_attr import HtmlAttr

from .unflatten import unflatten
from .has_default import parameter_has_default
from ..framework.route import Method, locator_route
from ..framework.locator import Locator, url
from ..utilities.map_list import draw_list
from .none_value import from_nullable_client_value


# Declare the return types that a post() function is allowed to return.
# Each return type should also have a corresponding transformation function that should be applied before handing the return type up to Flask.

class ElementList_(list):
	pass

# from web_framework.containers.page_ import Page_
valid_return_types: dict[type, Callable] = {
	Response: lambda x: x,
	
	# For Pages, also send back an update to the url
	# TODO: Do I need this? Isn't returning replaceState within the page sufficient? But I feel like there was a reason I needed this. It might have been something to do with return a Page_ in response to an HTMX request?
	Page_: lambda x: make_response(draw(x), 200, {"HX-Push-Url": url(x)}),
	
	Viewable: lambda x: draw(x),
	str: lambda x: x,
	
	# Return more than one element at the same time
	ElementList_: lambda x: make_response(draw_list(x))
}

SERVER_SUPPLIED_DATA = "server_supplied_data"
SERVER_SUPPLIED_LOOKUP_DATA = "server_supplied_lookup_data"
CLIENT_SUPPLIED_JS_DATA = "client_supplied_js_data"
PAGE_CONTEXT_DATA = "page_context_data"

#region: Helpers
def encode_server_supplied_parameters_to_hx_vals(
		server_supplied_parameters_dict: dict[str, Any],
		server_supplied_lookup_parameters_dict: dict[str, Any],
		page_context_data_eval_js_dict: dict[str, str],
		client_supplied_data_eval_js_dict: dict[str, str]
	) -> str:
	""" Encodes a list of JSON arguments into a single string that can be assigned to hx-vals. """
	output = f"""js:{{
	   "{SERVER_SUPPLIED_DATA}": {html.escape(json.dumps(server_supplied_parameters_dict, indent=4))},
	   "{SERVER_SUPPLIED_LOOKUP_DATA}": {html.escape(json.dumps(server_supplied_lookup_parameters_dict, indent=4))},
	   "{PAGE_CONTEXT_DATA}": {{
	"""

	# Add page context data JS expressions
	output += "\n"
	for data_key, data_eval_js in page_context_data_eval_js_dict.items():
		output += f'\t\t"{data_key}": '
		output += data_eval_js
		output += ",\n"
	
	if output[-2:] == ",\n":
		output = output.rstrip(",\n")
		output += "\n"
	
	output += "\t},"  # Close the page context data dict
	output += f'\n\t"{CLIENT_SUPPLIED_JS_DATA}": {{'  # Open client supplied data dict
	
	# Add client supplied data JS expressions
	if client_supplied_data_eval_js_dict:
		output += "\n"
		for data_key, data_eval_js in client_supplied_data_eval_js_dict.items():
			output += f'\t\t"{data_key}": '
			output += data_eval_js
			output += ",\n"
		
		if output[-2:] == ",\n":
			output = output.rstrip(",\n")
			output += "\n"

	output += "\t}"  # Close the client-supplied js data dict
	output += "\n}"  # Close the parent dict
	return output

@dataclass
class DecodedRequest:
	server_supplied_data: dict[str, Any]
	""" Json """
	server_supplied_lookup_data: dict[str, Any]
	""" Json """
	client_supplied_js_data: dict[str, Any]
	""" Json """
	client_supplied_form_data: dict[str, Any]
	""" Form data unflattened. """
	client_url: str
	""" The current URL of the client. """
	page_context_js_data: dict[str, Any]

def decode_request(request: Request) -> DecodedRequest:
	""" The form values from the client will include a mix of server-supplied parameters (echoed back) and client-supplied parameters.

	This function will separate server-supplied vs. client-supplied form fields and decode them into json.
	"""
	request_data = dict(request.form)
	
	# Get the client URL
	client_url = request.headers.get('HX-Current-URL', '')
	
	# Extract page context data
	page_context_js_data_values_dict = json.loads(request_data.pop(PAGE_CONTEXT_DATA))

	# Extract the various hx-vals data parts
	# Unescape the data and then load it as json
	server_supplied_json_values_dict = json.loads(html.unescape(request_data.pop(SERVER_SUPPLIED_DATA)))
	server_supplied_lookup_json_values_dict = json.loads(html.unescape(request_data.pop(SERVER_SUPPLIED_LOOKUP_DATA)))
	client_supplied_js_data_values_dict = json.loads(request_data.pop(CLIENT_SUPPLIED_JS_DATA))
	
	# All remaining request fields will have come from an html form element
	client_supplied_form_data: dict[str, str] = unflatten(**request_data)
	
	# Replace NONE_VALUE with None
	def replace_none_value(d: dict) -> dict:
		""" Recursively replace NONE_VALUE with None in a dictionary. """
		for key, value in d.items():
			if isinstance(value, dict):
				d[key] = replace_none_value(value)
			else:
				d[key] = from_nullable_client_value(d[key])
		return d
	page_context_js_data_values_dict = replace_none_value(page_context_js_data_values_dict)
	client_supplied_js_data_values_dict = replace_none_value(client_supplied_js_data_values_dict)
	client_supplied_form_data = replace_none_value(client_supplied_form_data)

	return DecodedRequest(
		server_supplied_data=server_supplied_json_values_dict, 
		server_supplied_lookup_data=server_supplied_lookup_json_values_dict,
		client_supplied_js_data=client_supplied_js_data_values_dict,
		client_supplied_form_data=client_supplied_form_data,
		client_url=client_url,
		page_context_js_data=page_context_js_data_values_dict
	)
# endregion

@dataclass
class FuncInfo:
	user_callable_parameters: MappingProxyType[str, inspect.Parameter]
	return_type_expectation: TypeExpectation
	unbound_func: Callable
	cls: type[BsonableDataclass]
	is_instance_method: bool = False
	is_class_method: bool = False

def public_htmxmethod(*,
		 show_loading: bool = True,
		 confirm: str | None = None, # If you want to display a confirmation pop up before submitting the request
		 **decorator_options
		):
	return htmxmethod(
		login_required=False,
		show_loading=show_loading,
		confirm=confirm,
		**decorator_options
	)

def htmxmethod(*,
		 login_required: bool = True, # By default login_required = True. This is VERY IMPORTANT. Do not modify this, as most of your routes rely on this.
		 show_loading: bool = True,
		 confirm: str | None = None, # If you want to display a confirmation pop up before submitting the request
		 **decorator_options
		):
	
	def decorator(func):
		# Determine method type and get the unbound function
		is_class_method = isinstance(func, classmethod)
		is_instance_method = (
			not isinstance(func, (classmethod, staticmethod)) and
			list(inspect.signature(func).parameters.keys())[0] == 'self'
		)

		# Extract the underlying function
		if is_class_method:
			unbound_func = func.__func__  # Get the raw function from classmethod
		elif is_instance_method:
			unbound_func = func  # Just use the original function
		else:
			unbound_func = func

		# Use the unbound function for parameter inspection
		func_signature = inspect.signature(unbound_func)
		func_parameters = func_signature.parameters
		func_return_type_expectation = get_type_expectation_from_type_annotation(
			func_signature.return_annotation, 
			resolve_forward_refs=True
		)
		if not issubclass(func_return_type_expectation.type_info.type_, tuple(valid_return_types.keys())):
			# Validate that the function is annotated to return an appropriate type
			raise SetupError(f"The functions '{func.__name__}' has an invalid annotated return type '{func_signature.return_annotation}'.")

		# Cached func_info
		func_info_cache = None
		def get_func_info() -> FuncInfo:
			""" Wrap this to avoid circular imports when decorating methods with @post() """
			nonlocal func_info_cache
			if func_info_cache is not None:
				return func_info_cache

			# Get the class (delayed until needed)
			class_name = func.__qualname__.split('.')[0]
			cls = getattr(sys.modules[func.__module__], class_name)

			# Filter out cls and self parameters
			filtered_parameters = MappingProxyType({
				name: param 
				for name, param in func_parameters.items() 
				if name not in ('cls', 'self', 'self_dict')
			})

			func_info_cache = FuncInfo(
				unbound_func=unbound_func,
				user_callable_parameters=filtered_parameters,  # Use filtered parameters
				return_type_expectation=func_return_type_expectation,
				cls=cls,
				is_instance_method=is_instance_method,
				is_class_method=is_class_method
			)
			return func_info_cache

		# 1. Construct API Route and register it with Flask
		def api_route() -> Response:
			""" The API route which the HTMX will call. Wraps the passed in func — extracting and decoding the arguments from request.form before passing them into func. """
			from ...typing.serialization.bson_to_type_annotation import bson_to_type_annotation
			
			# Get function info and class
			func_info = get_func_info()

			if login_required and not current_user.is_authenticated:
				return make_response(f"Authentication is required to access the endpoint '{ func_info.unbound_func.__name__ }'.", 401)
			
			# The request json will include a mix of sever-supplied parameters (which have been echoed back) and client-supplied parameters
			decoded_request = decode_request(request)
			
			# Stash the client url into Flask's g parameter (this is a request-scoped global)
			# We use g instead of a method parameter because there is no parameter to pass in when you call the function
			stash_client_url_into_g(decoded_request.client_url)

			# Extract page context (where the request came from) and stash it into Flask's g
			frame_container_page_field_path = decoded_request.page_context_js_data[DATA_FRAME_CONTAINER_PAGE_FIELD_PATH]
			field_path = FieldPath(frame_container_page_field_path)
			page_context = PageContext(frame_context=FrameContext(page_field_path=field_path))
			stash_page_context_into_g(page_context)
			
			route_parameter_values_dict: dict = {}
			
			# For classmethods, manually pass cls as first argument
			if func_info.is_class_method:
				route_parameter_values_dict['cls'] = func_info.cls
			
			# For instance methods, reconstruct self from self_dict
			elif func_info.is_instance_method:
				if 'self_dict' not in decoded_request.server_supplied_data:
					raise ValueError("Missing server-supplied data for 'self_dict' parameter.")
				self_dict = decoded_request.server_supplied_data['self_dict']
				instance = func_info.cls.from_bson(self_dict, None)
				route_parameter_values_dict['self'] = instance
			
			# Process remaining parameters
			for parameter_name, parameter in func_info.user_callable_parameters.items():
				# Handle GetClientSuppliedField parameters
				# For these parameters, we should expect two values from the request:
				# 1) A server-supplied value of type Lookup which specifies the form field name we should look for in the client-supplied json dict
				# 2) A client-supplied value for a field with the name and location specified in the Lookup
				if parameter_is_client_supplied_field(parameter):
					# For a client-supplied parameter, we need to first find the server-supplied lookup parameter to tell us how to lookup the corresponding client-side parameter.
					# Lookup determines how we should try to resolve the route parameter value.
					if not parameter_name in decoded_request.server_supplied_lookup_data:
						raise ValueError(f"Missing server-supplied lookup data for parameter '{parameter_name}'. Unable to lookup field.")
					lookup_data = decoded_request.server_supplied_lookup_data[parameter_name]
					lookup = bson_to_type_expectation(lookup_data, TypeExpectation(TypeInfo(Lookup, None), False), None)
					if not isinstance(lookup, Lookup):
						raise ValueError(f"Server-supplied parameters for client-supplied parameters should be of type Lookup.")

					# Determine what name we should use to look up our data
					if lookup.lookup_name == BY_PARAMETER_NAME:
						lookup_name = parameter_name
					else:
						lookup_name = lookup.lookup_name
					
					# Determine the actual type annotation within Annotated[]
					type_annotation = get_args(parameter.annotation)[0]
					assert type_annotation is not None and not isinstance(type_annotation, ForwardRef)
					
					# Handle the lookup differently depending on the location
					if lookup.lookup_location is LookupLocation.DATA:
						if not lookup_name in decoded_request.client_supplied_js_data:
							raise ValueError(f"Could not find data for route parameter '{parameter_name}' under the lookup field name '{lookup_name}' within client-submitted data.")
						data = decoded_request.client_supplied_js_data[lookup_name]
						obj = bson_to_type_annotation(data, type_annotation, None, resolve_forward_refs=True)
						route_parameter_values_dict[parameter_name] = obj
					
					elif lookup.lookup_location is LookupLocation.FORM:
						if not lookup_name in decoded_request.client_supplied_form_data:
							raise ValueError(f"Could not find data for route parameter '{parameter_name}' under the lookup field name '{lookup_name}' within client-submitted form values.")
						data = decoded_request.client_supplied_form_data[lookup_name]
						
						obj = bson_to_type_annotation(data, type_annotation, None, 
													  coerce_str_values=True, # HTML form fields always send values as strings, setting allow_coercion
													  resolve_forward_refs=True)
						
						route_parameter_values_dict[parameter_name] = obj

					else:
						raise ValueError("Invalid LookupLocation supplied.")

				# For RawClientJson param, just assign the raw client-supplied json dict into the parameter
				elif parameter_is_raw_client_supplied_json(parameter):
					route_parameter_values_dict[parameter_name] = decoded_request.client_supplied_form_data

				# All other func parameters should be server-supplied
				else:
					if not parameter_name in decoded_request.server_supplied_data:
						raise ValueError(f"Missing server-supplied data for route parameter '{parameter_name}'.")
					server_supplied_parameter_json_value = decoded_request.server_supplied_data[parameter_name]
					server_supplied_parameter_value = bson_to_type_annotation(server_supplied_parameter_json_value, parameter.annotation, None, resolve_forward_refs=True) # These parameters should have regular annotations
					route_parameter_values_dict[parameter_name] = server_supplied_parameter_value
				
			# Call the function (no need to handle classmethod specially)
			func_return_value = func_info.unbound_func(**route_parameter_values_dict)
			
			# Validate the function return value against the return annotation
			func_info.return_type_expectation.validate(func_return_value, None)
			
			# Apply the return type's transformation function before sending up to Flask
			# Determine the right transformation function to use
			transformation_func = None
			for valid_class, class_transformation_func in valid_return_types.items():
				if isinstance(func_return_value, valid_class):
					transformation_func = class_transformation_func
					break
			if transformation_func is None:
				raise ValueError("Unable to find matching transformation function.")
			
			output = transformation_func(func_return_value)
			return output

		# Rename the function (to prevent conflicts) and then register it as a route
		def wrapped_api_route() -> Response:
			is_debugging = sys.gettrace() is not None
			try:
				return api_route()
			
			# Always catch and display ValidationErrors. Notably, these can occur if SafeStr raises a ValidationError while constructing itself.
			except ValidationError as e:
				return make_htmx_response(draw(snackbar_error_message_(e.message)))
			
			except Exception as e:
				# TODO: Consider adding configurable error handling. You used to have this:
					# if is_debugging or shared.environment.runtime_environment is RuntimeEnvironment.LOCAL:
					# 	# Reraise the error if we're debugging so we can see it
					# 	raise e
					# else:
					# 	# Return an error page
					# 	# Note this works by swapping out the "main" div
					# 	return make_htmx_response(draw(ErrorPage_(public_message="An unexpected error occurred.", hidden_message=str(e))))
				return make_htmx_response(draw(snackbar_error_message_("An unexpected error occurred.")))

		# Assign route properties
		
		# Generate a route name
		# If the decorator is used on a staticmethod of a class, prepend the class name
		qualname_parts = func.__qualname__.split('.')
		class_name = qualname_parts[-2] if len(qualname_parts) > 1 else None
		if class_name:
			api_route_name = f"{class_name}_{func.__name__}"
		else:
			api_route_name = f"{func.__name__}"
		
		wrapped_api_route.__name__ = api_route_name
		
		# Register the route on the api host
		from .. import api_host
		api_locator = Locator(host=api_host, path=f"/{api_route_name}")
		locator_route(locator=api_locator, methods=[Method.POST])(wrapped_api_route)

		# 2. Construct HTMX generator function. This is what we will ultimately return so that we can "call" the API route directly from our view/template code.
		def htmx_generator(*args, **kwargs) -> HtmlAttr:
			""" A function that generates client-side HTMX to call the API route. 
			Performs type-checking on each passed in argument to make sure it matches the argument annotation. """
			from ...typing.serialization.obj_to_bson import obj_to_bson

			# Request page context
			page_context_data_eval_js_dict = {
				DATA_FRAME_CONTAINER_PAGE_FIELD_PATH: """(function(evt) { 
					try {
						let el = evt?.target;
						if (!el) el = this;
						if (!el || !(el instanceof Element)) return null;
						const container = el.closest("[data-frame-container]");
						return container ? container.getAttribute("data-frame-container-page-field-path") : null;
					} catch (e) {
						console.error("Error getting frame container path:", e);
						return null;
					}
				})(event)"""
			}

			# Get server and client supplied parameters
			client_supplied_data_eval_js_dict: dict[str, str] = {}
			""" A dictionary mapping data keys -> the js we want to evaluate and assign to those keys. """

			server_supplied_parameters_dict = {}
			server_supplied_lookup_parameters_dict = {}

			# Get function info and class
			func_info = get_func_info()
			
			# For instance methods, we need to extract self and serialize it
			if func_info.is_instance_method:
				if not args:
					raise ValueError("Instance method called without 'self' parameter")
				
				# Get the instance, serialize it, and add it to the server-supplied dict
				instance = args[0]
				self_dict = instance.to_bson()
				server_supplied_parameters_dict['self_dict'] = self_dict
				
				# Remove the self argument from args
				args = args[1:]
			
			# For class methods, cls is not passed into args for classmethod calls
			
			# Process remaining parameters
			for idx, (parameter_name, parameter) in enumerate(func_info.user_callable_parameters.items()):
				
				type_expectation = get_type_expectation_from_type_annotation(parameter.annotation, resolve_forward_refs=True)
				
				# If a parameter is meant to come from the form, it won't be supplied yet. The HTMX generator is called when the html is generated for the page. FromForm parameters will be submitted by the client.
				
				# Look for the argument from either arg or kwargs
				if idx < len(args):
					# If there are positional arguments, they must match against the parameter by order
					parameter_value = args[idx]
				elif parameter_name in kwargs:
					# If it's not in positional argumens, see if its in kwargs
					parameter_value = kwargs[parameter_name]
				elif parameter_has_default(parameter):
					# If a parameter value is not supplied, see if the parameter has a default value
					parameter_value = parameter.default
				else:
					# Otherwise, raise an error
					raise ValueError(f"Error generating HTMX for func {api_route.__name__}. No value supplied for '{parameter_name}'.")
				
				# If the parameter has a type annotation, validate that the argument provided matches the annotation. This will catch errors when the page is created.
				if parameter_is_raw_client_supplied_json(parameter):
					# We don't need to do anything with this parameter
					pass
				elif parameter_is_client_supplied_field(parameter):
					# For DataLookupBuilder, we need to extract the js and render that to the view, then send the Lookup over the wire.
					if isinstance(parameter_value, DataLookupBuilder):
						data_lookup_builder = parameter_value
						
						# Determine the lookup name
						if data_lookup_builder.lookup.lookup_name == BY_PARAMETER_NAME:
							lookup_name = parameter_name
						else:
							lookup_name = data_lookup_builder.lookup.lookup_name
						
						# Assign the js that we want to evaluate to the lookup name
						client_supplied_data_eval_js_dict[lookup_name] = data_lookup_builder.js
						
						# Send the lookup to be echoed back
						lookup_json_value = obj_to_bson(data_lookup_builder.lookup)
						server_supplied_lookup_parameters_dict[parameter_name] = lookup_json_value
					
					elif isinstance(parameter_value, Lookup):
						lookup = parameter_value
						assert lookup.lookup_location is LookupLocation.FORM # Regular lookups should be form lookups
						lookup_json_value = obj_to_bson(lookup)
						server_supplied_lookup_parameters_dict[parameter_name] = lookup_json_value
					
					else:
						raise ValueError("When using the HTMX generator, you must supply lookup instructions as the value of a ClientSuppliedField. Typically you would do this using the form_lookup() or data_lookup() factory function.")
				# All other parameters are server-supplied parameters
				else:
					# For server-supplied parameters, we can immediately validate whether they conform to the annotated type expectation, as these will be echoed back.
					type_expectation.validate(parameter_value, None)
					parameter_json_value = obj_to_bson(parameter_value)
					server_supplied_parameters_dict[parameter_name] = parameter_json_value

			html_attr = HtmlAttr(
				# Always make the HTMX request use a relative URL. The request should go to the same origin that it originates from.
				# So if we're on home.rhythmscheduler.com we should hit home.rhythmscheduler.com/api/xyz
				# (That's why we register all HTMX routes on domain and subdomain, so it can respond to both.)
				# This way, we don't have to worry about cross origin issues.
				# We had an issue where HTMX would not honor Hx-Push-Url or Hx-Redirect for cross origin requests.
				hx_post=api_locator.to_full_url(),
				hx_vals=encode_server_supplied_parameters_to_hx_vals(
					server_supplied_parameters_dict=server_supplied_parameters_dict, 
					server_supplied_lookup_parameters_dict=server_supplied_lookup_parameters_dict,
					page_context_data_eval_js_dict=page_context_data_eval_js_dict,
					client_supplied_data_eval_js_dict=client_supplied_data_eval_js_dict
				),
				hx_swap="none", # Set hx-swap to be none by default, so that the triggering element is not changed. (We only use oob swaps.)
			)

			# Add client-side behavior
			from ..framework.framework import LoadingIndicator
			if show_loading:
				html_attr.update(LoadingIndicator.get_loading_attr())
			if confirm:
				html_attr.update(HtmlAttr(hx_confirm=confirm))

			return html_attr
		
		return htmx_generator
	
	return decorator