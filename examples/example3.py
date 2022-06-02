"""
Unsafe: h is leaked

expsec_public: l
"""

h = 4
l = 6
l = h
print(l)
