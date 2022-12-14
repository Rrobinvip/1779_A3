import hashlib
REGION_NUMBER = 16

def key_to_md5(key):
    '''
    This function will conver a given key to md5 (upper caeses.)
    '''
    hash_result = hashlib.md5(key.encode())
    hash_result = hash_result.hexdigest()
    if len(hash_result) == 31:
        hash_result = '0'+hash_result
    return hash_result.upper()

class PoolHashingAllocator():
    region = None
    pattern = None
    region_starting_point = None
    current_number_nodes = None

    def __init__(self, number_nodes):
        self.region = REGION_NUMBER
        self.pattern = []
        self.region_starting_point = ['0','1','2','3','4','5','6','7','8','9','A','B','C','D','E','F']
        self.current_number_nodes = number_nodes

    def set_number_nodes(self, n):
        '''
        Set number of nodes. Call this method each time when number of instances change. 
        '''
        self.current_number_nodes = n

    def get_hash_region(self, key):
        '''
        Return index of a node (to assign key & value) and partition. Return -1 if no running instances.
        '''
        hash_result = key_to_md5(key)
        region_index = self.region_starting_point.index(hash_result[0])

        if self.current_number_nodes == 0:
            return -1, -1

        return region_index%self.current_number_nodes, region_index
