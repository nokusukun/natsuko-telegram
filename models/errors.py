import pprint

class APIError(Exception):

    def __init__(self, ex, message=None):
        self.expression = ex
        self.message = message
        print("Error: {}".format(ex))
