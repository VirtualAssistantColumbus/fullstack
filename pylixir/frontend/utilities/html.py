class Html(str):
    pass

    def __add__(self, other: 'Html') -> 'Html':
        """ Concatenates two Html objects together, returning a new Html object. """
        return Html(str(self) + str(other))