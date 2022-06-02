"""
Unsafe: l * h is leaked

expsec_public: l
"""

l = 3
h = 7
if l == 0:
    print(l * h)
else:
    pass
