import hashlib
from bisect import bisect_right

class ConsistentHashRing:
    def __init__(self, replicas=3):
        self.replicas = replicas
        self.ring = {}
        self.sorted_keys = []

    def _get_hash(self, value):
        """Generates a consistent hash for the given value."""
        return int(hashlib.sha256(value.encode()).hexdigest(), 16)

    def add_node(self, node):
        """Adds a node with replicas to the ring."""
        for i in range(self.replicas):
            replica_key = self._get_hash(f"{node}_{i}")
            self.ring[replica_key] = node
            self.sorted_keys.append(replica_key)
        self.sorted_keys.sort()

    def remove_node(self, node):
        """Removes a node and its replicas from the ring."""
        for i in range(self.replicas):
            replica_key = self._get_hash(f"{node}_{i}")
            if replica_key in self.ring:
                del self.ring[replica_key]
                self.sorted_keys.remove(replica_key)

    def get_node(self, key):
        """Returns the closest node for the given key."""
        if not self.ring:
            return None
        hash_value = self._get_hash(key)
        pos = bisect_right(self.sorted_keys, hash_value)
        if pos == len(self.sorted_keys):
            pos = 0
        return self.ring[self.sorted_keys[pos]]
