import json

class Result(object):
    def __init__(self,code,data,message):
        self.code = code
        self.data = data
        self.message = message
    def toJson(self):
        return json.dumps(self)
    def toDict(self):
        return self.__dict__