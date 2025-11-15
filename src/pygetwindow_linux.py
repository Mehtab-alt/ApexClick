"""
Mock implementation of pygetwindow for Linux demonstration purposes.
This provides basic window-like objects for testing the UI.
"""

class MockWindow:
    """Mock window object for Linux compatibility."""
    
    def __init__(self, title="Mock Window", left=100, top=100, width=800, height=600):
        self.title = title
        self.left = left
        self.top = top
        self.width = width
        self.height = height
        self._active = True
    
    @property
    def isActive(self):
        return self._active
    
    def activate(self):
        self._active = True
        print(f"Activated mock window: {self.title}")
    
    def __str__(self):
        return f"MockWindow(title='{self.title}', left={self.left}, top={self.top}, width={self.width}, height={self.height})"

def getAllWindows():
    """Return a list of mock windows for demonstration."""
    return [
        MockWindow("ApexClick Demo Window", 100, 100, 800, 600),
        MockWindow("Test Application", 200, 150, 640, 480),
        MockWindow("Browser Window", 300, 200, 1024, 768),
    ]

def getWindowsWithTitle(title):
    """Return windows matching the given title."""
    all_windows = getAllWindows()
    return [w for w in all_windows if title.lower() in w.title.lower()]

def getActiveWindow():
    """Return the currently active window."""
    return MockWindow("Active Window", 0, 0, 1024, 768)

print("Linux pygetwindow compatibility layer loaded")