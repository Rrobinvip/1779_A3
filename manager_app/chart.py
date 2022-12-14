from manager_app.helper import current_datetime


class Chart:
    hitRate = None
    numberOfItem = None
    totalSize = None
    numberOfRequest = None
    missRate = None

    def __init__(self):
        self.hitRate = 0.0
        self.numberOfItem = 0.0
        self.totalSize = 0.0
        self.numberOfRequest = 0.0
        self.missRate = 0.0
    
    def set_hitRate(self, hitRate):
        self.hitRate = hitRate
    
    def get_hitRate(self):
        return self.hitRate
    
    def set_number_of_item(self, numberOfItem):
        self.numberOfItem = numberOfItem
    
    def get_number_of_item(self):
        return self.numberOfItem
    
    def set_total_size(self, totalSize):
        self.totalSize = totalSize
    
    def get_total_size(self):
        return self.totalSize
    
    def set_number_of_request(self, numberOfRequest):
        self.numberOfRequest = numberOfRequest
    
    def get_number_of_request(self):
        return self.numberOfRequest
    
    def set_missRate(self, missRate):
        self.missRate = missRate
        
    def get_missRate(self):
        return self.missRate
    
class DataAggregation():
    data_list = None
    
    def __init__(self):
        self.data_list = []
        
    def add_entry(self, data):
        if len(self.data_list) == 30:
            self.data_list.pop()
        
        self.data_list.insert(0, data)
        
    def get_data(self):
        return self.data_list