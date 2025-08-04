from typing import Any


class HtmlAttr:
	""" NOTE: None in this context indicates an unset attribute. """

	def __init__(self, *, id: str | None = None, class_: str | None = None, href: str | None = None,
				 name: str | None = None, value: str | None = None, required: bool | None = None,
				 placeholder: str | None = None, 
				 hx_include: str | None = None, hx_vals: str | None = None, 
				 hx_post: str | None = None, hx_get: str | None = None,
				 hx_trigger: str | None = None, hx_target: str | None = None, 
				 hx_headers: str | None = None,
				 hx_swap: str | None = None, hx_push_url: str | None = None, hx_indicator: str | None = None,
				 hx_confirm: str | None = None,
				 x_data: str | None = None,
				 **kwargs: str | bool):
		self.id = id
		self.class_ = class_
		self.href = href
		self.name = name
		self.value = value
		self.required = required
		self.placeholder = placeholder
		
		self.hx_include = hx_include
		self.hx_vals = hx_vals
		self.hx_get = hx_get
		self.hx_post = hx_post
		self.hx_trigger = hx_trigger
		self.hx_headers = hx_headers # Headers to be sent back with the HTMX request
		self.hx_target = hx_target
		self.hx_swap = hx_swap
		self.hx_push_url = hx_push_url
		self.hx_indicator = hx_indicator # Set this value to the id of the element you want to show while a request is loading. That same element must also have the htmx-idicator class on it.
		self.hx_confirm = hx_confirm
		self.x_data = x_data
		
		self.__dict__.update(kwargs)

	def __str__(self):
		output = []
		for attr_name, attr_value in self.as_dict().items():
			# For booleans, just place the attr_name (i.e. for attrs like 'required')
			if isinstance(attr_value, bool):
				if attr_value:
					output.append(f"{attr_name}")
			# For others, place name = 'value'
			else:
				output.append(f"{attr_name}='{attr_value}'") # Note that you just must enclose the attr value in single quotes, because htmx attributes like hx-vals require json within the value to use double quotes.
		return " ".join(output)
	
	def as_dict(self) -> dict[str, Any]:
		output = {}
		for attr_name, attr_value in self.__dict__.items():
			if attr_value is not None:
				# Remap field names to conform to html standards
				if attr_name == "class_":
					attr_name = "class"
				attr_name = attr_name.replace("_", "-")
				output[attr_name] = attr_value
		return output
	
	def __add__(self, other: 'HtmlAttr') -> 'HtmlAttr':
		return self.update(other, allow_override=False)
	
	def update(self, other: 'HtmlAttr | Any', *, allow_override: bool = False) -> 'HtmlAttr':
		""" Updates self with the attributes of other and then returns self.
		Set override = True if you'd like other to be able to override attributes that are already set in self. """
		for other_field_name, other_field_value in other.__dict__.items():
			# Skip None values as these are unset attributes
			if other_field_value is None:
				continue
			if other_field_name in self.__dict__ and self.__dict__[other_field_name] is not None:
				if not allow_override:
					raise ValueError(f"Field '{other_field_name}' is specified in both HtmlAttr instances.")
			setattr(self, other_field_name, other_field_value)
		return self

def combine_attr(*args: HtmlAttr) -> HtmlAttr:
	output = HtmlAttr()
	for attr in args:
		if not isinstance(attr, HtmlAttr):
			raise ValueError
		output += attr
	return output