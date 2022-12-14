import boto3

class Scaler:
    '''
    This calss stores the config of the auto scaler
    '''
    max_miss_rate_threshold = None
    min_miss_rate_threshold = None
    ratio_expand = None
    ratio_shrink = None

    def __init__(self):
        '''
        Initialize the scaler object
        It will initailze as manual mode, max miss rate is 1, min miss rate is 0.0, expand ratio and shrink ratio
        are both 1
        '''
        self.max_miss_rate_threshold = 1.0
        self.min_miss_rate_threshold = 0.0
        self.ratio_expand = 1
        self.ratio_shrink = 1
    
    def set_max_miss_rate_threshold(self, max_miss_rate):
        '''
        This function will set the max miss rate threshold
        '''
        self.max_miss_rate_threshold = max_miss_rate
    
    def get_max_miss_rate_threshold(self):
        '''
        This function return the max miss rate threshold
        '''
        return self.max_miss_rate_threshold
    
    def set_min_miss_rate_threshold(self, min_miss_rate):
        '''
        This function set the min miss rate threshold
        '''
        self.min_miss_rate_threshold = min_miss_rate
    
    def get_min_miss_rate_threshold(self):
        '''
        This function return the min miss rate threshold
        '''
        return self.min_miss_rate_threshold
    
    def set_expand_ratio(self, expand_ratio):
        '''
        This function set the expand ratio
        '''
        self.ratio_expand = expand_ratio
    
    def get_expand_ratio(self):
        '''
        This function return the expand ratio
        '''
        return self.ratio_expand
    
    def set_shrink_ratio(self, shrink_ratio):
        '''
        This function set the shrink ratio
        '''
        self.ratio_shrink = shrink_ratio
    
    def get_shrink_ratio(self):
        '''
        This function return the shrink ratio
        '''
        return self.ratio_shrink


    
    
