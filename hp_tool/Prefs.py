import os

class Preferences:
    def __init__(self):
        self.file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'preferences.txt')
