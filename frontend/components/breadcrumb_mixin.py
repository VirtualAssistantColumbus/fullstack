from abc import ABC, abstractmethod

from .page_ import Page_
from ..utilities.html import Html
from ..framework.locator import url


class BreadcrumbMixin(ABC):
	""" Use this mixin to add a draw_breacrumbs() to any page. """

	@abstractmethod
	def get_previous(self) -> Page_ | None:
		return None
	
	@property
	def full_history(self) -> list[Page_]:
		""" Navigate back through the linked list to reveal the full history. """
		assert isinstance(self, Page_)
		assert isinstance(self, BreadcrumbMixin)
		
		history: list[BreadcrumbMixin] = []
		current_page = self
		while current_page:
			history.insert(0, current_page)
			current_page = current_page.get_previous()
		
		return history #type: ignore

	def show_back_button(self) -> bool:
		return len(self.full_history) > 1

	def draw_breadcrumbs(self) -> Html:
		rendered_breadcrumbs: list[str] = []
		
		# Add back button if needed
		back_button = ""
		if self.show_back_button():
			previous_page = self.get_previous()
			assert previous_page
			back_button = Html(f"""
				<a
					class="
						w-8
						h-8
						flex
						items-center
						justify-center
						rounded-full
						bg-blue-50
						hover:bg-blue-100
						transition-colors
						duration-200
						group
						mr-4
						border-r
						border-gray-200
						pr-4
					"
					href="{ url(previous_page) }"
				>
					<svg class="w-5 h-5 text-blue-600 group-hover:text-blue-700 transition-colors duration-200" fill="none" stroke="currentColor" viewBox="0 0 24 24" style="transform: translateX(8px);">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18"/>
					</svg>
				</a>
			""")
		
		for idx, page_ in enumerate(self.full_history):
			# Handle the first frame
			if idx == len(self.full_history) - 1:
				rendered_breadcrumb = Html(f"""
					<span class="text-gray-900 font-bold text-lg">
						{ page_.breadcrumb_title() }
					</span>
				""")
			# Handle other frames
			else:
				rendered_breadcrumb = Html(f"""
					<a 
						href="{ url(page_) }"
						class="
							text-blue-600
							font-medium
							text-lg
							hover:text-blue-700
							transition-colors
							duration-150
						"
					>
						{ page_.breadcrumb_title() }
					</a>
				""")
			rendered_breadcrumbs.append(rendered_breadcrumb)
		
		separator = Html(f"""<span class="text-gray-500 flex items-center"><svg class="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg"><path fill-rule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clip-rule="evenodd"></path></svg></span>""")
		breadcrumb_content = separator.join(rendered_breadcrumbs)
		
		return Html(f"""
			<div class="flex-1 ml-4 relative" x-data="{{
				isMobile: window.innerWidth < 768,
				init() {{
					window.addEventListener('resize', () => {{
						this.isMobile = window.innerWidth < 768;
					}});
				}}
			}}">
				<nav class="flex items-center justify-center" aria-label="Breadcrumb">
					<div class="flex items-center" style="transform: translateX(-{self.show_back_button() and '2rem' or '0'});">
						{ back_button }
						<div class="flex items-center overflow-x-auto">
							<!-- Mobile view - only show current page -->
							<div x-show="isMobile" class="flex items-center">
								{ rendered_breadcrumbs[-1] if rendered_breadcrumbs else "" }
							</div>
							
							<!-- Desktop view - show full breadcrumb trail -->
							<div x-show="!isMobile" class="flex items-center space-x-2">
								{ breadcrumb_content }
							</div>
						</div>
					</div>
				</nav>
			</div>
		""")
	
