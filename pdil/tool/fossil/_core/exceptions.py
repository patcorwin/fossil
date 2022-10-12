


class FossilMultiError(Exception):

    def __init__(self):
        Exception.__init__(self)
        self.errors = []

    def append(self, message, tracebackStr):
        self.errors.append( (message, tracebackStr) )

    def __bool__(self):
        return bool(self.errors)
        
    __nonzero__ = __bool__ # pyton 2.7 uses __nonzero__, __bool__ comes along in 3